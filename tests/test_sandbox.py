"""Tests for workers/sandbox.py and workers/protocol.py.

No Sage, no Django, no database -- these exercise the isolation mechanics on a
plain interpreter:

    python3 -m unittest discover -s tests -v
"""

import json
import os
import socket
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.protocol import (  # noqa: E402
    FrameTooLarge,
    ProtocolError,
    Timeout,
    recv_frame,
    send_frame,
)
from workers.sandbox import run_isolated  # noqa: E402


class Framing(unittest.TestCase):

    def setUp(self):
        self.a, self.b = socket.socketpair()
        self.addCleanup(self.a.close)
        self.addCleanup(self.b.close)

    def test_roundtrip(self):
        payload = {'op': 'search_program', 'source': '2^n', 'max_numbers': 10}
        send_frame(self.a, payload)
        self.assertEqual(recv_frame(self.b, timeout=5), payload)

    def test_roundtrip_of_unicode_and_nesting(self):
        payload = {'messages': [{'text': 'π ≈ 3.14', 'tags': 'alert-info'}]}
        send_frame(self.a, payload)
        self.assertEqual(recv_frame(self.b, timeout=5), payload)

    def test_empty_object(self):
        send_frame(self.a, {})
        self.assertEqual(recv_frame(self.b, timeout=5), {})

    def test_oversized_send_refused_rather_than_truncated(self):
        with self.assertRaises(FrameTooLarge):
            send_frame(self.a, {'x': 'y' * 5000}, max_bytes=1024)

    def test_oversized_announcement_refused_before_allocating(self):
        # A compromised peer announcing a huge frame must be rejected on the
        # header alone, without the body ever being read.
        self.a.sendall((10 ** 9).to_bytes(4, 'big') + b'{}')
        with self.assertRaises(FrameTooLarge):
            recv_frame(self.b, max_bytes=1024, timeout=5)

    def test_truncated_body_is_an_error(self):
        body = json.dumps({'hello': 'world'}).encode()
        self.a.sendall(len(body).to_bytes(4, 'big') + body[:4])
        self.a.close()
        with self.assertRaises(ProtocolError):
            recv_frame(self.b, timeout=5)

    def test_undecodable_body_is_an_error(self):
        body = b'{not json'
        self.a.sendall(len(body).to_bytes(4, 'big') + body)
        with self.assertRaises(ProtocolError):
            recv_frame(self.b, timeout=5)

    def test_deadline_covers_whole_frame_not_each_read(self):
        # A peer dribbling bytes must not be able to hold the connection open
        # indefinitely by staying under a per-read timeout.
        body = b'{"a":1}'
        self.a.sendall(len(body).to_bytes(4, 'big'))
        started = time.monotonic()
        with self.assertRaises(Timeout):
            recv_frame(self.b, timeout=0.3)
        self.assertLess(time.monotonic() - started, 3.0)


class Isolation(unittest.TestCase):

    def test_successful_result_is_returned(self):
        result = run_isolated(lambda: {'numbers': [1, 2, 3]}, timeout=10)
        self.assertTrue(result.ok, result.detail)
        self.assertEqual(result.value, {'numbers': [1, 2, 3]})

    def test_exception_in_child_is_reported_not_propagated(self):
        def boom():
            raise ValueError('deliberate')

        result = run_isolated(boom, timeout=10)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, 'crashed')
        self.assertIn('deliberate', result.detail)

    def test_sleeping_child_is_killed_on_wall_clock(self):
        # Sleeping burns no CPU, so RLIMIT_CPU would never fire here. This is
        # what the parent's wall-clock kill is for.
        started = time.monotonic()
        result = run_isolated(lambda: time.sleep(30), timeout=0.5)
        elapsed = time.monotonic() - started
        self.assertFalse(result.ok)
        self.assertEqual(result.error, 'timeout')
        self.assertLess(elapsed, 10.0, 'parent did not stop waiting promptly')

    def test_busy_loop_child_is_killed(self):
        def spin():
            while True:
                pass

        started = time.monotonic()
        result = run_isolated(spin, timeout=0.5)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, 'timeout')
        self.assertLess(time.monotonic() - started, 10.0)

    def test_oversized_output_is_refused(self):
        result = run_isolated(lambda: {'x': 'y' * 100000}, timeout=10,
                              max_output=4096)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, 'output_too_large')

    def test_child_cannot_mutate_parent_state(self):
        # Each evaluation starts from the parent's pristine image; this is the
        # property that a long-lived evaluator would not have.
        marker = {'touched': False}

        def mutate():
            marker['touched'] = True
            return 'done'

        result = run_isolated(mutate, timeout=10)
        self.assertTrue(result.ok, result.detail)
        self.assertFalse(marker['touched'],
                         'child mutation leaked into the parent')

    def test_consecutive_runs_do_not_share_state(self):
        counter = {'n': 0}

        def bump():
            counter['n'] += 1
            return counter['n']

        first = run_isolated(bump, timeout=10)
        second = run_isolated(bump, timeout=10)
        self.assertEqual(first.value, 1)
        self.assertEqual(second.value, 1, 'state carried between evaluations')

    def test_child_cannot_write_files(self):
        # RLIMIT_FSIZE is 0, so the sandbox cannot create or grow files even if
        # the filesystem were writable.
        target = os.path.join(tempfile.gettempdir(), 'sandbox-should-not-exist')
        self.addCleanup(lambda: os.path.exists(target) and os.unlink(target))

        def try_to_write():
            with open(target, 'w') as handle:
                handle.write('x' * 1024)
            return 'wrote'

        result = run_isolated(try_to_write, timeout=10)
        self.assertFalse(result.ok, 'sandbox was able to write a file')

    def test_grandchildren_are_killed_too(self):
        # Sage shells out to Singular, GAP, PARI and Maxima, so killing only the
        # direct child would strand helper processes. The whole process group
        # must go.
        #
        # The pid travels back over a pipe rather than a file, because the
        # sandbox forbids file writes (see test_child_cannot_write_files).
        read_fd, write_fd = os.pipe()
        self.addCleanup(lambda: os.close(read_fd))

        def spawn_and_hang():
            grandchild = os.fork()
            if grandchild == 0:
                try:
                    os.write(write_fd, str(os.getpid()).encode())
                    time.sleep(60)
                finally:
                    os._exit(0)
            time.sleep(60)

        result = run_isolated(spawn_and_hang, timeout=1.0)
        os.close(write_fd)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, 'timeout')

        content = os.read(read_fd, 64).decode().strip()
        self.assertTrue(content, 'grandchild never reported its pid')
        grandchild_pid = int(content)

        alive = True
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            try:
                os.kill(grandchild_pid, 0)
            except OSError:
                alive = False
                break
            time.sleep(0.05)
        self.assertFalse(alive, 'grandchild survived the process-group kill')

    def test_parent_survives_a_child_that_writes_garbage(self):
        def garbage():
            os.write(1, b'')  # harmless; the real check is the return value
            return object()   # not JSON-serialisable

        result = run_isolated(garbage, timeout=10)
        self.assertFalse(result.ok)
        self.assertIn(result.error, ('crashed', 'undecodable'))

    def test_no_zombies_left_behind(self):
        for _ in range(5):
            run_isolated(lambda: 1, timeout=10)
        # If children were not reaped, waitpid would find one here.
        with self.assertRaises(ChildProcessError):
            os.waitpid(-1, os.WNOHANG)


if __name__ == '__main__':
    unittest.main()

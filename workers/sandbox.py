"""Fork-per-evaluation isolation harness.

Deliberately free of any Sage or Django import so the isolation mechanics can be
unit-tested on a plain interpreter -- see ``tests/test_sandbox.py``. The Sage
parts live in ``workers/evaluator.py``.

The model is prefork: a parent imports Sage once (seconds), then forks a child
per request. The child inherits the warm interpreter copy-on-write, evaluates
exactly one expression, and exits. Each request therefore starts from the
pristine parent image, so nothing carries between requests -- no accumulated
state, no leaked objects, and an escape dies with its child.

Division of responsibility, which is the point of the design:

* The **child** computes and writes bytes to a pipe. It never touches the
  listening socket, never sees the client, and cannot influence the reply
  framing.
* The **parent** owns all I/O and every deadline. It assumes the child is
  hostile: bounded reads, wall-clock kill, whole-process-group SIGKILL.

Timeouts are layered because the innermost is defeatable. Sage's ``alarm()``
can be cancelled by the code being evaluated, so it is a convenience. The real
controls are ``RLIMIT_CPU`` -- which hostile code cannot raise, since the hard
limit is lowered too -- and the parent's wall-clock kill, which catches sleeping
and blocking that burn no CPU at all.
"""

import errno
import json
import os
import resource
import select
import signal
import time

__all__ = ['SandboxResult', 'run_isolated']

#: Ceiling on bytes a child may write back. Read is bounded regardless of what
#: the child intends.
MAX_CHILD_OUTPUT = 1 << 20


class SandboxResult:
    """Outcome of one isolated evaluation.

    ``ok`` is True only when the child exited cleanly *and* produced a decodable
    payload. ``error`` is a short stable token ('timeout', 'crashed',
    'output_too_large', 'undecodable', 'internal') suitable for branching on;
    ``detail`` is for logs, never for users.
    """

    __slots__ = ('ok', 'value', 'error', 'detail')

    def __init__(self, ok, value=None, error=None, detail=None):
        self.ok = ok
        self.value = value
        self.error = error
        self.detail = detail

    def __repr__(self):
        if self.ok:
            return '<SandboxResult ok>'
        return '<SandboxResult error=%r detail=%r>' % (self.error, self.detail)


def _apply_child_limits(cpu_seconds, address_space_bytes, max_processes,
                        max_open_files):
    """Lower resource limits in the child, before any user code runs.

    Both soft and hard limits are set, so the child cannot raise them back.
    """
    def _set(what, value):
        if value is None:
            return
        try:
            resource.setrlimit(what, (value, value))
        except (ValueError, OSError):
            # A limit we cannot lower is not worth aborting over; the container
            # limits still apply.
            pass

    _set(resource.RLIMIT_CPU, cpu_seconds)
    _set(resource.RLIMIT_AS, address_space_bytes)
    # RLIMIT_NPROC is deliberately off by default. It is per *UID* and counts
    # processes that already exist, so a small value fails instantly whenever
    # the UID is shared -- on a developer machine with ~170 processes, a limit
    # of 64 makes the very first fork raise BlockingIOError. Use the
    # container's `pids_limit` instead: it is per-container and counts only
    # this container's processes. Left configurable for callers that run under
    # a dedicated UID and know what they are asking for.
    _set(resource.RLIMIT_NPROC, max_processes)
    _set(resource.RLIMIT_NOFILE, max_open_files)
    _set(resource.RLIMIT_CORE, 0)      # no core dumps; they would leak memory
    _set(resource.RLIMIT_FSIZE, 0)     # cannot create or grow files


def _kill_process_group(pid):
    """SIGKILL the child's whole process group.

    The group matters: user code may have spawned helpers (Sage shells out to
    Singular, GAP, PARI, Maxima), and killing only the direct child would leave
    those running.
    """
    try:
        group = os.getpgid(pid)
    except OSError:
        group = pid
    for signal_number in (signal.SIGKILL,):
        try:
            os.killpg(group, signal_number)
        except OSError as error:
            if error.errno != errno.ESRCH:
                try:
                    os.kill(pid, signal_number)
                except OSError:
                    pass


def _read_bounded(read_fd, limit, deadline, clock):
    """Read up to ``limit`` bytes before ``deadline``.

    Returns (data, overflowed, timed_out).
    """
    chunks = []
    total = 0
    while True:
        remaining_time = deadline - clock()
        if remaining_time <= 0:
            return b''.join(chunks), False, True
        ready, _, _ = select.select([read_fd], [], [], remaining_time)
        if not ready:
            return b''.join(chunks), False, True
        try:
            chunk = os.read(read_fd, 65536)
        except OSError:
            break
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            return b''.join(chunks), True, False
        chunks.append(chunk)
    return b''.join(chunks), False, False


def run_isolated(compute, timeout=10.0, max_output=MAX_CHILD_OUTPUT,
                 cpu_seconds=None, address_space_bytes=None,
                 max_processes=None, max_open_files=64, clock=None):
    """Run ``compute()`` in a forked child and return a ``SandboxResult``.

    ``compute`` must return a JSON-serialisable object. It runs in a child that
    has had its resource limits lowered and has been placed in its own process
    group. Exceptions inside it are reported as 'crashed' rather than
    propagating -- the parent must survive anything the child does.
    """
    if clock is None:
        clock = time.monotonic
    if cpu_seconds is None:
        # A hard CPU ceiling slightly above the wall-clock budget: the wall
        # clock should normally fire first, with RLIMIT_CPU as the backstop for
        # code that has disabled softer timers.
        cpu_seconds = int(timeout) + 1

    read_fd, write_fd = os.pipe()

    pid = os.fork()
    if pid == 0:  # ---- child ----
        exit_code = 1
        try:
            os.close(read_fd)
            # Own session and process group, so the parent can kill the child
            # together with anything it spawned.
            try:
                os.setsid()
            except OSError:
                pass
            _apply_child_limits(cpu_seconds, address_space_bytes,
                                max_processes, max_open_files)
            try:
                payload = {'ok': True, 'value': compute()}
            except BaseException as error:  # noqa: BLE001 - must not escape
                payload = {
                    'ok': False,
                    'error': 'crashed',
                    'detail': '%s: %s' % (type(error).__name__, error),
                }
            body = json.dumps(payload, separators=(',', ':'),
                              allow_nan=False).encode('utf-8')
            os.write(write_fd, body)
            exit_code = 0
        except BaseException:  # noqa: BLE001
            exit_code = 1
        finally:
            try:
                os.close(write_fd)
            except OSError:
                pass
            # _exit, not sys.exit: no atexit handlers, no flushing of buffers
            # inherited from the parent, no interpreter teardown in a process
            # that may be in an arbitrary state.
            os._exit(exit_code)

    # ---- parent ----
    os.close(write_fd)
    deadline = clock() + timeout
    try:
        data, overflowed, timed_out = _read_bounded(read_fd, max_output,
                                                    deadline, clock)
    finally:
        try:
            os.close(read_fd)
        except OSError:
            pass

    if timed_out or overflowed:
        _kill_process_group(pid)
        _reap(pid, deadline=clock() + 2.0, clock=clock)
        if overflowed:
            return SandboxResult(False, error='output_too_large',
                                 detail='child exceeded %d bytes' % (max_output,))
        return SandboxResult(False, error='timeout',
                             detail='exceeded %.1fs' % (timeout,))

    status = _reap(pid, deadline=clock() + 2.0, clock=clock)
    if status is None:
        _kill_process_group(pid)
        _reap(pid, deadline=clock() + 2.0, clock=clock)
        return SandboxResult(False, error='timeout',
                             detail='child did not exit')

    if not data:
        return SandboxResult(False, error='crashed',
                             detail='no output; wait status %r' % (status,))

    try:
        payload = json.loads(data.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return SandboxResult(False, error='undecodable', detail=str(error))

    if not isinstance(payload, dict):
        return SandboxResult(False, error='undecodable', detail='not an object')
    if payload.get('ok'):
        return SandboxResult(True, value=payload.get('value'))
    return SandboxResult(False, error=payload.get('error', 'crashed'),
                         detail=payload.get('detail'))


def _reap(pid, deadline, clock):
    """Wait for ``pid``, returning its status, or None if it outlives the deadline."""
    while True:
        try:
            waited_pid, status = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            return 0
        except OSError:
            return 0
        if waited_pid == pid:
            return status
        if clock() >= deadline:
            return None
        time.sleep(0.005)

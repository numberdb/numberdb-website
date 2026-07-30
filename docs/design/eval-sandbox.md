# Design: sandboxed evaluator, and removing Pyro

Status: proposed
Supersedes: `workers/eval.py` (`SafeEval` over Pyro5), services `eval` and `pyro-ns`

## Summary

Replace the Pyro-based `SafeEval` worker with a single sandboxed evaluator
container that has **no network access at all**, speaks a JSON protocol over a
Unix domain socket, and runs every user expression in a **fresh forked child
that is killed after one evaluation**.

Pyro is removed entirely. Nothing else in the application uses it.

## What is actually there today

Worth stating precisely, because the migration is far smaller than it looks.

**Exactly one live call site.** `numberdb_app/api.py:138` →
`E.eval_search_program(program)`, powering advanced search. The other two
apparent callers are dead:

- `utils/utils.py` — the Pyro block sits after an unconditional `return None`.
  Unreachable. (Separately: `factor_with_timeout` is defined six times in that
  file; only the last binding survives. Worth cleaning up.)
- `numberdb_app/views.py` — its Pyro block is inside a `'''…'''` string literal.

**The dangerous method is exposed but unused.** `SafeEval.eval()` is a bare
`eval(preparse(source))` with no validation. No caller invokes it. It is
reachable by anyone who can speak Pyro to the daemon.

**`SafeEval.factor()` cannot work.** Its `wrap_result` references an undefined
`result_bytes` (it builds `wrapped_result_bytes`), so it raises `NameError`.
Consistent with it never having been called.

**It has never run in Docker anyway.** `Pyro5.server.Daemon()` at
`workers/eval.py:484` takes no host argument, so it binds `localhost` and
registers that URI with the name server. From the `web` container `localhost`
is the web container. Every call fails and is swallowed by the
`(NamingError, CommunicationError)` handlers. The eval container's entire log
is `Ready.`

So there is no working service to preserve, no cutover risk, and the callers
already degrade gracefully when the evaluator is absent.

## Threat model

The input is an arbitrary expression typed into a public, unauthenticated
search box.

**Assume the expression achieves arbitrary code execution inside the
evaluator.** The design goal is to make that outcome boring, not to prevent it.
Python-level sandboxing of a library as large as Sage is not a boundary anyone
should bet on: Sage reaches into the filesystem, spawns helper binaries
(Singular, GAP, PARI, Maxima), and exposes enormous attack surface through
attribute traversal.

The current AST filter is a **deny-list**, which is the weak form. It carries a
live bug that illustrates the point exactly — in `check_Identifier`:

```python
'exec', 'breakpoint', 'classmethod', 'compile'
'delattr', 'dir', 'getattr', ...
```

The missing comma concatenates the two entries into `'compiledelattr'`, so
**neither `compile` nor `delattr` is blocked**. One absent character silently
opened two holes and nothing failed loudly. A deny-list of ~50 names against a
language with `__subclasses__` traversal was never going to hold; a typo in one
just makes it faster.

Keep the AST check — it gives good error messages and stops honest mistakes —
but demote it to defence in depth. The container is the boundary.

What we are protecting:

1. **The `web` container** — holds Postgres credentials and the Django secret
   key. Currently reachable from the evaluator via the pickle it returns.
2. **The host** — Docker socket, other projects (`garden-codex`, `project-hub`,
   `site-edge`), TLS private keys.
3. **The network** — outbound abuse, exfiltration, pivoting to Tailscale peers.

## Can Pyro go completely?

Yes. Pyro supplies three things here, all of them liabilities:

| Pyro provides | Why it is not needed |
|---|---|
| Name discovery | Compose already gives stable DNS. Discovery is why a name server was published to the internet and could be rebound. |
| RPC transport | One request/response, one endpoint. A socket and a length prefix cover it. |
| Serialization | It carried Sage pickles into the web process — the pickle sink we are removing. |

Removing Pyro deletes the `pyro-ns` container, the `Pyro5` dependency, the
name-rebinding attack, and the `loads()` sink in one change.

## Architecture

The hard constraint is startup cost: importing `sage.all` takes seconds. That
rules out the obvious strong design.

- **Long-lived service** (what exists today) — fast, but state persists between
  requests. One successful escape poisons every later evaluation and dwells
  indefinitely.
- **One container per evaluation** — perfect isolation, but pays full Sage
  startup per request. Unusable interactively.
- **Prefork, one evaluation per child** *(recommended)* — a supervisor imports
  Sage once at boot, then `fork()`s a child per request. The child inherits the
  warm interpreter copy-on-write, evaluates exactly one expression, returns its
  result, and exits. The supervisor never evaluates anything itself.

The third gives one-shot isolation at fork cost rather than interpreter-boot
cost. Each request starts from the pristine parent image, so nothing carries
over — no cross-request contamination, no leak accumulation, and an escape dies
with its child.

The supervisor must treat every child as hostile: it owns the timeout, it reads
a bounded reply, and it kills the whole child process group on expiry.

### Validated against real Sage

Prefork rests on an assumption worth checking rather than believing: that Sage
survives `fork()`. Run inside the production image, with `sage.all` imported in
the parent and each expression evaluated in a forked child:

| expression | result |
|---|---|
| `2^10` | `1024` |
| `{n: 2^n for n in [1..5]}` | `{1: 2, 2: 4, 3: 8, 4: 16, 5: 32}` |
| `RIF(10,11)` | `11.?` |
| `sqrt(2)` | `sqrt(2)` |
| infinite loop | killed, `error=timeout` |
| `__import__("os").system("id")` | rejected by the validator |

So the warm-parent/forked-child model holds for this workload.

### A note on RLIMIT_NPROC

`RLIMIT_NPROC` looks like the natural way to stop fork bombs, and it is the
wrong tool here: it is per **UID** and counts processes that already exist, so a
small value fails instantly whenever the UID is shared. Setting 64 on a
developer machine already running ~170 processes makes the very first `fork`
raise `BlockingIOError` — found by a test, not by reasoning.

Use the container's `pids_limit` instead: per-container, counting only that
container's processes. `workers/sandbox.py` therefore leaves `RLIMIT_NPROC`
unset by default while keeping it configurable.

### Isolation

The key decision: **`network_mode: none`**. The evaluator needs no network
whatsoever. With no interfaces, arbitrary code execution still cannot exfiltrate
data, reach Postgres, call the Docker API, or touch Tailscale peers. Since that
forbids TCP, `web` and the evaluator communicate over a **Unix domain socket** on
a shared volume.

```yaml
  evaluator:
    image: numberdb/web:latest
    command: ["sage", "-python", "workers/evaluator.py"]
    network_mode: none          # no interfaces at all; UDS is the only channel
    read_only: true             # immutable root filesystem
    user: "65534:65534"         # non-root
    cap_drop: [ALL]
    security_opt:
      - no-new-privileges:true
    pids_limit: 64              # blocks fork bombs
    mem_limit: 512m
    cpus: 1.0
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=64m
    volumes:
      - eval-sock:/run/eval     # the only shared surface
    restart: unless-stopped
```

Notes:

- `network_mode: none` is the single highest-value control here. Prefer it over
  a firewall: Docker publishes ports through its own iptables chain and bypasses
  `ufw` entirely, so a firewall rule would look protective without being so.
  This is the same reasoning that removed the `9090` publish rather than
  filtering it.
- If UDS proves awkward, the fallback is a compose network marked
  `internal: true` — no gateway, so no egress — but it still permits
  container-to-container traffic and is strictly weaker.
- Mount no source code and no secrets. The evaluator needs Sage and its own
  entry point, nothing else. It must never see `.env`.
- The image is currently shared with `web` (`numberdb/web:latest`). A separate,
  smaller image without Django, credentials handling, or the data pipeline
  would be better, and pairs naturally with the passagemath work.

### Timeouts

Three layers, because the innermost is defeatable:

1. `alarm()` inside the child — cheap, gives a clean error, but hostile code can
   cancel it. Convenience only, not a control.
2. **Supervisor-side wall-clock kill** — `SIGKILL` to the child's process group
   on expiry. This is the real control.
3. Client-side deadline in Django, so a wedged supervisor cannot hang a worker.

The current `alarm(1)` is layer 1 only.

## Wire protocol

Length-prefixed JSON in both directions. **No pickle on either side.**

Returning a pickle to `web` hands code execution to whatever the evaluator
became — the exact inversion we are fixing, since `web` holds the database
credentials. Serialize numbers as typed records and reconstruct them explicitly
on the Django side with a fixed dispatch table, mirroring the existing
`to_serializable_dict()` shape:

```json
{"type": "RIF", "value": "3.14159...", "param": "n=3"}
```

Reconstruction must be a lookup keyed on `type`, never a constructor named by
the payload.

Request:

```json
{"op": "search_program", "source": "<user expression>", "max_numbers": 1000}
```

Reply:

```json
{"ok": true, "numbers": [...], "messages": [...]}
{"ok": false, "error": "timeout" | "rejected" | "internal", "messages": [...]}
```

Bound the reply size in the supervisor. `max_numbers` alone does not cap bytes.

## Migration

1. Add `workers/evaluator.py` (supervisor + fork-per-request) and the compose
   service. Nothing calls it yet.
2. Add a small client module for `web`, with an explicit reconstruction table.
3. Switch `numberdb_app/api.py` to it. Keep the existing
   `except` fallback so absence stays graceful. **This is the only call site.**
4. Delete: `workers/eval.py`, services `eval` and `pyro-ns`, the `Pyro5`
   dependency, and the dead Pyro blocks in `utils/utils.py` and
   `numberdb_app/views.py`.
5. ~~Port the AST check into the child as defence in depth.~~ **Done ahead of
   the rest**: `workers/expression_validator.py` replaces the deny-list with an
   allow-list, covered by `tests/test_expression_validator.py` (29 tests, no
   Sage or Django needed — `python3 -m unittest discover -s tests`). The child
   calls `validate_expression(preparsed_source, namespace)` before evaluating.

### The validator

Two properties carry most of the weight:

- **`ast.Attribute` is not an allowed node at all.** Nearly every published
  Python sandbox escape traverses attributes
  (`().__class__.__bases__[0].__subclasses__()`). Search expressions have no
  legitimate need for attribute access, so forbidding the node type removes the
  whole family rather than naming its members.
- **The allowed-name set is derived from the evaluation namespace**, not
  maintained beside it. A name that is not in the namespace is not permitted,
  and adding one permits it automatically — the two cannot drift apart, which
  is precisely how the old list rotted.

It validates *preparsed* source, so `PREPARSER_NAMES` covers what Sage's
preparser emits (`Integer`, `RealNumber`, `ellipsis_range`, `ellipsis_iter`,
`Ellipsis`). Verified against the real preparser rather than assumed:
`2^n` → `Integer(2)**n`, `[1..10]` →
`ellipsis_range(Integer(1),Ellipsis,Integer(10))`.

Also enforced: no dunder names anywhere, calls only to bare permitted names
(no `f()()`, no method calls), no lambda/walrus/f-string/starred arguments, no
statements, and caps on source length, node count and nesting depth. Comprehension
scoping is handled properly — loop variables are visible in the body, later
generators and conditions, but do not leak out, and the first iterable is
evaluated in the enclosing scope.

This remains defence in depth. It is not the boundary; the container is.

Steps 1–2 are additive and independently reviewable. Step 3 is a one-line swap.

## Related, not in scope

**The public API ships pickles to clients.** `to_serializable_dict()` emits
`'sage': self.to_sage().dumps().decode('cp437')` (`models.py:499`, `621`, `753`),
and the shipped client unpickles it:

```python
'sage': loads(bytes(result['number']['sage'], encoding='cp437'))
```

Every user of `clients/sage/numberdb-sage-interface.py` therefore executes
whatever the server sends. A server compromise, or a MITM, becomes code
execution on their machine. This is the same pickle-as-transport mistake at the
public boundary, and it deserves its own change — the JSON encoding designed
above is directly reusable, but the client is already distributed, so it needs a
compatibility story.

## Open questions

1. UDS or `internal: true` network? UDS is stricter; the network is simpler.
2. Split the evaluator into its own image now, or after the passagemath work?
3. Do we keep `SafeEval.eval()` (raw eval) in any form? Nothing uses it. Default
   to deleting it.
4. Concurrency: how many simultaneous children before shedding load? `pids_limit`
   sets a hard ceiling; the supervisor needs a softer one with a clear error.

# Running agents against this deployment

Notes about *this* repository and *this* server: the containers, the ssh, the
proxy, the runner. None of it belongs in the skill at
<https://numberdb.org/skill>, which is written for somebody with Python and
perhaps Sage who wants to contribute a table, and for whom none of this is
true. See the top of `agents/lessons/PROPOSALS.md` for which way a given
lesson goes.

These are notes rather than proposals: most are already fixed in the script
they describe, and are kept because the next person to change that script will
otherwise undo them.

---

## Never test in the container that is serving the site

What happened: to run the test suite against uncommitted changes, the changed
files were copied into the running production container with `docker cp`. One
of them added a model field. The migration had not been applied to the
production database, so live code began selecting a column that did not exist,
and every page that touches a permission check started returning 502. It went
unnoticed for several minutes because the home page renders without one and
still answered 200 -- the site looked up while table pages were down.

What the skill says now: nothing. It covers how to build a table and says
nothing about where to run things.

What it should say: the container serving the site is not a test environment.
Run tests in a throwaway (`docker compose run --rm --no-deps` with the code
mounted read-only), where a half-applied change cannot reach a reader. And
when checking whether a deploy is healthy, fetch a page that exercises the
thing that changed -- the home page answering 200 is not evidence that table
pages do.

Evidence: `curl https://numberdb.org/T94` returned 502 in 36s while
`curl https://numberdb.org/` returned 200 in 5.8s, on 2026-08-30. Restored
with `docker compose up -d --force-recreate web`, which puts the image's own
code back.

## A pipeline that swallows the verdict reports nothing

What happened: the suite was run as `manage.py test ... | tail -30`. The
summary goes to stderr and was lost, and the shell reported `tail`'s exit
code, which is 0 whatever the tests did. The run was recorded as "exit code
0" and it was not evidence of anything. A second run then failed for an
unrelated reason -- the first run's `test_numberdb` was still there and the
prompt to delete it hit no stdin -- and that failure was briefly mistaken for
a real one.

What the skill says now: nothing.

What it should say: capture the whole run to a file (`> log 2>&1`), report the
command's own exit code, and grep the file for the summary line. Pass
`--noinput` so a leftover test database is an answer rather than a hang. A
result you cannot point at a summary line for is not a result.

Evidence: `EXIT=1` with no matching summary line, 2026-08-30; the log ended in
`EOFError: EOF when reading a line` from `_create_test_db`.

## An unattended run needs the permissions its prompt requires

What happened: the first stage-one run under `agents/run.sh` was started
with `--permission-mode acceptEdits` and no allowlist. That mode permits file
edits and nothing that leaves the machine, so every call the prompt makes
mandatory was refused with nobody there to approve it: `gh issue list`,
`curl https://api.github.com/...`, `WebFetch`, `WebSearch`, `python3 -c ...`
(and so `screen.py`), and `agents/sage.sh` (which is `ssh`). Compound lines
(`a | b`, `a; b`) were refused as a unit even where each half was harmless.
The run could not search the corpus, could not read the issues, could not
screen a source, and could not compute a single check; it produced a batch
anyway, from repository prose and memory, and had to say so in every
section. Two hundred turns were budgeted; the useful work fitted in far
fewer because most of what the prompt asks for was unreachable.

What the skill says now: nothing about the environment a run gets. `run.sh`
says what a run *cannot* do (publish, deploy, reach the serving container)
and nothing about what it must be *able* to do.

What it should say (in `run.sh`, not the skill): pass an allowlist that
covers exactly the prompt's needs and no more --

    --allowedTools "Bash(gh issue list:*)" "Bash(gh issue view:*)" \
                   "Bash(agents/sage.sh:*)" \
                   "Bash(python3 agents/table-ideas/screen.py:*)" \
                   "Bash(python3 agents/table-build/*:*)" \
                   "Bash(git add:*)" "Bash(git commit:*)" \
                   "WebFetch(domain:numberdb.org)" \
                   "WebFetch(domain:en.wikipedia.org)" \
                   "WebFetch(domain:oeis.org)" "WebFetch(domain:dlmf.nist.gov)" \
                   "WebFetch(domain:mathworld.wolfram.com)" \
                   "WebFetch(domain:github.com)" "WebFetch(domain:api.github.com)"

-- and, before spending a turn, a preflight that runs `gh issue list
--limit 1` and `agents/sage.sh` on a two-line script from *inside* the
session, so that a run which cannot do the work stops in its first minute
rather than its last. Better still, have `run.sh` fetch the open issues to
`agents/table-ideas/issues.json` and the corpus titles to `corpus.tsv`
before launching, so stage one screens against cached files and makes one
network call instead of dozens.

Evidence: 2026-08-31, `agents/runs/20260830T211242Z-ideas.log`; every
network and Python call in it ends in "This command requires approval" or
"requested permissions ... but you haven't granted it yet". The batch that
resulted is `agents/table-ideas/BATCH-2026-08-31.md`, whose first section
lists what was and was not done.

## Python does not see the proxy that curl sees

What happened: with the allowlist in place, `curl https://numberdb.org/skill`
answered 200 in a second, and `numberdb.table('T94')` from the same shell
hung for its full 60-second timeout with "the handshake operation timed out".
GitHub answered Python directly, so it looked like numberdb.org was down. It
was not: the machine reaches it only through `ALL_PROXY=socks5h://127.0.0.1:1080`,
which curl honours and Python's `http.client` and `urllib` ignore. Every
call the prompt makes mandatory -- `search_text`, `table`, `screen.already_here`,
`screen.source_names_it` -- goes through those two modules. Worse,
`already_here` catches the transport error and `continue`s, so it returned
`[]` for every name, which reads exactly like "nothing in the corpus". The
first corpus search of this run produced no output for five minutes and was
that close to being written up as a clean sweep.

What the skill says now: nothing about the environment; `screen.py` says it
"reaches the outside through ordinary HTTP".

What it should say: (in `run.sh` or `screen.py`) if `ALL_PROXY` names a SOCKS
proxy, route Python through it -- PySocks is installed, and eight lines
(`socks.set_default_proxy`, `socket.socket = socks.socksocket`, drop the
`*_proxy` variables so urllib does not try to use the SOCKS URL as an HTTP
proxy) make the client and the screen work unchanged. And `already_here`
should report "could not ask the corpus" the way `already_asked` reports
"could not ask GitHub", rather than swallowing the exception: an empty answer
and a failed question must not look the same.

Evidence: 2026-08-31, `/tmp/diag_net.py`: `numberdb.org 45.33.90.86 AF_INET:
FAILED in 8.13s`, `api.github.com: TLS ok in 0.09s`; after the bootstrap,
`search_text` answered in 0.2-1.8 s per term.

## `already_asked` cannot see an issue more general than the name

What happened: `already_asked('Regulators of real quadratic fields')`
returned `[]`. numberdb-data#15, *Regulators of number fields*, is open and
is exactly the issue. The search ANDs the first three words longer than four
letters -- `Regulators quadratic fields` -- against issue titles, and #15 has
no "quadratic". Likewise `Dedekind zeta values ... at negative integers` did
not find #22, *Special values of various L-functions at integers*. Both were
found by reading the 82 open titles by hand, which the prompt also asks for.

What the skill says now: nothing; `screen.py` says a closed issue "usually
means it exists".

What it should say: `already_asked` finds an issue that shares the name's
words and misses one that asks for the superset. Run it once with the full
name and once with the family's *genus* ("Regulators", "L-function values"),
and read the open titles regardless -- 82 lines is one screen.

Evidence: 2026-08-31, this run; #15 and #22 in the open list, `[]` from the
screen for both names.

## `source_names_it` matches word forms, not words

What happened: `source_names_it('Regulators of real quadratic fields',
'.../Fundamental_unit_(number_theory)')` reported "the source does not
mention regulators". The page says "regulator", singular, nine times. The
Bianchi group page likewise "does not mention fields" -- it says "field".
Both are the right sources.

What the skill says now: nothing.

What it should say: the check looks for each distinguishing word as a
substring of the page text, so a plural in the name and a singular on the
page fail it. Either strip a trailing `s` before matching, or -- cheaper --
name the family in the singular when screening and say so in the proposal.
A pass is evidence; a fail on a plural is not.

Evidence: 2026-08-31, this run's screen log; the same two names passed on
their second URL, which happened to use the plural.

## `import numberdb` fails outside sage.sh, and reads like the site being down

What happened: the corpus listing for the 2026-08-31b batch was run with plain
`python3` and died with `ModuleNotFoundError: No module named 'numberdb'`. The
client is not installed anywhere; it lives at `clients/python`, and only
`agents/sage.sh` puts it on the path (`PYTHONPATH=/app/clients/python`, inside
the container). The prompt tells the run to call `numberdb.search_text` and
`numberdb.table` as if they were importable.

What the skill says now: "`pip install numberdb`", which the run may not do
and which would install the published package rather than the repository's.

What it should say (in `PROMPT.md` or `screen.py`): a local script needs
`sys.path.insert(0, 'clients/python')` and `sys.path.insert(0,
'agents/table-ideas')`, then `screen.use_socks_proxy_if_set()`, then `import
numberdb`. Better, `screen.py` could do the first insert itself, since it
already does the proxy bootstrap for the same reason.

Evidence: 2026-08-31, `/tmp/corpus_list.py`, first run exit 1 with the
traceback above; second run listed 127 tables in about four minutes.

## `agents/sage.sh` passes no arguments, so `dry_run.py` cannot be run as written

What happened: the prompt says `sage -python agents/table-build/dry_run.py
path/to/generate.py`, and the run environment says every Sage computation
goes through `agents/sage.sh`. `sage.sh` runs `sage -python /work/<script>`
with no arguments, so `dry_run.py` under it prints its usage and exits. The
run wrote a nine-line wrapper that sets `sys.argv` and imports `dry_run`,
and mounted `dry_run.py`, `check.py` and the generator beside it.

What the skill says now: nothing; `PROMPT.md` gives the bare command.

What it should say: either `sage.sh` should forward arguments after the
first file (`agents/sage.sh dry_run.py generate.py -- generate.py`), or
`dry_run.py` should also read the generator's path from an environment
variable, and the prompt should give the command that works under
`sage.sh`. Also: `dry_run.py`'s docstring offers `--identities checks.py`,
which `main` does not implement.

Evidence: 2026-08-31, building T128; `/tmp/dry.py` is the wrapper.

## ssh forwards stdin, so a helper call before the real one eats the key

What happened: `cat key | agents/sage.sh create_draft.py` failed with
"writing needs an API key; set NUMBERDB_API_KEY". The script read stdin and
got nothing: `sage.sh` makes two `ssh` calls before the one that runs the
container, and `ssh` without `-n` passes its stdin to the remote command,
so the `chmod` call consumed the key. The message reads like a missing
variable, and the first guess was that the container did not see the pipe.

What the skill says now: nothing; the run prompt says `sage.sh` forwards
stdin.

What it should say: fixed in `sage.sh` (commit 18c27c9): `-n` on every ssh
but the last. The lesson for any other runner: a "no key" refusal from a
script that was piped one means something upstream read the pipe first, and
a probe that prints `len(sys.stdin.read())` -- never the bytes -- settles it
in one run.

Evidence: 2026-08-31, `/tmp/stdin_probe.py`: 0 bytes before the fix, 10 after.

## `audit_table` can be run from a run, in the throwaway

What happened: the prompt asks for `manage.py audit_table T1xx`, and a run
has no Django and no database. Six lines through `agents/sage.sh` did it:
`sys.path.insert(0, '/app')`, `django.setup()`,
`call_command('audit_table', 'T128', '--links')`. The compose service
supplies `DJANGO_SETTINGS_MODULE` and `DATABASE_URL`, the throwaway shares
the network, and the command changes nothing. "Nothing to report."

What the skill says now: run the audit; nothing on how, from outside.

What it should say: give the six lines, or add `agents/audit.sh T1xx` so the
next run does not have to work out that the throwaway can reach the
database read-only.

Evidence: 2026-08-31, `/tmp/audit.py`.

## `POST /api/table/<tid>` answered 403 to the key that had just created and filled the table

What happened: retitling draft T128 through `write_table` was refused with
"the server refused the API key" -- the same key had created the draft and
written its 607 entries minutes before. `write_table` was the one writer in
`api.py` with neither `@csrf_exempt` nor `@rate_limited`, so Django's CSRF
middleware answered the POST with a bare HTML 403 before the view ran, and
the client, seeing 403 and no JSON, blamed the key. The Django test client
does not enforce CSRF, so no test could have seen it.

What the skill says now: nothing about which API routes work from outside.

What it should say: nothing in the skill -- the fix is `@csrf_exempt` on the
view and a test with `Client(enforce_csrf_checks=True)`, both in this
commit and not yet deployed. For a run: a 403 from a key that just worked on
a neighbouring route is the route, not the key; and the draft's title, and
so its address, is left for a person to fix on the site, or for a later run
once the fix is deployed (`/tmp/retitle.py` does it in one request).

Evidence: 2026-08-31, `/tmp/retitle.py`: `HTTPError: HTTP Error 403:
Forbidden` from `urllib`, no JSON body; `create_table` and `write_entries`
with the same key returned 201 and 200.

## The server is small, and concurrent Sage runs take it down

What happened: several test suites were started on the server without waiting
for the previous one to finish -- and `timeout` on this side kills the local
ssh, not the remote `docker compose run`, so runs believed to be dead were
still going. Load average reached 68 on a box with 961 MB of RAM. sshd went on
accepting TCP connections but stopped completing handshakes, which reads
exactly like the server being down, and the SOCKS proxy that this machine
reaches numberdb.org through is itself an ssh tunnel to that same box, so it
died too and the site became unreachable from here. The site itself was up
throughout, and answering; only this machine could not see it.

What to do instead: **one thing at a time on that server.** Wait for a test
run to report before starting another. Give a run a timeout long enough to
finish -- the full suite takes about ten minutes and 780 seconds was not
enough -- and remember that a `timeout` here does not stop the container
there.

`agents/sage.sh` now multiplexes its ssh calls (`ControlMaster`), so a run
costs one connection rather than three.

To tell an overloaded server from a dead one: TCP connects on 22, 443 and 80
but ssh hangs "during banner exchange" -- that is load, not a ban, and it
clears on its own. `https://r.jina.ai/https://numberdb.org/` fetches a page
from outside this network and answers whether the site is actually serving.

## The rule against concurrent runs is now a lock

The note above said "one thing at a time on that server". It was ignored
twice, on the same day, by the person who wrote it -- once by starting an
audit while the suite ran, once by starting the suite while an audit ran. Both
times the load average passed 70, sshd stopped completing handshakes, and
access took between fifteen and sixty minutes to come back. The site kept
serving throughout; only administration was lost.

A rule that has to be remembered at the moment of temptation is not a control.
`agents/sage.sh` now takes an exclusive `flock` on the server for the life of
the run, so a second one waits instead of starting, and registers a cleanup
that removes the container by name -- because a `timeout` on the near side
kills the ssh and never the work, which is how the abandoned processes arose
in the first place.

If a run reports "another run held the lock for an hour", something really is
stuck: `docker ps --filter name=numberdb-agent-run` names it.

## `/app` on `sys.path` shadows the client: the site is also a package called `numberdb`

What happened: one script wanted both Django (to read a draft's stored tree
byte for byte) and the client (to write it back through the API). After
`sys.path.insert(0, '/app')` and `django.setup()`, `import numberdb` returned
the Django project package, which has no `configure`, and the script died
with `AttributeError: module 'numberdb' has no attribute 'configure'`. The
two cannot share one process: the settings module is `numberdb.settings`,
so the site's package must own the name while Django is up.

What to do instead: two runs. One with Django prints the document between
markers (`BEGIN-DOCUMENT` / `END-DOCUMENT`) and the head revision's digest;
the near side saves it to a file and mounts it into a second run that has
only the client on the path. That is how T129's Definition was shortened
without touching its 150 entries: the stored tree round-trips exactly, and
`X-Base-Revision` pins the write to the revision that was read.

Evidence: `/tmp/hcp_edit.py` (failed) and `/tmp/hcp_read_tree.py` +
`/tmp/hcp_write_doc.py` (worked), 2026-09-01.

## `write_table` works from outside now

The note above about `POST /api/table/<tid>` answering 403 to a valid key
is history: the `@csrf_exempt` fix was deployed, and on 2026-09-01 the same
route accepted a full document for draft T129 and returned the new revision.
A run may now fix a draft's prose itself, provided it sends the *whole*
document -- `write_table` replaces it, so a document without `Numbers`
would empty the table. Read the stored tree first (previous note).

## The task line handed to stage two can disagree with the proposal it names

What happened: the build was asked for "Hilbert class polynomials, indexed
by fundamental discriminant", and proposal 4's own text says, with reasons,
"all discriminants $D < 0$ with $D = 0, 1 \bmod 4$, not only fundamental
ones". The one-line task was written from the batch's header ("the five
share one enumeration -- fundamental discriminants"), which proposal 4
explicitly excepts itself from. The build followed the proposal's body,
because that is where the decision and its reasons are, and said so in its
report.

What to do instead: when `run.sh build` is given a task, quote the
proposal's own "What has to be decided" section rather than paraphrasing the
batch; and a build that meets a disagreement should follow the body and
report the conflict rather than resolve it silently either way.

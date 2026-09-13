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

## Working in the repository while a campaign runs is not free

What happened: a `git add -A`, run to stage an unrelated change, staged the
build's half-finished generator along with it. `agents/run.sh` refuses to
start on a tree with uncommitted changes -- deliberately, so that what a run
changed is what it committed -- and staged changes count. The critique and
repair of T160 both refused, before writing any log at all, so the campaign
reported "the critique run failed" with nothing to read. The table was left
built and unread.

Two smaller versions of the same thing: editing `agents/campaign.sh` or
`agents/run.sh` while either is executing corrupts the running shell, because
bash reads a script from its open inode as it goes and resumes at a byte
offset into whatever the file now says. Writing the new version to a temporary
file and renaming it over the old one is safe -- the running processes keep
the inode they opened -- and that is how the engine changes were installed
under a running build.

What to do instead: stage by name, never `-A`, while a campaign is running;
and install changes to the runner scripts by rename. If a stage fails with no
log, look at the tree before looking at the agent.

Evidence: `agents/runs/campaign-20260906T132003Z.log` ends "the critique run
failed; the table stands and somebody should look" with no
`*-critique.log` for T160 anywhere, 2026-09-06.

## One minified file made every repo-wide search cost a fortune

What happened: a codex build cost $42.89, and 82% of that -- $35.32 -- was
re-reading its own context on 399 model calls. The context had reached 200k
tokens by call 40 and stayed there. Two ordinary orientation searches were
responsible:

    rg -n "class .*Generator|def publish|def create|X-Draft" -S .
    rg -n "T160|Values of Dedekind zeta functions of totally real cubic" -S .

Each returned over two megabytes. Not because the repository is large: because
`static/vendor/mathjax/tex-svg.js` is **one line of 2,108,617 bytes**, and any
search matching it prints the whole line. Both searches matched it. The rest of
the output was 17 KB and 1.7 KB respectively.

What that costs is not the one command. Tool output enters the context and is
then re-read on every model call for the remainder of the run, so a single
2 MB line early on is billed hundreds of times.

What to do instead: the repository now has an `.ignore` file -- honoured by
ripgrep and fd, and not the same thing as `.gitignore`, because these files
belong in the repository and are only searched by accident. It excludes
`static/vendor/`, `staticfiles/` and the built copies of the client. The two
searches above now return 17 KB and 1.7 KB.

Evidence: `agents/runs/20260906T161625Z-build.log`, 151 commands totalling
3.2 MB of output, two of them 1,048,607 bytes each after truncation; the same
build's session file gives 399 calls at a median context of 188k tokens. The
next codex build, after this, made 117 calls at a median of 111k and cost
$10.85.

## A file deleted in git stays on the server

What happened: a test module was renamed with `git mv`. The code was uploaded
the way everything is uploaded -- `tar c ... | ssh "tar x -C /opt"` -- which
writes the new file and knows nothing about the old one. The suite then found
both, and the fourteen errors were the stale copy calling functions that had
been renamed out of existence.

`scripts/ship.sh` copies the same way, so this is not only about tests: a
module deleted in git remains at `/opt/numberdb-website`, is copied into the
next image built there, and stays importable indefinitely. Nothing has been
bitten by that yet beyond a confusing test run, but the shape of it -- old
code running because nobody removed it -- is worth knowing about before it
matters.

What to do meanwhile: after renaming or deleting a file, remove it on the
server by hand before running anything, and treat an unexplained failure in
a module you have just renamed as this until proved otherwise.

Evidence: `Ran 1400 tests ... FAILED (errors=14)` on 2026-09-06, every error
in `test_search_restatements`, a file that existed only at `/opt`; the local
tree had `test_search_repeats.py` and 1385 tests.

## A test run can make the server unreachable while the site stays up

What happened: `agents/on-server.sh manage.py test numberdb_app` was started
in the ordinary way. Load average reached **83.94** on the one vCPU, and ssh
stopped answering -- "Connection timed out during banner exchange" on every
attempt for about twenty minutes. The SOCKS proxy is an `ssh -N -D` tunnel to
that same host, so it died with it, and from this machine numberdb.org
answered nothing at all. It looked exactly like the site being down.

The site was fine throughout. Asked from the server itself, `https://127.0.0.1/`
and `/T7` both answered 200 in under 60 ms, and every container was up and
healthy. What was saturated was everything *outside* the running containers:
sshd could not complete a handshake, so no tool that reaches the box over ssh
could report anything.

Two things follow. **A test container is not free on this box**: `docker
compose run` starts a second Sage and Django beside the live ones with 961 MB
to share, and a six-second test run costs eight and a half minutes of wall
clock even when nothing goes wrong. Run the suite once, not per module, and
never beside anything else. **And when the box goes quiet, do not conclude the
site is down.** Ask the server: an ssh that eventually connects can curl
127.0.0.1 with a `Host:` header, which separates "the site is broken" from
"I cannot reach the box".

The proxy does not recover on its own. The `ssh -N -D` process stays alive
with a dead connection, still listening on 1080 and timing out every request,
so it has to be killed and started again.

Evidence: load average 83.94/80.28/70.12 at 01:18 UTC on 2026-09-06, six
users, 137 MB free; `docker ps` showing web healthy; localhost 200 while the
proxy returned nothing. The container was removed by hand, after which load
fell to 5.82 within three minutes.

## A `/tmp` Sage wrapper that imports Django needs `/app` on `sys.path`

What happened: a repair run needed `manage.py audit_table T179` after finding
that the local checkout had no Django installed. The first wrapper run through
`agents/sage.sh` set `DJANGO_SETTINGS_MODULE` and called
`execute_from_command_line`, but failed with `ModuleNotFoundError: No module
named 'numberdb.settings'`. The script was mounted and executed from `/work`,
so Python's script directory was `/work`; the application code in the
container was not importable until the wrapper added `/app` to `sys.path`.

What to do instead: when a temporary script run under `agents/sage.sh` needs
to import the Django project, put `sys.path.insert(0, '/app')` before importing
Django or calling a management command. This is separate from generator runs,
where the client package path is the important one.

Evidence: `/tmp/audit_t179.py`, 2026-09-09, failed before the path insert and
then ran `audit_table T179`, reporting `Nothing to report.`

## Put `/app` before the client path when a Sage wrapper imports Django

What happened: a T218 repair wrapper added both `/app` and
`/app/clients/python` to `sys.path`, but put the client path first. Django then
failed at `django.setup()` with `ModuleNotFoundError: No module named
'numberdb.settings'`, because the Python client package is also named
`numberdb` and shadowed the Django project package.

What to do instead: for a temporary script under `agents/sage.sh` that imports
Django, put `sys.path.insert(0, "/app/clients/python")` first if the client is
needed, then `sys.path.insert(0, "/app")`, so `/app` ends up before the client
path. A wrapper that only imports Django does not need the client path at all.

Evidence: `/tmp/render_t218_preview.py`, 2026-09-11, failed with the client
path first and rendered `/preview/T218` after `/app` was made first.

## `agents/sage.sh` mounts extra files rather than passing arguments

What happened: `agents/sage.sh agents/table-build/dry_run.py /tmp/boole_generate.py`
copied both files to `/work`, but executed only `/work/dry_run.py`. The
first run failed before that mattered, because `dry_run.py` imports its
sibling `check.py` and only the main script plus the generator had been
mounted. Mounting `check.py` as a third file would make the import work, but
`dry_run.py` would still receive no command-line path to the generator.

What to do instead: run a tiny wrapper under `agents/sage.sh` that puts
`/work` on `sys.path`, imports `dry_run`, and calls
`dry_run.main(['/work/generate.py'])`. Mount the wrapper, `dry_run.py`,
`check.py`, and the generator. That still uses the shared dry-run checks and
keeps the computation in the throwaway Sage container.

Evidence: the Boole polynomial draft T184, 2026-09-09, used
`/tmp/run_boole_dry.py` after the direct `agents/sage.sh
agents/table-build/dry_run.py /tmp/boole_generate.py` run failed with
`ModuleNotFoundError: No module named 'check'`.

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

## The Sage helper image may not contain the Django app

What happened: after filling draft T221, the required
`manage.py audit_table T221` check could not be run from the local checkout,
because the host Python had no Django installed. The usual fallback was a
temporary wrapper through `agents/sage.sh`, but the container used for this
run did not have `/app` at all. Its root contained `/work` and
`/opt/numberdb-client`, so a wrapper changing into `/app` failed before it
could import Django. A filesystem probe inside the same helper image confirmed
that only the client package was present, not the website checkout.

What to do instead: do not assume `agents/sage.sh` can run Django management
commands. If `/app` is absent, use a runner image or sanctioned helper that
contains the site code and database configuration, or record that the audit
could not be run from this environment. The table build can still use the
client-side dry run, `verify()`, and API read-back checks, but that is not the
same as `audit_table`.

Evidence: T221 build, 2026-09-13. `python3 manage.py audit_table T221` failed
with `ModuleNotFoundError: No module named 'django'`; `/tmp/run_audit_t221.py`
through `agents/sage.sh` failed with `FileNotFoundError: /app`; a probe of
`/`, `/app`, `/work`, and `/opt` inside the helper image showed
`/opt/numberdb-client` and no Django app checkout.

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

## Django scratch scripts under `agents/sage.sh` must put the app before the client

What happened: a repair script for T176 needed to render a private draft as
its owner and call `audit_table`. Run through `agents/sage.sh`, it set
`DJANGO_SETTINGS_MODULE=numberdb.settings.dev` and called `django.setup()`,
but failed with `ModuleNotFoundError: No module named 'numberdb.settings'`.
The wrapper sets `PYTHONPATH=/app/clients/python`, so `import numberdb`
resolved to the client package instead of the Django project. The script had
to run `sys.path.insert(0, "/app")` before importing Django.

A smaller version in the same run: a dry-run guard used
`SEND_T176_REPAIR=1`, but the wrapper only forwards selected environment
variables. The flag never reached the container, so the script printed the
dry run again and wrote nothing. `NUMBERDB_PUBLISH=1` did reach it, because
the wrapper explicitly forwards that name.

What the skill says now: nothing. This is only true of the deployment wrapper.

What it should say: when a scratch script under `agents/sage.sh` imports
Django, put `/app` first on `sys.path` before `django.setup()`. If the script
needs a switch inside the container, use stdin or one of the variables the
wrapper forwards, or change the wrapper deliberately.

Evidence: `/tmp/t176_live.py` and `/tmp/t176_repair.py`, 2026-09-09; the
first failed before the path insert, and the write script stayed in dry-run
mode until it used `NUMBERDB_PUBLISH=1`.

## `agents/sage.sh` setup must not read the key pipe

What happened: filling draft T167 followed the documented shape,
`cat "$NUMBERDB_KEY_FILE" | agents/sage.sh generate.py`, but the script
mounted `/work/generate.py` as a directory rather than as the copied file.
Running the same command without a pipe mounted the file correctly. The setup
`scp` calls were still attached to the script's stdin, so the API-key pipe
could be consumed or disturbed before the final `ssh` command forwarded it to
the container. The failed run also left a directory at the would-be bind-mount
source, and the cleanup used `rm -f`, so a later run reusing the same local PID
mounted that stale directory again.

What to do instead: every setup copy in `agents/sage.sh` must read from
`/dev/null`, just as the setup `ssh -n` calls already do. Its remote temporary
prefix should also be unique per run, and cleanup must remove both files and
directories below that generated prefix. The only command in the wrapper that
may read stdin is the final `ssh` that runs Sage, because that is the one a
fill script expects to receive the key.

Evidence: on 2026-09-09, `agents/sage.sh /tmp/inspect.py
generators/named-euler-products/generate.py` listed `/work/generate.py` as a
file, while `cat "$NUMBERDB_KEY_FILE" | agents/sage.sh /tmp/inspect.py
generators/named-euler-products/generate.py` listed it as a directory. Adding
`</dev/null` to the `scp` command, making the temporary prefix include a
timestamp, and cleaning with `rm -rf` fixed the mounted file before the T167
fill.

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

## `agents/sage.sh` mounts extra files; it does not pass script arguments

What happened: a table-build dry run was started as

    agents/sage.sh agents/table-build/dry_run.py generators/.../generate.py

following the plain-Sage command in the table-building prompt. The wrapper
copied both files to `/work`, but ran only `/work/dry_run.py` with no
arguments. It also did not mount `check.py`, so the first visible failure was
`ModuleNotFoundError: No module named 'check'`; after that, the missing
generator argument would have been next.

What to do instead: for tools that need neighbouring helper modules and
arguments, run a small `/tmp` shim as the wrapper's main script, mount the
helpers and target files beside it, put `/work` on `sys.path`, and call the
tool's `main()` with `/work/...` paths. For `dry_run.py`, that is the shape:

    agents/sage.sh /tmp/run_dry.py agents/table-build/dry_run.py \
      agents/table-build/check.py generators/.../generate.py

where `/tmp/run_dry.py` imports `dry_run` and calls
`dry_run.main(['/work/generate.py'])`.

Evidence: on 2026-09-06, the failed command returned
`ModuleNotFoundError: No module named 'check'`; the wrapper source says
`agents/sage.sh path/to/script.py [more files to mount...]` and the final
remote command runs only `/work/$(basename "$main")`.

## The Sage wrapper's `$$`-based container name can collide after interrupts

What happened: after interrupting a long Sage dry run, a traced smoke test
reached the wrapper's final remote command and then Docker refused to start:

    Error response from daemon: Conflict. The container name
    "/numberdb-agent-run-2" is already in use

In this sandbox, each separate shell command can run with `$$ == 2`, so
`agents/sage.sh` repeatedly chose the same remote copy prefix
`/tmp/agent-run-2.*` and the same Docker container name
`numberdb-agent-run-2`. The wrapper's cleanup hook on the failed traced run
removed the stale container, and the next one-line `agents/sage.sh` smoke
test printed `smoke ok`.

What to do meanwhile: when a one-line Sage smoke test is silent, trace the
wrapper once before assuming the mathematical script is slow. If Docker
reports a name conflict, let the wrapper's own cleanup hook run; do not
remove containers by hand unless a person with server access is deliberately
repairing the environment.

Evidence: 2026-09-06, `bash -x agents/sage.sh /tmp/sage_smoke.py` showed
the final `docker compose run --name 'numberdb-agent-run-2'` command and then
the Docker conflict above; the immediate retry of `agents/sage.sh
/tmp/sage_smoke.py` returned `smoke ok`.

## Some sessions can edit the worktree but not commit

What happened: a stage-two table build was asked to commit every repository
change as it was made. The worktree was writable, but `.git` was mounted
read-only in the Codex sandbox. Staging a documentation-only change failed
with:

    fatal: Unable to create '.git/index.lock': Read-only file system

What to do meanwhile: treat commits as unavailable when `.git` is read-only,
say so in the run output, and keep the file changes as the durable record.
Do not work around it with `git push`, copying a repository elsewhere, or
rewriting `.git`; those would defeat the runner's permission boundary.

Evidence: 2026-09-06, `git add docs/agent-environment.md` failed with the
index-lock error above while file edits under the repository root succeeded.

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

## `/tmp` outlives a run, and `sage.sh` mounts by basename

What happened: this run wrote its draft-creation script as
`/tmp/create_draft.py`. The `Write` tool refused, because a file of that
name from the T128 run still existed and had not been read, and the
`agents/sage.sh` call in the same turn went ahead and executed the *old*
script -- which failed on its own missing input before it could post
anything. Had the old script been self-contained it would have created a
second draft with the previous table's document.

What to do instead: name scratch files after the table or the date
(`/tmp/t130_create.py`), or clear `/tmp/*.py` at the start of a run; and
never put a `Write` and the `sage.sh` call that runs it in the same turn.

Evidence: 2026-09-01, `FileNotFoundError: /work/draft.json` from a script
that this run never wrote.

## The stored tree keeps `Numbers` as a flat list; the API nests it

What happened: the whole-document edit of T130 counted its entries with
`tree['Numbers'].values()` and died, because the tree from
`tree_of(head_revision)` holds `Numbers` as a list of
`{params: {D, s}, number, comment}` records, while `numberdb.table()`
returns the same entries nested by parameter value
(`Numbers['5']['-1']`). Both are the same table; a script that reads one
shape and writes the other should know which it has.

What to do instead: the two-run edit (previous note) round-trips the flat
list untouched, and `write_table` accepted it as is; count with
`len(tree['Numbers'])` on the stored side and by walking the nesting on the
API side.

Evidence: `/tmp/write_doc_t130.py`, 2026-09-01, first attempt
`AttributeError: 'list' object has no attribute 'values'`; second attempt
`906 added` preserved as `906/906 matched`.

## Corpus searches and slugs need no Sage run: `curl` through the proxy does it

What happened: the build of T131 needed the corpus searched for
"regulator", "fundamental unit", and its neighbours, and the slug of every
table it would link to. Each earlier run did that from inside
`agents/sage.sh`, at twenty to thirty seconds a run. `curl -s -G
https://numberdb.org/api/lookup --data-urlencode text=regulator` from this
machine -- `curl` honours the SOCKS proxy that Python does not -- answers in
about a second with `tables`, each carrying `tid`, `title` and `url`, which
is the slug `HREF{...}` needs; `api/table?id=T128` gives a published table's
whole document, and answers "does not exist" for a draft, which is how the
run learned T130 was still unpublished without a key. A lookup by digits is
the same call with the digits as `text`.

The `api/search` route is not this: it is the advanced search and answers
`{"results": [], ...}` to a word. Also, `curl -o /dev/null -w
'%{redirect_url}'` on `numberdb.org/T35` prints nothing -- a T-number is
served directly, not redirected -- so the slug has to come from a search
result, as the skill says.

Evidence: 2026-09-02, this run; every slug in T131's document was read
from `api/lookup` output and `audit_table` reported nothing.

## `already_asked` is throttled after ten names, and this `gh` cannot search issues

What happened: the 2026-09-02 ideas run called `already_asked` seventeen
times in one script. The first ten answered; the rest returned `could not
ask GitHub (HTTPError)`, because the unauthenticated GitHub search API
allows ten requests a minute. The fallback of `gh search issues --repo ...`
does not exist here: this machine's `gh` has only `gh search repos`.

What to do instead: `gh issue list -R numberdb/numberdb-data --state closed
--limit 300 --json number,title` and the same for `open` -- two authenticated
calls that return the whole tracker (81 open, 44 closed today), which is
what `already_asked` searches word by word. Read them. `already_asked` could
go through `gh api search/issues` when `gh` is present, or sleep six
seconds between calls; `run.sh` could fetch the two lists once, as the
notes above already ask.

Evidence: `/tmp/gq_20260902_screen.py` output, 2026-09-02; `gh search
issues` prints `unknown flag: --repo` and lists `repos` as the only
subcommand.

## The anonymous lookup budget is per address and shared by every tool on the machine

What happened: the corpus walk at the start of the run spent the 60
anonymous requests an address gets per hour before the key was set, and
forty minutes later `curl .../api/lookup` -- which the previous note
recommends as the fast way to search -- was refused with `retry_after:
2665`. The sign test that needed it went through the Python client with
`NUMBERDB_API_KEY` set instead. `curl` can carry the key too, but only as a
header on the command line or from a file, and neither is the "pipe it, never
an argument" shape the run is held to; the client reading it from the
environment is.

What to do instead: set the key in the environment for the whole run before
the first `numberdb.table()` call, and treat `curl` lookups as anonymous and
metered.

## `agents/sage.sh script | tail -N` throws away the half that matters

What happened: the first check run was piped through `tail -150`; it had
262 lines, and the Gauss-Legendre and Hermite sections -- the ones with the
published-value comparisons -- were the ones lost, so the run had to be
repeated. Same lesson as the pipeline note above, in a different shape.

What to do instead: `agents/sage.sh script.py > /tmp/out.txt 2>&1`, then
`grep -c PASS` and `grep FAIL | grep -v 'must fail'` on the file; the file
is also what the batch quotes from.

## `dry_run.py` measures the ball's printed form, not the digits that will be written

What happened: the dry run of the Gauss-Legendre generator reported
"longest 139 characters at expression=x,k=8,n=16, block 174.5 KB, OVER THE
TARGET". The same 930 entries passed through `numberdb._write.to_text` at
100 digits measure 104 characters and 129.1 KB. `check.measure` takes
`str()` of whatever `value()` returned, and a 397-bit `RealBall` prints
about 120 digits and a radius, so a table of balls is overstated by a
third and a range decision was nearly taken on the wrong number.

What to do instead: `dry_run.py` should write each value with `to_text(value,
digits)` before measuring, as `publish()` will. Until then, re-measure
through `to_text` (`/tmp/gl_measure.py`, ten lines) before believing OVER
THE TARGET on a table of balls; exact tables are measured correctly.

Evidence: 2026-09-02, the dry run and `/tmp/gl_measure.py` on the same
generator: `{'entries': 930, 'longest': 104, 'block_kb': 129.1}`.

## Editing a draft's prose after the fill: read the tree with Django, write the document with the client

Repeated here because it was needed again and the earlier notes say it in
three pieces. `manage.py audit_table` found two things in T132's
Definition after the fill; fixing them means sending the *whole* document,
`Numbers` included, to `POST /api/table/132` with `X-Base-Revision` set to
the head digest. `/tmp/gl_read_tree.py` (Django in the throwaway, prints
the flat tree between markers and the digest) and `/tmp/gl_write_doc.py`
(client only: the repository's `table.yaml` plus the stored `Numbers`,
posted with the digest) are the pair; they cannot share a process because
the site is also a package called `numberdb`.

## A bug in somebody else's data goes in docs/external-bugs.md

Runs turn these up regularly -- a swapped OEIS label, a value that disagrees
with a published table. They are worth keeping and worth reporting, but not
one at a time and not by the run that found them: a claim that somebody else's
data is wrong should be checked by a person before it is sent.

Write the finding in `docs/external-bugs.md`, in the format at its head, and
leave the reporting to a person with the batch.

## The slug of a draft is not in any search result; read it with Django in the throwaway

What happened: T133 links to T132, which is still a draft. The skill says
to take a slug from `search_text(...).tables[0].url`, and a draft is in no
search result and `numberdb.table('T132')` carries no address. Six lines
through `agents/sage.sh` -- `sys.path.insert(0, '/app')`, `django.setup()`,
`Table.objects.get(tid_int=132).url` -- printed it
(`Nodes_and_weights_of_Gauss_Legendre_quadrature`), and `slug_for(title)`
from `numberdb_app.editing` said in advance what the new table's own address
would be, which the creation answer then confirmed. The creation answer's
`url` is the other place it exists; save it.

What to do instead: `/tmp/sp_slug.py` is the script; or have the `offer`
and `create` answers written to a file the next script can read.
`audit_table --links` then checks that a draft-to-draft link resolves.

## `cd /tmp && agents/sage.sh ...` is "No such file or directory"

What happened: the first run of the Hermite checks chained the DLMF
extraction and the Sage run in one shell line beginning `cd /tmp`, and the
`agents/sage.sh` half failed with exit 127 before doing anything. The
working directory is reset for every Bash call, and a `cd` inside a compound
command changes it for the rest of that command, so a relative path to the
runner stops resolving. The same line with
`/home/.../numberdb-website/agents/sage.sh` worked.

What to do instead: call the runner by absolute path, always; the relative
form works only until somebody puts a `cd` in front of it.

## `WebFetch` is refused for Wikipedia in a build run; `curl` through the proxy is not

What happened: `WebFetch` on the Gauss–Hermite quadrature article answered
"Unable to verify if domain en.wikipedia.org is safe to fetch", although the
allowlist names the domain. The raw wikitext fetched by `curl` (which honours
the SOCKS proxy) was already in `/tmp/gh_wiki.txt` from an earlier run, and
was enough. OEIS also answered `error code: 502` for some minutes in the
middle of the run; the b-files an earlier run had saved to `/tmp` carried
the comparison.

What to do instead: fetch sources with `curl` into `/tmp` under the table's
prefix, once, and read the files; a run that depends on the site answering at
the moment of the check is a run that stops for somebody else's outage.

## `dry_run.py` does not say how many digits the balls support; the guard was nearly too small and nothing printed said so

What happened: the Gauss–Laguerre generator was written with the same
64-bit guard as the Legendre and Hermite ones, whose worst balls support
110 digits. The dry run reported "every value is exact, or carries its own
error bound" and would have let the table be filled. Only the wrapper
(`/tmp/la_dry.py`) that also prints the worst relative radius showed
$3\cdot10^{-104}$ at $n = 30$, $k = 21$: a hundred digits supported with
three to spare, because $L_{31}$ evaluated at a node near 40 loses about
fifteen digits to cancellation. The guard went to 128 bits (radius
$1.6\cdot10^{-123}$) before anything was sent. `numberdb` would have
refused to *write* more digits than the ball supports, so nothing wrong
could have reached the table; but a table published with three spare
digits is one the next family of the same shape overruns.

What to do instead: `dry_run.py` should print, for a table of balls, the
worst relative radius and where it is, beside the size measurement -- the
same ten lines as the wrapper -- so the guard's own comment ("measured:
...") can be written from the run that measured it. Until then, every
build of a `proven` table should use a wrapper like `/tmp/la_dry.py` and
quote the number in the generator.

Evidence: `/tmp/la_dry_out.txt`, 2026-09-03, first run: `worst relative
radius: (3.03e-104, '30,21,w')`; second run with `WORKING_GUARD = 128`:
`(1.63e-123, '30,21,w')`.

## A chain of `sage.sh` runs in one shell command can stall; run the writes alone, with `NUMBERDB_TIMEOUT` set, and check the digest before retrying

What happened: after filling T136, one Bash command chained four
`agents/sage.sh` runs: read the stored tree with Django, write the
shortened document back through the client, audit, verify. The read, which
takes 25 seconds on its own, returned after about nine minutes, and the
write that followed was killed by the Bash tool's ten-minute limit with an
empty output file. Nothing said why: the site answered in a second
throughout, the lock message ("another run held the lock") never printed,
and a fresh read a minute later took 25 seconds and showed the head
revision unchanged. The write was retried alone and landed in 26 seconds.
The same shape as the "timeout kills the ssh, not the work" note above; the
new part is that a stall can sit in front of the step that matters and eat
its budget, and that a killed write leaves no way of knowing from this side
whether it happened.

What to do instead: one `sage.sh` run per Bash call for anything that
writes, with `NUMBERDB_TIMEOUT` set to a few minutes rather than the default
half hour, so a stall fails here rather than at the tool's limit; and after
any interrupted write, read the head revision's digest before retrying, and
retry only with `X-Base-Revision` set to what was read, so a write that did
land is refused rather than repeated.

Evidence: 2026-09-03, the chained command (`read exit 0` printed, then the
tool's `Command timed out after 10m 0s`); `/tmp/gk_tree2_out.txt` with the
old digest `6848c4fd…` 25 seconds later; `/tmp/gk_write_out.txt` on the
retry, `revision = 1f2f43a5…` after 26 seconds.

## Testing a `Programs` snippet under `sage -python`: preparse it and hand it `Integer`

What happened: the Sage program offered under T136's `Programs` uses the
preparser's syntax (`R.<x> = QQ[]`, `x^2`), which `sage -python` does not
read. `sage.repl.preparse.preparse` turns it into Python, but the result
calls `Integer(7)` for every literal, and the namespace it runs in has to
supply `Integer` (from `sage.rings.integer`), `QQ`, `matrix`, `vector`,
`RealIntervalField` and `PolynomialRing` by hand -- the first attempt died
with `NameError: name 'Integer' is not defined`. `legendre_P` is not
importable in the throwaway at all (`sage.functions.orthogonal_polys`
raises `AttributeError` before Sage is fully initialised), so the test
substituted Bonnet's recurrence for that one name and said so. The rest of
the program ran as written and reproduced $x_1$, $w_1$, the central weight
and $E_8$.

What to do instead: `/tmp/gk_programs.py` is the harness -- read the
`code:` block out of `table.yaml`, preparse, run it in a namespace built
from named imports plus `Integer` (and `RealNumber` if the program has a
decimal literal), and print the values the program's comments claim. A
name the throwaway cannot import is a limitation of this environment, not
of the program; substitute it, and say in the report which name it was.

## `WebFetch` is refused for numberdb.org too; the skill is in the repository

What happened: the build prompt opens with "Read <https://numberdb.org/skill>
first", and `WebFetch` on that address answered "Unable to verify if domain
numberdb.org is safe to fetch", as it did for Wikipedia in the Hermite run.
The skill is the file `.claude/skills/numberdb-table/SKILL.md` in this
repository, which is what the site serves; reading it there took one call and
no network. `curl` through the proxy reaches the site as before, and was
enough for every corpus lookup and stored-table fetch this run made.

What to do instead: read the skill from the repository, and let the prompt
say so; keep `WebFetch` out of a build run's plan and fetch outside sources
with `curl` into `/tmp` under the table's prefix.

## Rendering a draft's page as its owner sees it, without a session

What happened: a critique has to read the *rendered* page, and a draft is
Not Found to an anonymous `curl`. The T136 and T137 critiques rendered it
in the throwaway with Django's `RequestFactory`: `django.setup()`, get the
`Table` and its `created_by`, build `rf.get('/T137', HTTP_HOST=
'numberdb.org')`, attach `request.user = table.created_by` and an unsaved
`SessionStore()`, and call `views.table_by_tid(request, 'T137')`. The
response body is the page the author sees, `status` 200, nothing is
written, and no login or cookie is involved. The same script runs
`call_command('audit_table', tid, '--links')` and prints `tree_of(head)`
between markers, so one run gives audit, document and rendering.

What to do instead: the script only existed as `/tmp/crit136.py` and was
copied with `sed s/T136/T137/`; it should live in the repository as
`agents/render_draft.py` or take the tid from the environment. Split the
output on the `=== HTML ===` markers rather than reading it whole: the
page is 750 KB and the tool result is truncated at about 100 KB.

Evidence: `/tmp/crit137.py` and `/tmp/crit137_out.txt`, 2026-09-03; the
three `label:`/`properties:` lines at the top of the HTML block are the
view's stdout noise, not part of the page.

## KnotInfo's site is unreachable from here, but its data is a `pip download` away; the container has no SnapPy

What happened: the 2026-09-03 ideas run needed KnotInfo as the independent
copy of every knot invariant. `curl https://knotinfo.math.indiana.edu/`
through the proxy returns no status at all (`000`), and
`screen.source_names_it` reports `URLError`, so the site cannot be cited
through the screen. `pip download --no-deps --no-binary :all:
database_knotinfo` from this machine, through the same proxy, fetched the
16 MB sdist in seconds; it contains
`database_knotinfo/csv_data/knotinfo_data_complete.csv` (12966 knots to 13
crossings, 248 pipe-separated columns, header row then a description
row) and `linkinfo_data_complete.csv`. That file was the check for all 249
knots. The Sage behind `agents/sage.sh` has neither `snappy` nor
`database_knotinfo` (`ModuleNotFoundError` for both), so hyperbolic
volumes cannot be computed in a run at all, and `sage.knots.knotinfo`
imports but cannot answer.

What to do instead: fetch published datasets as packages from PyPI when
their site is dark; keep the sdist in `/tmp` under the batch's prefix. A
build of a volume table needs SnapPy on the builder's own machine, and the
proposal says so.

Evidence: `/tmp/kn_pkg/database_knotinfo-2026.9.1.tar.gz`; probe output
`snappy NOT importable: ModuleNotFoundError`, `database_knotinfo NOT
importable: ModuleNotFoundError`, 2026-09-03.

## `env | grep -i numberdb` prints the key into the transcript log

What happened: the 2026-09-03 ideas run listed its environment with
`env | grep -i -E 'proxy|numberdb'` to see the proxy and the key file's
name, with a `sed` meant to mask anything containing `KEY`. The mask did
not match the line `NUMBERDB_API_KEY=...` (it looked for `KEY` after the
`=`), and the key went into the tool output, hence into
`agents/runs/<started>-ideas.log` and the campaign log, which `tee` was
holding open. Both are under `agents/runs/*` and gitignored, so nothing
tracked carries it (checked with `grep -rlF "$(cat "$NUMBERDB_KEY_FILE")"`
before committing), and the files are readable only by the same user, as
`/proc/<pid>/environ` already is. Rewriting a log that `tee` still has open
would lose the rest of the run, so they were left as they are.

What to do instead: never grep the environment for values; `env | cut
-d= -f1 | grep -i numberdb` shows which variables are set and nothing
else. A person may want to scrub the two logs of 2026-09-03 after the
campaign ends, or rotate the key.

Evidence: `agents/runs/20260903T030506Z-ideas.log`,
`agents/runs/campaign-20260903T030422Z.log`; `.gitignore` lines 162-163.
It happened again in the T142 repair run of 2026-09-03 (run
`20260903T125530Z`), with a `sed` mask on "key" after the `=` that
matched the `NUMBERDB_KEY_FILE` line and not `NUMBERDB_API_KEY`: the same
mistake in a different spelling, so the rule is to never print values from
the environment at all, masked or not. That run's log is a third one to
scrub, and a third reason to rotate the key.

## `audit_table --links` reports KnotInfo as `URLError`; that is this network, not the link

What happened: the audit of draft T138 returned one finding,
`Links[KnotInfo] answered URLError: https://knotinfo.math.indiana.edu/`.
The note above says the site gives `curl` no status from here; the audit
runs on the same server and sees the same thing. The link is the right one
-- KnotInfo is the reference every knot table cites, and its data reached
the build as the `database_knotinfo` package -- so the finding was left
standing rather than the link removed.

What to do instead: a reviewer reading that audit line should treat it as
the known outage of one route rather than a dead link, and check the
address from another network before acting on it. The dry run and the fill
of T138 needed one wrapper each around `agents/sage.sh`, as the T128 note
says (`/tmp/kn_dry.py`), and the `Knots().from_table` computation of all
249 knots took about fifteen seconds in the throwaway, so nothing else in
this environment stood in the way of a knot table.

## An edit sent with `agents/api_edit.py` is recorded as assisted but the history shows no tool name

What happened: the T138 repair's two revisions, sent through
`edit_over_api` with `assistant='Claude Fable 5.1'`, print `assisted_by`
as empty in the throwaway (`rev assisted_by` blank, where the build's
revision shows `claude (agent run 20260…)`). `_produced_by` in `api.py`
stores the `X-Produced-By` header as sent, `assisted by Claude Fable 5.1`.
The trust counter in `permissions.py` looks for `assisted by` with
`icontains`, so the revision counts as assisted there. The display
property `TableRevision.assisted_by` in `models.py` splits on
`', assisted by '` -- with a leading comma, because the package writes
`<generator>, assisted by <tool>` -- and returns nothing when the marker
stands alone at the start of the string. So `revision-history.html` and
`entry-blame.html` print no "with …" note for these edits, which is the
disclosure they exist to make. The T137 repair, sent the same way, will
show the same.

What to do instead: nothing for a run; the record is right and the counter
sees it. For a person: either have `assisted_by` accept the marker at the
start of `produced_by` as well as after a comma, or have `api_edit.py` send
`edit, assisted by <tool>`; one line either way, with a test that a bare
`assisted by X` renders as "with X".

Evidence: `/tmp/crit138_after.txt` and `/tmp/crit138_final.txt`, 2026-09-03;
`numberdb_app/models.py` `assisted_by`, `numberdb_app/api.py`
`_produced_by`, `agents/api_edit.py` `edit_request`.

## A repair edits the live document; the `table.yaml` beside the generator is not touched unless the repair does it

What happened: the T140 repair changed four passages of the draft through
the API, and then found that `generators/conway-polynomials-prime-knots/
table.yaml`, the document the draft was created from, still carried the old
text. The T138 and T139 repairs made the same kind of edit and left their
`table.yaml` files as they were: on 2026-09-03 both
`generators/alexander-polynomials-prime-knots/table.yaml` and
`generators/jones-polynomials-prime-knots/table.yaml` still cite `issue91`,
which the live T138 and T139 no longer do, and the Alexander file still has
the Definition without Perko. `verify()` compares values, not prose, so
nothing reports the drift; a later `create` from the file would bring the
repaired findings back.

What to do instead: a repair that changes a table's prose changes the
generator's `table.yaml` in the same commit, and checks the two agree
section for section (a dozen lines: `GET /api/table?id=<TID>` against
`yaml.safe_load` of the file, `Numbers` excluded). The T140 repair did this;
the T138 and T139 files are left for a person, since the live documents are
the ones under review and the two repairs are already committed.

Evidence: `/tmp/t140_edit.py`, 2026-09-03; `grep -n issue91
generators/*/table.yaml`.

## SnapPy installs on the runner's machine in a minute; the container never needed it

What happened: the 2026-09-03 ideas run wrote that the volume table "cannot
be built here" because the Sage behind `agents/sage.sh` has no SnapPy.
`python3 -m pip install --user snappy` on this machine, through the proxy
in `ALL_PROXY`, installed SnapPy 3.3.2 with spherogram in about a minute
(manylinux wheels for the local Python 3.10). Triangulating all 249
exteriors from Sage's braid words, taking quad-double shapes, and checking
isometry against SnapPy's own table and KnotInfo's diagrams took 20 s
locally (`/tmp/hv_export2.py`); the gluing equations and shapes went to the
container as a 1.3 MB JSON mounted as an extra file to `agents/sage.sh`,
and everything proven happened in arb there. The generator itself calls
SnapPy, so a person running it needs `sage -pip install snappy`; the run's
fill and dry run substituted the JSON for that call (`/tmp/hv_fill.py`,
`/tmp/hv_dry.py`).

What to do instead: when a proposal says a package is missing from the
container, try `pip install --user` locally first; the local Python is a
fine place for a library's combinatorics, and the container is for what
must be certified with the site's Sage.

Evidence: `python3 -c "import snappy; print(snappy.__version__)"` -> 3.3.2;
`/tmp/hv_export2.py` output, 2026-09-03.

## `dry_run.load` does not register the module it loads

What happened: the volume generator's data source had to be replaced for
the dry run. `agents/table-build/dry_run.py` builds its module with
`importlib.util.module_from_spec` under the name `generator_under_test` and
never puts it in `sys.modules`, so `sys.modules[type(gen).__module__]`
raised `KeyError`. Patching the function's globals worked:
`type(gen).value.__globals__['triangulation'] = from_export`. Also worth
knowing: the dry run computes every entry, and a wrapper that then loops
over `gen.value` for its own checks computes them all again -- the volume
dry run took seven minutes for that reason, where the fill took four.

Evidence: `/tmp/hv_dry.py`, 2026-09-03, its first traceback and the second
run's output.

## Journal PDFs are not fetchable from here, so a citation's internal numbering goes unchecked

What happened: the T141 critique offered a reference for Thurston's
trichotomy with a corollary number, "Bull. Amer. Math. Soc. 6 (1982),
357–381, Corollary 2.5". The repair wanted to read the page before writing
the number in. `curl` through the proxy to the AMS PDF answers 403 with an
HTML body, and Project Euclid's download route answers 200 with a 1 KB HTML
page, not the PDF. The reference went in with the bibliographic data only,
which is settled, and without the corollary number, which was not checked.

What to do instead: cite a reference at the level you could verify. A
person with a library login can add the theorem number afterwards; a wrong
one is worse than none. `pdftotext` is on this machine if a PDF ever does
arrive.

Evidence: `/tmp/thurston1982.pdf` (both attempts, HTML), 2026-09-03.

## A Sage run that times out prints nothing, and two of them took the proxy down for twenty minutes

What happened: three probes for the Gauss-sum table (T142) were killed at
`NUMBERDB_TIMEOUT` (1800 s, then 1700 s) inside a loop whose cost per
entry had not been measured -- Sage's `minpoly()` in a field of degree
1012, then an $n^2$ overlap count over a thousand balls. Each run's output
came back empty apart from the lines printed before the slow loop, because
the container's stdout goes through `grep -viE` in `agents/sage.sh`, which
block-buffers when its output is a file, so `sys.stdout.flush()` in the
script changes nothing that reaches this side; the traceback of a run that
*dies* arrives, the progress of a run that is *killed* does not. During the
third run `curl https://numberdb.org/` through the proxy answered `000` in
60 s while `r.jina.ai` fetched the site in 20 s: the box was loaded, the
ssh tunnel the proxy rides on stopped answering, and it came back on its
own about twenty minutes after the run was killed, as the notes above say
it does.

What to do instead: time the worst entry in a two-minute run before looping
over a family (the fourth probe did, and the whole table then took 47 s);
set `NUMBERDB_TIMEOUT` to a few minutes for a probe, not the default half
hour; and have `sage.sh` run `grep --line-buffered` and `sage -python -u`,
so a killed run still shows how far it got. A `137` exit from the runner is
the `docker rm -f` in its cleanup, not necessarily the OOM killer.

Evidence: `/tmp/gs_probe_out.txt`, `/tmp/gs_probe2_out.txt` (exit 137),
`/tmp/gs_probe3_out.txt` (exit 124), the `curl` line `home 000 in
60.058028s` and `jina 200 in 20.17s`, 2026-09-03.

## The deployed client refuses every complex ball under `proven`; fixed in the repository, not deployed

What happened: filling T142 stopped at its first entry with "rigour is
'proven', and this value carries no error of its own", because
`_carries_its_own_error` in `clients/python/numberdb/_generate.py` looked
for real endpoints only (`agents/lessons/PROPOSALS.md` has the lesson). The
fix and its tests are committed here; the container mounts the client from
the deployed image at `/app/clients/python`, so a run cannot use the fix
until somebody deploys. The fill worked by reassigning
`numberdb._generate._carries_its_own_error` in `/tmp/gs_fill.py` before
`publish()`, which is the shape for any run that meets a client bug before
the next deploy.

Evidence: `/tmp/gs_fill_out.txt`, first and second runs, 2026-09-03; commit
"a complex ball carries its error in its parts".

## The LMFDB sometimes answers `curl` through the proxy with a reCAPTCHA page, and sometimes with the page

What happened: the T142 critique could not compare comment (12) with the
Conrey knowl it cites, because `curl` through the proxy to
`lmfdb.org/knowledge/show/character.dirichlet.conrey` answered a reCAPTCHA
page, and the 2026-09-03 ideas run met the same gate on the per-character
calculators. Three hours later the T142 repair fetched the same knowl and
`/Character/Dirichlet/7/2` the same way and got both pages whole (status
200, 28 KB and 51 KB, the knowl's full definition in the text). Both pages
carry the word reCAPTCHA in an embedded script even when they are not the
gate, so the word is not the test.

What to do instead: test for the content you came for (the knowl's
definition, the calculator's form), not for "reCAPTCHA"; if the gate is up,
try again later in the run rather than recording the page as unreachable.
The knowl's definition agrees with T142's comment (12), so that comparison
is done and need not be repeated.

Evidence: `agents/critiques/T142.md`, last bullet of "Noting only";
`/tmp/t142_knowl.html`, `/tmp/t142_knowl2.html`, 2026-09-03.

## A key reaches `curl` on stdin with `-K -`, which is the pipe shape the run is held to

What happened: the T143 build needed the stored digits of draft T142 as an
outside check, and a draft is served by `api/table` only to a request
carrying its owner's key. The note above says `curl` can carry the key only
as a header on the command line or from a file. `curl -K -` reads its
configuration from stdin, so

    printf 'header = "Authorization: Bearer %s"\n' "$(cat "$NUMBERDB_KEY_FILE")" | curl -s -K - 'https://numberdb.org/api/table?id=T142' -o /tmp/js_T142.json

fetches the draft (200, 168 KB) with the key never on a command line and
never in a file in the repository; it goes through the proxy like every
other `curl`. The same shape works for any authenticated GET a run needs
without a Sage round trip.

## `_reference_href` promises `?entry=x#x` for a same-table `#x` and returns `?entry=x`; and a parameter `comments` key is accepted and never rendered

What happened: the T143 critique found two site-side gaps behind two
table faults. `views._reference_href`'s docstring says `#CL` becomes
`?entry=CL#CL`; the code returns the query alone, so a same-table `HREF{#x}`
can never scroll to an anchor and always asks the server for entry `x`.
Whether an in-page anchor should be reachable through `HREF` at all is a
design question -- the docstring says these are entry addresses -- but the
docstring and the code should agree. Separately, `validate.py` lists
`comments` in `KNOWN_ANNOTATIONS` and the parameter renderer reads `title`,
`display` and `constraints` only, so a `comments` key under a parameter is
stored and shown nowhere, on the page or in the editor. T142 and T143 were
the only tables carrying it; T143's is moved into Comments by the repair,
T142's is still there.

What to do instead: for the table, write `CITE{label}` or nothing (lesson in
`agents/lessons/PROPOSALS.md`). For the site, either render a parameter's
`comments` under the parameter line or have `audit_table` report a
parameter key nothing reads; and make `_reference_href` do what its
docstring says or say what it does.

Evidence: `agents/critiques/T143.md`, findings 1 and 2; `/tmp/audit143_out.txt`
2026-09-03: the repaired T143 renders with no `?entry=CL`.

## A run that dies between writing its generator and creating its draft leaves a generator claiming a T-number it never got

What happened: the Kloosterman build of 2026-09-03 found
`generators/dirichlet-l-values-positive-integers/generate.py` untracked in
the working tree, with `table = 'T144'` in it and no `table.yaml` beside
it. `api/table?id=T144` answered "does not exist", which a draft also
answers to an anonymous request, so the file looked like a finished
proposal 3. Creating the Kloosterman draft then returned `tid = T144`: the
earlier run had written the number it expected and stopped before the
creation call, so no L-values draft exists and the number now belongs to
another table. The Kloosterman generator had done the same thing in the
other direction -- it was written with `T145` as a guess and had to be
edited after the answer came back.

What to do instead: a generator carries no T-number until the creation
answer supplies one (write `TBD`, which `dry_run.py` accepts, and let the
fill script refuse a mismatch, as the `*_fill.py` scripts already do); a
stage-two prompt that asks "which proposals have a generator" should also
ask whether the generator's table exists, with the key, before counting
the proposal as built; and a run that ends early should commit what it has
with a note saying the draft was not created. The L-values file is left
untouched for a person: it is somebody else's uncommitted work, and its
tid line is wrong.

Evidence: `git status` at the start of the run (`?? generators/dirichlet-l-values-positive-integers/`),
`grep -n T144 generators/dirichlet-l-values-positive-integers/generate.py`,
`/tmp/kl_create_out.txt`: `tid = T144`, 2026-09-03.

## LMFDB's Kloosterman calculator answered eight of ten `curl` requests today, and the two that failed left no page at all

What happened: `Character/calc-kloosterman/Dirichlet/<p>/1?val=<a>,1`
answered eight values with ten decimals in two batches of four and six,
and `5/1?val=1,1` and `13/1?val=1,1` in the second batch answered nothing
that matched the value pattern -- presumably the reCAPTCHA gate the notes
above describe, arriving mid-batch. The eight were enough for the outside
check and are in T144's rigour details.

What to do instead: as the note on the character calculators says, a
handful of values per batch, saved to `/tmp` as they arrive, and do not
count a blank answer as a disagreement.

Evidence: the shell output of the two `curl` loops, 2026-09-03; `LMFDB =
{...}` in `/tmp/kl_probe.py` holds the eight.

## zbMATH answers through the proxy, and its reviews are enough to confirm a citation but not always a theorem's scope

What happened: the T144 critique proposed attributing the distinctness of
the $K(a;p)$ to Fisher (1992) and Wan (1995) and could not reach a source.
`curl https://zbmath.org/?q=au%3AFisher+ti%3Adistinctness+kloosterman`
answered through the proxy with the full record and review: both papers
exist with the titles, journals and pages the critique gave. But the
reviews state the results for $p$ "sufficiently large", so the question the
critique actually asked -- does it hold for every prime? -- is not settled
by them, and the repair left the sentence scoped to the table.

What to do instead: use zbMATH from a run to confirm that a reference
exists and what it is called; treat a review's statement of a theorem's
hypotheses as the strongest thing a run can claim from it, and leave the
rest for a person with the paper.

Evidence: `/tmp/zb_fisher.html`, `/tmp/zb_wan.html`, 2026-09-03;
`agents/critiques/T144-repaired.md` item 3.

## The orphaned L-values generator was taken over, and the stage-two test is "does its table exist", not "does a file exist"

What happened: the stage-two prompt of 2026-09-03 asks for the
highest-ranked proposal "that no generator in generators/ answers yet".
`generators/dirichlet-l-values-positive-integers/generate.py` existed,
untracked, with `T144` in it, from the run that died before creating its
draft (the note above). Read literally the prompt would have skipped
proposal 3 and built proposal 5. This run listed the unpublished tables
with Django (`/tmp/lv_drafts.py`: T136, T142, T143, T144 -- the four
`drafts_held` the Kloosterman creation answer reported), found no
L-values table, and took the file over: `TBD` in place of `T144`, the dry
run and the outside checks it had never had, then the draft, which
became T145. The earlier note said the file was "left untouched for a
person"; the person's campaign asked for the next unbuilt proposal, and
that was this one.

What to do instead: the stage-two prompt should say "no *table* answers
yet", and the check is one Django query for unpublished tables (or the
`drafts_held` count from the last creation answer) rather than `ls
generators/`. A run that inherits such a file owes it the whole order of
work, since nothing in it was checked by the run that wrote it.

Evidence: `git status` at the start of the run, `/tmp/lv_drafts.py`
output ("T145 exists: False"), `/tmp/lv_create_out.txt`: `tid = T145`,
`drafts_held = 5`.

## T145 links to draft T142; publish the Gauss sums first

T145's closed-form formula and its Similar tables link
`Gauss_sums_of_primitive_Dirichlet_characters`, which is draft T142.
`audit_table` reports nothing, by design (the note on T144 above), and
the link answers 404 until T142 is public. The same publishing-order
decision as for T144, for the same reason: the closed form is where
those numbers are used. T145's outside checks used T142's stored digits
through the API with the key (`/tmp/lv_T142.json`), so the two tables
have been checked against each other in both directions.

## A whole-document write stores `Numbers` in the shape it was sent, and the review diff does not mind

What happened: the T145 repair read the draft through `api/table`, which
nests `Numbers` by parameter value, changed six sentences and wrote the
document back as it came. Before the write `tree_of(head_revision)` gave
`Numbers` as the flat list the fill had stored (the note on T130 above);
after it, the head's tree holds the nested dict. A check script written
against the first shape died on the second with `'list' object has no
attribute 'items'`, and its successor died the other way round. The
reviewer's view is unaffected: `flatten_entries` gives 503 identities for
both revisions and `changed_params` between them is empty, so the queue
shows the prose changes and no entry.

What to do instead: a script that reads the stored tree should accept both
shapes, and a run should not read a shape flip in the revision content as
a rewritten table. One more thing met on the way: `cat "$NUMBERDB_KEY_FILE"
| python3 - <<'EOF'` sends the *script* on stdin and the key nowhere, so
the request goes out anonymous and a draft answers "does not exist"; pipe
the key into a script file, `cat "$NUMBERDB_KEY_FILE" | python3 script.py`,
which is the shape `agents/sage.sh` takes as well.

Evidence: `/tmp/repair145_check.py` and `/tmp/repair145_audit.py` output,
2026-09-03: "stored Numbers shape: dict", "previous revision: 8b1a2cb8…
shape list", "flatten before/after: 503 503", "changed_params between
them: 0".

## The draft ceiling of fifteen is deployed; a sixth draft went through with nine to spare

What happened: the T146 build began with zeta3 holding five drafts (T136,
T142 to T145), which is the number the run prompt still gives as the
limit ("may hold up to five drafts"). `permissions.py` says fifteen since
commit 93f0ee8, and whether that commit was deployed could not be read
from here. The creation call was the test: it answered `drafts_held = 6`,
`drafts_remaining = 9`. The anonymous lookup budget, on the other hand,
was already spent when the run started -- the first sixteen `curl` lookups
of the run answered "Rate limit exceeded" -- because earlier runs of the
same day share the address; every corpus call after that carried the key
with `curl -K -`.

What to do instead: the run prompt should say fifteen, or say to read
`drafts_remaining` from the last creation answer in `/tmp/*_create_out.txt`;
and a run should carry the key on its first lookup rather than its
seventeenth.

Evidence: `/tmp/gp_create_out.txt`, 2026-09-03: `tid = T146`,
`drafts_remaining = 9`, `drafts_held = 6`; the rate-limit answers at the
start of the same run's transcript.

## The corpus title list for a critique: `/tables` shows fifty a page, and `Table` has no `id`

What happened: the T146 critique needed every published title, to see
whether a family the page names is a table the page should link.
`curl https://numberdb.org/tables` through the proxy answers the first
fifty tables and a `page=2` link; walking `/tables?page=1` to `page=6`
gave all 140 published titles in six seconds, drafts excluded as they
should be. The Django route in the throwaway,
`Table.objects.all().order_by('id')`, fails with `FieldError: Cannot
resolve keyword 'id'`: the model's key is `tid`, with `tid_int` for
sorting, and a listing that wants drafts too should order by `tid_int`.

What to do instead: for published titles, walk the paginated `/tables`
anonymously; for drafts as well, `Table.objects.order_by('tid_int')` in
the throwaway. Either is cheaper than the audit run.

Evidence: `/tmp/tables_1.html` to `/tmp/tables_6.html` and
`/tmp/crit146_titles_raw.txt`, 2026-09-03.

## T146 links to draft T142 as well; the same publishing order

T146's formula on Gauss sums and its Similar tables link
`Gauss_sums_of_primitive_Dirichlet_characters`, draft T142, as T143, T144
and T145 do. `audit_table` reports nothing, by design, while T146 is a
draft, and the two links answer 404 until T142 is public. The T146 repair
left them in, as the three earlier repairs did: the decision is which
draft to publish first, and it is the same decision for all four. A
critique of the next table that links T142 need not report it again
unless the order has been settled.

Evidence: `agents/critiques/T146.md` finding 1 and
`agents/critiques/T146-repaired.md`, 2026-09-03; `curl -o /dev/null -w
'%{http_code}' https://numberdb.org/Gauss_sums_of_primitive_Dirichlet_characters`
through the proxy answers 404.

## `source_names_it` fails a name made of common nouns when the page says it another way

What happened: the lattice batch of 2026-09-03 proposed a table of
covering densities, SPLAG's name for $V_n R^n/\sqrt{\det L}$, and the
screen failed "Covering density" on every page tried: Wikipedia *Sphere
packing* never says "covering", Wikipedia *Covering problem* is set cover,
and the arXiv abstracts of the two papers that are about exactly this
(math/0403272, math/0405441) say "covering" and "least dense" but never
"density". The word check is honest -- the pages do not contain the word
-- but a real, standard name failed in the same way an invented one would,
and the batch had to say in prose that the source is a book.

What to do instead: when the screen fails a name on the page that most
obviously defines the thing, try a page that lists it (an OEIS entry, a
catalogue) before concluding the name is wrong, and if none passes, write
the failure into the proposal with the pages tried, as
`BATCH-2026-09-03T1730.md` proposal 4 does. A screen that took a list of
synonyms ("thickness" for "density") would have passed the Springer
abstract, had it been readable -- see the next note.

Evidence: the `source_names_it` lines in the run's transcript for
`Covering density`, `Lattice covering thickness`, and the `curl` keyword
scans of the same pages, 2026-09-03.

## Springer article pages answer `urllib` with a gate and `curl` with the abstract

What happened: `curl` of
`https://link.springer.com/article/10.1007/s00454-005-1202-2` through
the proxy returned the abstract (the word "thickness" is in it);
`screen.source_names_it` on the same URL, which uses `urllib` with the
`numberdb-proposal-screen` user agent, got a 200 whose text contained
neither "covering" nor "thickness" -- a bot-check page. The screen
reported the source as not naming the family. Wikipedia, MathWorld, OEIS,
arXiv and the Nebe-Sloane catalogue answer `urllib` normally.

What to do instead: do not cite a Springer (or other publisher) page as
the source the screen checks; cite the arXiv abstract or the Wikipedia
page and give the DOI in the proposal's prose. If a publisher page is the
only source, say the screen could not read it rather than that it failed.

Evidence: the `curl` scan (`200 ... :: thickness covering`) against the
screen's `does not mention lattice, covering, thickness`, 2026-09-03.

## Neither LattE nor Normaliz is in the container's Sage

What happened: `Polyhedron.ehrhart_polynomial()` answers "Executable
'count' not found on PATH" and `engine='normaliz'` needs a polyhedron
built with the normaliz backend, which is not installed either. The same
absence stops `Polyhedron.integrate`, so a Voronoi-cell second moment (the
quantizer constant) cannot be had from the library and would need a
simplex decomposition written by hand. Vertex enumeration itself works:
the $E_8$ Voronoi cell (480 half-spaces, 19440 vertices) took 128 s with
the default ppl backend.

What to do instead: issue #94 (Ehrhart polynomials) and a quantizer table
wait on `sage -i latte_int` or `pynormaliz` in the image, which is a
person's decision; a proposal that needs either should say so.

Evidence: `/tmp/lat_probe.py` (`ehrhart ERR count is not available`) and
`/tmp/lat_probe3.py` (`['E', 8] R^2, #vecs, #vertices (1, 1200, 19440)
[128.4s]`), 2026-09-03.

## A generator committed at `TBD` counted as "built" by the task line; the table is the test, again

What happened: the stage-two task line of 2026-09-05 asked for "the
highest-ranked proposal in `BATCH-2026-09-03T1730.md` that no generator in
`generators/` answers yet". `generators/lattice-packing-densities/generate.py`
existed, with `table = 'TBD'` and no `table.yaml`, written by a build run on
2026-09-03 that died before creating its draft and swept into a person's
commit (29860f0) two days later. Read literally the task line would have
skipped proposal 1, the batch's top-ranked table and the one two issues
ask for, and built proposal 2, which depends on it. A Django listing of the
tables with `tid_int >= 130` (`/tmp/lp2_drafts.py`, 25 seconds) showed no
lattice table, published or draft, so the run took the file over and gave
it the whole order of work, as the T145 note says to. The dry run then
counted 399 entries where the proposal and the generator's own docstring
said 414 and 138 lattices; the generator lists 133, which is right, and
the proposal's count was never recounted.

What to do instead: `agents/campaign.sh` line 76 should say "that no
*table* answers yet -- list the drafts with Django before deciding", and a
build run that dies after writing a generator should commit it with a
message saying the draft was not created, so the next run does not have to
infer that from a `TBD`.

Evidence: `/tmp/lp2_drafts_out.txt` (T130 to T146, no lattice table);
`git log --stat -- generators/lattice-packing-densities` (one commit, not
about lattices); `/tmp/lp2_dry_out.txt`: `399 entries computed`.

## `sage.sh` is line-buffered now, and a killed run that shows only the first 4 KB was the reason

What happened: three runs of the lattice checks were killed at their
timeout, and each output file stopped at the same place, a few lines after
the Leech lattice's first `qfminim`, so three different stalls (one in
`qfisom`, two never explained) looked identical. The note above on the T142
probes had already asked for `grep --line-buffered` and `sage -python -u`;
both are in `agents/sage.sh` now, and the fourth run's output showed the
section timestamps up to the moment it was killed. What the timestamps then
showed: every section of the checks but the code constructions takes five
seconds, so a 560-second run that died was not slow, it was stuck. The
standalone rewrite of that section (`/tmp/lp2_codes.py`, lists and
`echelon_form` instead of `vector` and `span`, one `qfminim` per matrix)
passes in four seconds; the lesson in `agents/lessons/PROPOSALS.md` has the
details, and the cause of the two unexplained stalls is still open -- a
person watching `docker stats` during a repeat would settle whether it is
memory on the 961 MB box.

Evidence: `/tmp/lp2_check_out.txt` (8408 bytes, three times),
`/tmp/lp2_check_out2.txt` with the `[5 s]` stamps, `/tmp/lp2_codes_out.txt`,
2026-09-05.

## The site accepts a document whose `Parameters` order no longer matches the nesting of `Numbers`

What happened: T147's fourth revision (2026-09-05) arrived with every
mapping key-sorted, `Parameters` as `expression, family, n` over a
`Numbers` block nested `family, n, expression`. `POST /api/table/147`
accepted it and reported 399 entries; `audit_table T147 --links` reported
only the Definition's length. The rendered page has its column headers
shifted one column to the right, the Symbolic `values` displays are not
applied, and the rows run `A 1, A 10, …, A 19, A 2`. The `_ordered_document`
docstring in `api.py` says a write with reordered parameters "is refused"
because entry identity is positional; that refusal did not fire here,
presumably because the base revision matched and the nesting itself was
unchanged. The lesson for a contributor is in `agents/lessons/PROPOSALS.md`
(`yaml.dump` sorts keys); this note is about the two checks that were
silent.

What to do instead: until the API compares the `Parameters` order with the
first levels of `Numbers`, or `audit_table` does, a critique should print
the header row of the rendered numbers block and the first six row ids,
which is one grep on the HTML (`/tmp/crit147.py` prints the page;
`class="table-param-group-header"` is the header). The render helper still
lives only in `/tmp` and was rewritten from this file's notes for the
third time today; `agents/render_draft.py` is overdue.

Evidence: `/tmp/crit147_out.txt` (rendering, audit and document in one
run), `/tmp/crit147_hist.py` (the four revisions and their key orders),
`/tmp/crit147_params.py` (`TableData.full_yaml` parameter order
`expression, family, n`; jsonb order `n, family, expression`), 2026-09-05.

## `WebSearch` is refused in a build run too; zbMATH and arXiv through `curl` did the literature check

What happened: the densest-packings build of 2026-09-05 asked `WebSearch`
whether any lattice record had changed since the catalogue's 2012 table and
was answered "requested permissions ... but you haven't granted it yet",
as `WebFetch` is (notes above). Henry Cohn's page of records, which the
proposal named as the thing to check, answers 404 at
`cohn.mit.edu/sphere-packings` and `/sphere-packings/`. What worked, all
through the proxy: `curl https://arxiv.org/pdf/1611.01685` fetched Cohn's
Notices survey (2 MB) and `pdftotext -layout` gave its Table 1 of 36 record
densities as text; `curl https://arxiv.org/abs/<id>` gives an abstract with
its dateline; and `curl 'https://zbmath.org/?q=ti%3A...+%26+py%3A2013-2026'`
lists matching papers and preprints in `<article>` blocks. Four zbMATH
queries found the two 2025 preprints that changed the table's prose.

What to do instead: do not plan a build around `WebSearch`; for "has this
changed since" questions use zbMATH with a `py:` range and read arXiv
directly, and for a printed table in a paper try the arXiv PDF before
giving up on it (journal PDFs still answer 403, note above).

Evidence: the two `WebSearch` refusals in this run's transcript;
`/tmp/dl_cohn.html` (404, 40 KB of WordPress); `/tmp/dl_cohn_notices.txt`
lines 200–215; `/tmp/dl_zb/*.html`, 2026-09-05.

## Exit 137 from `sage.sh` after ten seconds is the box running out of memory, not the timeout

What happened: the T148 check run ended with `exit 137` in the output
file eleven seconds in, right after `Q31 done`, while PARI's `qfminim` was
returning the 261120 minimal vectors of $Q_{32}$. `NUMBERDB_TIMEOUT` was
1500 s and the Bash tool's limit ten minutes, so neither killed it; the
container was killed, presumably by the kernel's OOM killer on the 961 MB
box, and nothing in the output says so. The note above on the T142 probes
already says a 137 from the runner is its own `docker rm -f`; this one is
a third meaning. `qfrep` in place of `qfminim` (lesson in
`agents/lessons/PROPOSALS.md`) finished the same section in 34 s.

What to do instead: treat a 137 that arrives long before the timeout as
memory, and look at what the last stamped line was building; do not store
a list of more than about $10^5$ lattice vectors in a run on this box.

Evidence: `/tmp/dl_check_out2.txt`, 2026-09-05.

## Checking that an `equals` anchor lands: `views._entry_address` under `RequestFactory`, and a missing entry raises rather than returns

What happened: the T148 critique had to know whether 44 `equals` links of
the form `HREF{slug#Z,1,density}` into the draft T147 find a row, and
whether they would survive the alphabetical re-sort of T147's head
revision. Fetching the target anonymously cannot answer for a draft. In
the throwaway, `views._entry_address(request, table,
views.table_context(table))` with a `RequestFactory` request carrying
`{'entry': 'Z,1,density'}` returns `entry_found: True` and the canonical
URL in a second per anchor (`/tmp/crit148_t147.py`). Two things to know:
the positional identity is the row's `params_id`, which follows the
nesting of the `Numbers` block and not the order of the `Parameters`
section, so T147's sorted head still resolves `family,n,expression`
anchors; and for an entry that does not exist the view calls
`messages.warning`, which under `RequestFactory` raises `MessageFailure`
("cannot add messages without MessageMiddleware"). The exception is the
"not found" answer, not a fault in the script; catch it, or attach a
`FallbackStorage` to the request first.

What to do instead: check anchors this way rather than by fetching pages,
and wrap the call in `try/except MessageFailure` so one dead anchor does
not end the run.

Evidence: `/tmp/crit148_t147_out.txt`, 2026-09-05: seven anchors found,
then the traceback on `K,11,density`.

## Reading a draft as its owner needs only curl: the key goes in through `-H @-`

What happened: a repair has to re-read the live document of a draft, which
answers Not Found anonymously, and every earlier run reached it through
Python with the SOCKS bootstrap or through the throwaway. `GET
/api/table?id=T148` with the owner's key answers 200 to curl through the
proxy, and curl reads a header from stdin when told `-H @-`, so

    { printf 'Authorization: Bearer '; cat "$NUMBERDB_KEY_FILE"; } | curl -s -H @- 'https://numberdb.org/api/table?id=T148'

fetches the document in a second with the key in no argument, no process
list and no file outside its own. The answer is JSON in the stored key
order, and `json.load` keeps that order, so the same object can be edited
and handed to `agents/api_edit.edit_over_api`, which accepted it and
recorded `via api`, `merged false`, `reviewed false`.

What to do instead: use this for the re-read the repair prompt asks for;
keep the throwaway for the audit and the rendering, which need Django.

Evidence: `/tmp/t148_live.yaml`, `/tmp/t148_after.json` and
`/tmp/repair148.py`, 2026-09-05; revision `78a8b78b…` of T148.

## `sage.sh` forwards no environment variable but `PYTHONPATH` and `NUMBERDB_ASSISTED_BY`

What happened: the T149 build wrote its stored-check, audit and offer
scripts to read the table id from `HC_TID`, set on the near side as
`HC_TID=T149 agents/sage.sh script.py`. Inside the container the variable
was unset and each script stopped at its own guard, "set HC_TID". The
`docker compose run` line in `agents/sage.sh` passes exactly two `-e`
flags, and nothing else crosses the ssh and the container boundary.

What to do instead: write the tid into the script, as the `dl_*.py` scripts
of the T148 build did, or read it from a small mounted file; a `TID = 'TBD'`
guard that refuses to run is the right shape, since the alternative is a
script that quietly works on the wrong table. `sage.sh` could take
`NUMBERDB_TID` through as a third `-e` if this keeps happening.

Evidence: `/tmp/hc_stored_out.txt`, first run, 2026-09-05: `set HC_TID`,
exit 1; the same script with `TID = 'T149'` written in: 67 PASS.

## A generator committed at `TBD` counted as "built" for the third time; the previous run's `/tmp` scratch was the fastest way to finish its table

What happened: the stage-two task line of 2026-09-05 (afternoon) again asked
for "the highest-ranked proposal ... that no generator in `generators/`
answers yet". `generators/lattice-covering-densities/` existed with
`table = 'TBD'`, committed by the run before with a message saying the draft
was not created; read literally the line would have skipped proposal 4 and
built proposal 5. `/tmp/cv_programs.py` (Django, tables with `tid_int >= 140`)
showed T147 to T149 and no covering table, so proposal 4 was the next one.
That run's scratch was all still in `/tmp` under the `cv_` prefix -- the
sources it had fetched (`cv_sources.json`, `cv_src/`, `cv_zb/`), its dry run,
and a check script rewritten at 14:42 that had never been run, because the
earlier version of it had been killed at 14:44 after 367 s in one Voronoi
cell. Rerunning the dry run, the rewritten check (192 s), a new check against
the 2008 table, and the create, fill, stored-check, audit and offer scripts
with the tid written in took about an hour; nothing had to be fetched twice.

What to do instead: the campaign line should say "no *table* answers yet"
(the two notes above ask the same); a run that rewrites a check and dies
before running it should say "not yet run" in the commit, as this one's
predecessor did; and a run that inherits a table should read `/tmp/<prefix>*`
before writing anything, since `/tmp` outlives a run (note above) and the
sources are the expensive part.

Evidence: `/tmp/cv2_programs_out.txt` (T147–T149, no T150),
`/tmp/cv_check_out.txt` ending in `Terminated`, `git log -1 1adc250`,
2026-09-05.

## After a whole-document write, `cv_audit.py`'s "entries in the head revision" counts families, not rows

What happened: T150's one-word repair through `agents/api_edit.edit_over_api`
(the document as `api/table` returns it, `Numbers` nested by parameter
value) stored the nested shape, as the T145 note says it does, and the audit
script's `len(tree['Numbers'])` printed 8 (the families) where the fill's
revision had printed 234. The anchors loop in the same script already
accepted both shapes and found 27 of 27, the rendered page was 5 bytes
longer (the length of the changed phrase), and `/tmp/cv2_stored.py` through
the client read 234 entries and passed 732 checks; nothing was lost.

What to do instead: count entries with the client (`numberdb.table(tid)`
nests them; walk three levels) or flatten the stored tree before counting;
and after any whole-document write, run the stored check rather than trust
a count printed from the tree's first level.

Evidence: `/tmp/cv2_audit_out.txt` (`entries in the head revision: 234`),
`/tmp/cv2_audit_out2.txt` (`8`), `/tmp/cv2_stored_out2.txt` (`stored
entries: 234`, `PASS 732, FAIL 0`), 2026-09-05.

## `export.arxiv.org` answers `curl` with an empty body here; `arxiv.org/abs/<id>` answers with the page

What happened: the T151 build fetched ten arXiv abstracts to check the
number each cited paper claims. The Atom API
(`export.arxiv.org/api/query?id_list=...`) returned zero bytes for every
request, with no error, through the proxy and without it. The abstract
pages (`https://arxiv.org/abs/2411.04916`) answered at once, and the
abstract sits in `<blockquote class="abstract ...">`, which a regex reads.

What to do instead: fetch the `/abs/` page and read the blockquote; do not
spend a turn on the API. Ten pages took a few seconds in one loop.

Evidence: 2026-09-06, `/tmp/kn_arxiv1.xml` (0 bytes) against
`/tmp/kn_abs_2411.04916.html`.

## `audit_table` saying "N values are written but only M are in the search index" can mean the values are not numbers

What happened: after the first fill of T151 the audit said 24 values were
written and 6 were in the index, and suggested rebuilding the index. The
cause was in the values: eighteen had been stored as YAML mappings (a
`str` subclass serialised as a Python object by the client, see the
lessons file), which the indexer rightly skipped. `verify()` had reported
24/24 matched. The table read back through `numberdb.table(tid)` showed
the shape, and the rendered page showed each as two sub-entries,
`args` and `state`.

What to do instead: when the audit reports an index gap on a table just
filled, read the stored values back through the API before rebuilding
anything; if a value is a mapping, the fill is wrong, not the index. The
integer intervals themselves index fine: after the repair the audit said
"Nothing to report", and T6's audit, run beside it for comparison, says
nothing about its intervals either.

Evidence: 2026-09-06, `/tmp/kn_audit_out.txt` before and
`/tmp/kn_audit_out3.txt` after; `/tmp/kn_stored_out2.txt`.

## Django is not installed on the runner's machine, so a new test in `numberdb_app` cannot be run here

What happened: two tests were added to `test_agents.py` beside the
`check.py` ones, and `python3 manage.py test` failed with "Couldn't import
Django"; there is no virtualenv in the repository (`env/` holds no
`bin/python`). The toolkit under test needs no Django, so the assertions
were run directly against `check.py` with `importlib`, which is what the
test class itself does.

What to do instead: for a change to `agents/table-build/check.py`,
exercise it directly as the test does and say so in the commit; leave the
Django test run to CI or to a person. A test that needs the database
cannot be run from a build run at all.

Evidence: 2026-09-06, the commit "T151 repaired after the stored check".

## arXiv's HTML search page answers `curl` when `export.arxiv.org` does not

What happened: the stage-one run of 2026-09-06 needed the arXiv number of
a paper it knew only by title (Codello, "Exact Curie temperature for the
Ising model on Archimedean and Laves lattices"). `export.arxiv.org/api`
returns empty bodies from here (noted above, 2026-09-06 build run).
`https://arxiv.org/search/?query=Codello+Curie+temperature+Archimedean&searchtype=all&abstracts=hide&size=25`
answers plain `curl` with an HTML list; the abstract links are
`arxiv.org/abs/NNNN.NNNNN` in it and the titles follow each "arXiv:" line
in the stripped text. That found 1008.4720 in one call, and the `abs` page
then passed `source_names_it`.

What to do instead: search `arxiv.org/search/` by title words, strip the
HTML, and read the `abs` page; do not wait on the API.

Evidence: 2026-09-06, `/tmp/search_codello.html` and `/tmp/abs_1008.4720.html`.

## The task line "write the batch and commit it" cannot be followed for `agents/table-ideas/BATCH-*.md`

What happened: `.gitignore` line 172 (commit 74d29f7, 2026-09-04) ignores
every batch file, `git ls-files agents/table-ideas` lists only `PROMPT.md`
and `screen.py`, and no earlier batch is in the history either. The
stage-one prompt of 2026-09-06 still said "write it to
agents/table-ideas/BATCH-2026-09-06T0326.md and commit it". The batch was
written and left uncommitted, like the batch of 2026-09-03T1730 before it;
only this note is committed.

What to do instead: write the batch, do not `git add -f` it (the ignore is
the owner's decision that agent output is data), append the lessons to
`agents/lessons/PROPOSALS.md` (also ignored), and commit the environment
note alone. The stage-one task line should drop "and commit it" or name
this file as the thing to commit.

Evidence: 2026-09-06, `git check-ignore -v agents/table-ideas/BATCH-2026-09-06T0326.md`
-> `.gitignore:172`.

## `pdftotext -layout` puts a paper's table beside its figure's axis labels, and the last row of a wikitext table ends at `|}`

What happened: the outside check of the percolation table parsed Mertens
and Moore's Table II out of the arXiv PDF. Half the rows were missed:
`pdftotext -layout` lays the table's columns beside the figure on the same
page, so the row for $d=4$ begins with the caption of Figure 1 and the rows
for $d=10$ to $13$ begin with the axis label `10−5`, and a regex anchored at
the start of the line saw nothing. Likewise the last row of the Laves table
in the Wikipedia wikitext is followed by `|}` rather than `|-`, so a parser
splitting rows on `|-` handed the check `}` as the bond cell, and cite
templates inside a cell begin lines with `  | last = ...`, which a split on
`\n|` takes for new cells. Each was a parser fault that first read as a
missing value in the source.

What to do instead: search for a table row anywhere in the line rather than
anchoring it; strip the closing `|}` before splitting rows; split cells only
at `|` not followed by `key =`; and when a parsed source shows a value
"missing", print the raw lines before concluding the source lacks it.

Evidence: 2026-09-06, `/tmp/pc_check_out.txt` (ten "is None as printed in
MertensMoore" and `D-3-12-12 bond: Wikipedia derives None`) against
`/tmp/pc_check_out3.txt` after the fixes in `/tmp/pc_sources.py`.

## An Uppsala thesis is one `curl` away through DiVA's urn resolver; IOP comment-and-reply papers are not, and zbMATH confirms them

What happened: Wikipedia cites Parviainen's 2005 dissertation for three Laves
site thresholds, one of them without an error bar. `curl -L
http://urn.kb.se/resolve?urn=urn:nbn:se:uu:diva-4251` answers a DiVA record
page whose `FULLTEXT01` link gives the PDF (386 KB), and `pdftotext` of it
has the table and the sentence stating the standard error. The 2024 comment
and reply in J. Phys. A that Wikipedia quotes for the square-lattice site
threshold have no arXiv version and IOP's pages do not answer here; zbMATH
(`zbmath.org/?q=ti%3A...`) confirmed both exist with the titles and pages
Wikipedia gives, and the table cites them for the numbers "as quoted in"
the Wikipedia table.

What to do instead: for a dissertation cited by a Wikipedia table, try the
urn resolver and DiVA first; for a journal item without an arXiv copy,
confirm it on zbMATH and say in the table that the value was taken from the
secondary source.

Evidence: 2026-09-06, `/tmp/pc_src/parviainen_thesis.txt` lines 2660-2700,
`/tmp/pc_src/zb_comment.html`.

## The draft ceiling is fifteen and the run prompt still says five; T152 was the second draft held

What happened: the creation answer for the percolation table reported
`drafts_held = 2` and `drafts_remaining = 13` (T151 being the other). The
build prompt still says zeta3 "may hold up to five drafts"; the number does
not bind anything, but a run reading it might decline to build.

Evidence: 2026-09-06, `/tmp/pc_create_out.txt`.

## A draft's title is listed on the public tag pages before it is published

What happened: the T152 critique found `/tags/physics` and
`/tags/probability+theory`, fetched anonymously, listing "Site and bond
percolation thresholds of lattices" with a link to `/T152`, which answers
Not Found to everybody but its owner; `/tags/discrete+geometry` lists the
draft T151 the same way, while `/tables` lists neither. Re-checked on
2026-09-06 during the T152 repair: `curl -s https://numberdb.org/tags/physics`
contains `href="/T152"` and the title, and `/tables` contains no
"percolation". So a draft's existence and title are public through its
tags, and every link the tag page offers for it is a dead one.

What to do instead: nothing in a run; the tag view should filter as
`/tables` does. Until then a critique or repair should not count a tag-page
listing as the draft being reachable.

Evidence: 2026-09-06, `agents/critiques/T152.md` (the "site matter"
section) and the `curl` above.

## `audit_table` has no rule for a count in the prose that disagrees with the rows

What happened: T152's comment and rigour details said "Eleven of the
thresholds are known exactly" and "the other 55 entries" where the rows
held nine exact entries and 57 estimates; the number came from the
proposal, not from the rows, and the generator's docstring and commit
message repeated it. `audit_table T152 --links` reported only the length
of the Definition. The critique caught it by counting the rows without
`+/-`.

What to do instead: a rule that finds a number word or numeral in the prose
followed by "entries", "thresholds", "rows" or "values" and compares it
with the entry count, or with the count of entries of each shape, would
have found this. Until there is one, a critique should count.

Evidence: 2026-09-06, `/tmp/rep152_audit_before.txt` and the T152 rows.

## Stored `Number` rows are fewer than entries when exact values repeat

What happened: after the T152 repair, `Number.objects.filter(table=t)` in
the throwaway counted 62 rows for a document of 66 entries, and the same
run showed the revision's `Numbers` stored as the nested mapping the read
endpoint serves rather than the flat list the package wrote (T151's did the
same after its repair). Both read as a write that had lost entries. The
read-back document had all 66, and the missing four were the second to
fifth `1/2` entries: `data_pipeline/build.py` skips a row whose exact value
already has one in the same table ("don't save duplicate exact numbers"),
and balls and intervals are never deduplicated, so the count was right
before the edit too.

What to do instead: check a write by comparing the `GET /api/table`
document with what was sent; if rows are counted, subtract repeated exact
values first. A critique that finds an `equals` link on several entries
should expect them to share one row in search.

Evidence: 2026-09-06, `/tmp/rep152_count.py` (62 rows, `square,2,bond` the
one `q 1/2`), `data_pipeline/build.py` at "exact_numbers".

## `check.exactness` did not accept a plain decimal string, the first spelling of a real in the skill

What happened: the dry run of the entropy-constants generator reported
"coefficient of unexpected type str" for the two transcribed Baxter values,
`1.5030480824753322643220663294755536893857810` and the honeycomb constant:
`check.py` accepted the integer interval `[a, b]` and the ball
`c +/- r` and nothing else in text. Extended in this run with
`_is_decimal_text` (plain `str`, digits on both sides of a point, optional
sign and exponent; a string without a point is an integer and is refused, as
are a `str` subclass and `1.` or `.5`), with two tests beside the ball-text
ones in `numberdb_app/test_agents.py`, exercised directly since Django is not
installed here.

What to do instead: nothing now; the check accepts the three strings a table
returns on purpose.

Evidence: `/tmp/ec_dry_out.txt` (two complaints), `/tmp/ec_dry_out2.txt`
(clean), 2026-09-06.

## `audit_table`'s Definition-length note fires on a 328-character, one-sentence definition

What happened: T153's Definition, one sentence defining $\kappa$ and $h$
with the limit written out, drew "Definition is 328 characters (median here
is 195); check whether part of it belongs in Comments or Formulas" after the
list of the four models had already been moved out of it (459 characters
before). The T152 critique disputed the same note on that table. A
definition that names a limit and two symbols is over the median by
construction, so the note is advice, not a finding, and the run left it.

What to do instead: the note could stay silent when the Definition is a
single sentence, or state the threshold it fires at; a run reading it as a
finding would cut the mathematics to reach a number.

Evidence: `/tmp/ec_audit_out2.txt`, 2026-09-06.

## A draft's whole document can be rewritten as zeta3 with one `POST /api/table/<n>` pinned to the head revision

What happened: the two audit findings on T153 were applied by sending the
repository's `table.yaml` with the stored `Numbers` attached, through
`client.submit('/api/table/153', yaml.dump(document), headers={'X-Base-Revision': head, ...})`
with the zeta3 key on stdin (`/tmp/ec_write_doc.py`, after
`/tmp/lp2_write_doc.py`), rather than through `agents/api_edit`, which
signs as bmatschke. The script refuses unless exactly the sections it
expects differ, and the answer carries `merged`, `reviewed`, `revision`,
`unchanged`; the numbers came back intact (34, re-checked by
`/tmp/ec_stored.py`). The head digest to pin comes from
`Table.head_revision.digest` in the audit script, since `GET /api/table`
carries none.

What to do instead: keep this shape for a draft's prose repair; the
`api_edit` route is for a person's session edit.

Evidence: `/tmp/ec_write_doc.py` answer `revision = a2506f1a...`, 2026-09-06.

## The two `/tmp` whole-document write scripts sorted every mapping; T147 is published that way

What happened: `/tmp/lp2_write_doc.py` (T147, 2026-09-05) and
`/tmp/ec_write_doc.py` (T153, 2026-09-06) both called `yaml.dump(document, ...)`
without `sort_keys=False`, so the revision each wrote has its top-level keys,
parameters, formulas, comments, links, references and numbers alphabetised.
On T153, a draft, the critique caught it and the repair rewrote the document
in the repository's order (`/tmp/rep153_write.py`). T147 is published with
its five formulas in alphabetical order (duals, hermite-constant, laminated,
relations, root-lattices) against the yaml's relations, root-lattices, duals,
laminated, hermite-constant; its parameters `family, n` survived only because
that is alphabetical. The `agents/api_edit` module has always dumped with
`sort_keys=False`. Neither `audit_table` nor the API notices a parameter
order that disagrees with the nesting of the numbers.

What to do instead: any whole-document write script dumps with
`sort_keys=False` and reads the order back; T147's formula order is a repair
somebody may still want to make (one API edit, pinned to its head, changing
no text). The lesson for a contributor's own laptop is in
`agents/lessons/PROPOSALS.md`.

Evidence: `/tmp/rep153_audit_before.txt` (T153 head `a2506f1a…`, every
mapping sorted), `GET /api/table?id=T147` on 2026-09-06 (top-level keys
`Comments, Data properties, Definition, …`).

## The T154 build: what was reachable, and the drafts count

What happened: the primary sources for the cubic Ising couplings are
partly out of reach. APS abstract pages (`journals.aps.org/pre/abstract/...`)
answer 403 with a JavaScript challenge, so Deng and Blöte 2003 could not be
read; the arXiv export API (`export.arxiv.org/api/query?id_list=...` and
`search_query=au:...+AND+ti:...`) answers title, journal reference and
abstract for anything with an arXiv version, and the PDF downloads for
`pdftotext`; and Crossref's REST API
(`api.crossref.org/works?query.bibliographic=...&select=DOI,title,...`)
resolves 1950s physics papers to title, volume, pages and DOI, which is
how Thompson–Wardrop 1974, Utiyama 1951, Kano–Naya 1953, Houtappel 1950
and the Philosophical Magazine and JPSJ papers were confirmed. The
creation answer for T154 reported `drafts_held = 4` and
`drafts_remaining = 11` (T151, T152, T153, T154).

What to do instead: for a paper without an arXiv version, confirm it on
Crossref and say in the table that the value was taken from the secondary
source, as the fcc and diamond rows of T154 do.

Evidence: `/tmp/ic_db2003.html` (403), the Crossref answers in the run
transcript, `/tmp/ic_create_out.txt`, 2026-09-06.

## The rendered-page word count in the audit scripts sees the site's own text

What happened: the audit scripts for T152, T153 and T154 strip the tags
from the table page as the owner sees it and count "below" and "above";
every table reports `below occurs 2 times` (T152: 3) with no "below" in
its document or entries, so the count comes from the page's own text and
not from the table.

What to do instead: count the words in the document and the entries
(`check.prose` does the entries now), and read the page for the rendering
of the entries, not for those words.

Evidence: `/tmp/ic_audit_out3.txt`, `/tmp/rep153_audit_after.txt`,
`/tmp/pc_audit_out.txt`, 2026-09-06.

## arXiv PDFs can be read here with curl and pdftotext

What happened: the T154 build recorded that APS abstract pages answer
403 and that only the arXiv export API and Crossref could be reached, so
the papers behind the cubic estimates were confirmed by title and not
read. The repair needed the actual numbers: `curl -sL
https://arxiv.org/pdf/1710.03574` through the proxy fetches the PDF, and
`/usr/bin/pdftotext -layout` on this machine turns it into text that
`grep` can search, tables included. Both papers behind the bcc finding
were read in full that way in under a minute.

What to do instead: for a paper with an arXiv number, fetch the PDF and
run `pdftotext -layout` before deciding that it cannot be read; the
tables come out aligned enough to find a value and its citations. A paper
without an arXiv version stays unreadable from here, as before.

Evidence: `/tmp/lc1710.txt` line 442, `βc = 0.1573725(5) [7, 27, 30]`;
`/tmp/bc0112.txt` line 1477, Table II, `0.1573725(10)`; 2026-09-06.

## The table view prints two debug lines to stdout on every render

What happened: rendering T155 in the throwaway for its critique, the
output carried `label: program-sage` and `properties: {'type': 'Q', …}`
before the HTML. They are `print("label:",label)` at
`numberdb_app/views.py:697` and `print("properties:",properties)` at
line 1039, in the view that builds every table page, and they have been
there since 64c41cf of 2021-03-10. In production they go to the web
container's log on every page view; in a critique run they land in the
captured output ahead of `STATUS 200`, where a script that takes "the
first line is the HTML" would be wrong.

What to do instead: in a critique script, print a marker before the HTML
and cut at it, as `/tmp/crit155.py` does. On the site, delete the two
prints; nothing reads them.

Evidence: `/tmp/crit155.out` lines 217–218, 2026-09-06.

## A whole-document write through the API stores Numbers nested, and a Django check must flatten it

What happened: T157 was filled by `generate.py` (revision `5d6d15cb…`,
`Numbers` a flat list of 16 `{params, number, comment}` records in
`tree_of(head_revision)`), then its definition was trimmed with
`agents.api_edit` by sending the document back as the API had served it.
The API serves `Numbers` nested by parameter value, and the new head
(`9bc0bf7e…`) stores it that way: a dict of 12 lattices with the five
hypercubic rows under one key. `len(tree['Numbers'])` then says 12, and a
check script that loops `for entry in numbers: entry.get(...)` crashes on
a string key. T152 has the same shape since its repair (24 first-level
items, 66 leaves). The page renders all 16 values, `audit_table` reports
nothing, and `verify(sample=None)` through the client matches 16 of 16, so
the shape is only a fact about the stored tree, not a fault.

What to do instead: in a Django-side check, flatten `Numbers` whether it is
a list or a nested dict (`/tmp/cc_after.py` has a `leaves()` that walks
both) and count leaves, not first-level items; `check.stored()` in
`agents/table-build/check.py` still assumes the flat list and returns
nothing for a table stored nested.

Evidence: `/tmp/cc_after.py` run of 2026-09-06 listing both shapes across
the four revisions of T152 and T157.

## `audit_table --links` from the throwaway can time out on oeis.org, and the next run may not

What happened: the critique of T158 ran `audit_table T158 --links` in the
throwaway on 2026-09-06 and got `Links[OEIS-neg] answered TimeoutError:
https://oeis.org/A023679` while the same link answered 200 through the
proxy from the workstation; the repair ran the same command in the same
container two hours later and got "Nothing to report" with all four OEIS
links checked. The KnotInfo `URLError` recorded above is the same kind of
thing.

What to do instead: treat a `TimeoutError` or `URLError` from `--links` as
the container's network and not as the link, confirm the URL from outside
the container, and run `--links` once more before writing the finding down.

Evidence: `agents/critiques/T158.md` and `/tmp/rep158_audit_before.txt`,
`/tmp/rep158_audit_after.txt`, 2026-09-06.

## `sys.path.insert(0, '/app')` before the client is imported hides `numberdb.sage`

What happened: the dry run of T159 listed the drafts with Django at the top
of the script, inserting `/app` at the front of `sys.path` as
`/tmp/cf_audit.py` does, and then imported the generator: `import
numberdb.sage` failed with `No module named 'numberdb.sage'`, because
`/app/numberdb` is the Django project package and it now shadowed
`/app/clients/python/numberdb`, the client. `cf_audit.py` never noticed
because it uses no client.

What to do instead: keep the Django part of a throwaway script last, after
every client call, and before `django.setup()` delete every `numberdb*`
entry from `sys.modules` as well as inserting `/app`; `/tmp/cr_dry.py` does
that and both halves ran in one container. Or use two scripts, which costs
a second run of `agents/sage.sh`.

Evidence: the first `/tmp/cr_dry_out.txt` of 2026-09-06 (traceback at
`generate.py` line 64) and the second, which lists T158 and computes 515
entries.

## A draft can be published while the run is still checking it

What happened: T159 was created as a draft at 12:42 UTC, filled at 12:43,
and by the time the audit ran in the throwaway a few minutes later the
table had `published=True`, `ready_for_review=False` and `reviewed_by =
bmatschke`, with the anonymous page answering 200; a person had accepted it
from the table page without it ever being offered. The offer script would
have posted to a published table.

What to do instead: read `published` and `reviewed_by` before offering, and
skip the offer when a person has already acted; `/tmp/cr_revs.py` prints
both.

Evidence: `/tmp/cr_create_out.txt` (`published = False`) against
`/tmp/cr_audit_out.txt` and `/tmp/cr_revs.py`, 2026-09-06.

## The LMFDB's API gates after a handful of calls; its list pages did not

What happened: the T160 build needed the two smallest fields of each of 28
signatures from the LMFDB. `api/nf_fields/?degree=..&r2=..&_sort=disc_abs`
answered the first eight calls, then every call for the next twenty minutes
was the reCAPTCHA page; after a pause it answered three to five more, then
gated again, and so on through the run. The search page
`NumberField/?degree=n&signature=[r1,r2]` answered for seven signatures in a
row on the first try and the eighth on the third, with the labels, the
polynomials (in `$...$`, LaTeX) and the discriminant in the stripped HTML,
which is all the API had been asked for. Battistoni's Theorem 1 and OEIS's
example lines were the other copies, so nothing waited on the gate.

What to do instead: ask the API in batches of three or four with a minute
between, save every answer to `/tmp` as it arrives, and fall back to the
HTML list page for whatever is still missing; the labels parse with one
regular expression and the polynomial sits in the first `$...$` after the
label.

Evidence: the `GATED` lines in this run's transcript against
`/tmp/md_lmfdb/n*_r*.json` and `/tmp/md_lmfdb/html_*.html`, 2026-09-06.

## Odlyzko's discriminant tables are at `unpublished/discr.bound.table1` to `table4`

What happened: the batch named Odlyzko's page as a source, and the URL that
comes to mind, `unpublished/discr.bound.table`, answers 404. The index page
`www-users.cse.umn.edu/~odlyzko/unpublished/index.html` links
`discr.bound.table1` (GRH), `discr.bound.table2` (unconditional),
`discr.bound.table3` and `discr.bound.table4` (the same as
$D>A^{r_1}B^{2r_2}e^{-E}$ per $b$), and `discr.bound.tables.txt` describing
them; all five answer `curl` through the proxy. The best unconditional bound
for a signature is the maximum over the 162 rows of Table 4, which is what
T160's comment on the open rows quotes.

Evidence: `/tmp/md_odlyzko_table4`, `/tmp/md_odlyzko_tables.txt`, and the
Python that reads them in `/tmp/md_check.py`, 2026-09-06.

## `enumerate_totallyreal_fields_all(8, 282300416)` took 41 s in a probe and 233 s in the dry run

What happened: the same call, in the same container, on the same day. The
dry run's wrapper computes every entry twice (the T138 note explains why),
so the octic enumeration ran twice in that run and the second took four
minutes; the probe had the box to itself. A fill plus a full verify of T160
is therefore about nine minutes on this box, all of it that one call, and
`NUMBERDB_TIMEOUT` for it was set to 1500 s.

What to do instead: budget a `sage.sh` run for a table whose generator
enumerates something by the loaded time, not the probe's; and if the
generator's own check is ever too slow for a person's `verify()`, the octic
enumeration is the one line to move behind a flag.

Evidence: `/tmp/md_probe2_out.txt` (`41.5 s`), `/tmp/md_dry_out.txt`
(`[233.2 s]` on the (8,0) entry), `/tmp/md_fill_out.txt`, 2026-09-06.

## An extra `agents/sage.sh` mount named `generate.py` can arrive as a directory

What happened: the T165 repair tried to verify the updated attached
generator by running
`agents/sage.sh /tmp/t165_verify_generator.py generators/artin-primitive-root-densities/generate.py`.
Inside the container, importing `generate` failed, and loading
`/work/generate.py` directly raised `IsADirectoryError`: the path existed as
a directory. A uniquely named scratch copy,
`/tmp/t165_generate_verify_source.py`, mounted and verified the table:
`<VerifyReport T165: 92/92 matched, 0 differing, 0 missing, 0 extra>`.

What to do instead: when a secondary mount must be imported, give the
scratch file a unique basename rather than `generate.py`, or check
`/work` before assuming the mount is a file. The likely wrapper-side cause
is a stale remote directory with the same basename; `agents/sage.sh` removes
remote scratch paths with `rm -f`, which does not remove directories.
The same symptom can occur when the main script itself is named `generate.py`
and a key is being piped on stdin; a uniquely named scratch main that writes a
transient attachment copy named `generate.py` inside the container let T166 be
filled while still attaching the expected filename.

Evidence: `/tmp/t165_verify_generator.py` and the failed and successful
verification outputs, 2026-09-09; the T166 fill first failed with
`can't find '__main__' module in '/work/generate.py'`, then succeeded through
`/tmp/fill_bh_with_attachment.py`.

## A burst of outbound fetches through the proxy fails as a batch, then works one at a time

What happened: a stage-one run fired twelve `screen.source_names_it` calls
in one Python process while three other background jobs (an OEIS loop, a
Wikipedia scrape and a Sage run's ssh) were fetching at the same time. Ten
of the twelve came back `source could not be read (URLError)` for
Wikipedia, MathWorld, OEIS and arXiv pages that had answered a minute
earlier; the last two in the list, reached after the other jobs finished,
passed. Re-run alone a few minutes later, every one of the ten passed or
failed for a real reason.

What the skill says now: nothing; this is the proxy, not the corpus.

What to do instead: run the source screens in one process, one at a time,
with nothing else fetching; and read a `could not be read` from a busy run
as "not yet screened", never as a failed source. `screen.py` already
distinguishes an unreadable source from a source that names nothing, so the
verdict is legible; it is the scheduling that hides it.

Evidence: `/tmp/claude-1000/.../tasks/bqh8aunkl.output`, 2026-09-09: ten
`URLError` lines followed by two verdicts; the same twelve URLs rerun at
00:40 UTC in one process, all answered.

## `agents/sage.sh` mounts extra files; it does not forward ordinary argv

What happened: T168's dry run was first invoked as
`agents/sage.sh agents/table-build/dry_run.py generators/.../generate.py`.
Inside the container `dry_run.py` saw no generator path, because the wrapper
uses additional command words as files to mount under `/work`, not as
arguments to pass to the script. A small wrapper that set
`sys.argv = ["/work/dry_run.py", "/work/generate.py"]` and then ran
`/work/dry_run.py` worked.

The same run also showed that launching several `agents/sage.sh` checks at
once can give exit code 1 with no useful output, while the same scripts run
one at a time either pass or show the real failure. The meaningful checks were
therefore rerun serially before the draft was offered.

What to do instead: write a scratch wrapper when a script needs arguments, and
refer to mounted files by their `/work/<basename>` names. Run the final audit,
stored-value checks and `verify()` serially; a silent failure from a parallel
batch is not a result.

Evidence: `/tmp/run_dry_repo_logistic.py`, `/tmp/stored_logistic_checks.py`
and T168, 2026-09-09.

## `agents/sage.sh` did not forward arbitrary environment variables (fixed)

What happened: filling T169 first ran

    cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 \
      NUMBERDB_PUBLISH=1 NUMBERDB_ASSISTED_BY=codex-cli \
      agents/sage.sh generators/logistic-periodic-windows/generate.py

The generator's `__main__` branch looks for `NUMBERDB_PUBLISH` and
`NUMBERDB_KEY_FROM_STDIN`, but inside the container neither variable was set,
so it took the default verification path and reported
`Table with id 'T169' does not exist` for the still-private draft. The wrapper
only passes `PYTHONPATH` and `NUMBERDB_ASSISTED_BY` explicitly.

Fixed on 2026-09-09: `sage.sh` forwards `NUMBERDB_KEY_FROM_STDIN` and
`NUMBERDB_PUBLISH` as well, which are the two a generator's `__main__` reads.
It still forwards nothing else, so the rest of this entry stands.

What to do instead, for any other flag: when a Sage script needs one, run a
scratch wrapper as the main script, mount the
real generator beside it, and have the wrapper read stdin and call the wanted
function directly. For a fill, import `/work/generate.py`, put the piped key
in `NUMBERDB_API_KEY`, and call `generator.publish(...)`.

Evidence: T169, 2026-09-09; the failed run entered
`LogisticPeriodicWindows().verify(sample=None)`, and
`/tmp/publish_windows_generator.py` filled the same draft successfully.

## Interrupting `agents/sage.sh` can leave its container name occupied

What happened: a slow direct `mpmath.nsum` probe was stopped with Ctrl-C.
The remote container continued long enough that the next `agents/sage.sh`
call failed before running the script, with Docker reporting that
`/numberdb-agent-run-2` was already in use. In this Codex environment the
local shell PID seen by the wrapper can be reused, so the fixed container
name based on `$$` is not unique across calls.

A later run had the unique name in place, but found the cleanup still using
the old literal `numberdb-agent-run-$$` while the started container was named
`numberdb-agent-run-$run_id`. Interrupting a write attempt could therefore
leave exactly the container the cleanup was meant to remove.

What the skill says now: nothing; this is the runner and this deployment's
remote Docker cleanup, not a table-building convention.

What to do instead: make the runner's container name unique per call, not
only per local shell PID, so an interrupted or slow-to-clean container does
not block the next unrelated Sage run, and have cleanup remove that exact
name. Avoid interrupting Sage probes when a shorter controlled test can be
written instead.

Evidence: the failed `/tmp/cf_zeta_test.py` run on 2026-09-09 immediately
after stopping `/tmp/cf_compute_test.py`; `agents/sage.sh` now includes a
timestamp and random suffix in both the remote scratch path and Docker name.
On 2026-09-10 the cleanup command was changed from
`docker rm -f 'numberdb-agent-run-$$'` to `docker rm -f "$name"`.

## `audit_table` has no rule for an `HREF` or `CITE` inside `$...$`

What happened: the T170 critique found formula (5) written as
`$e^\beta=HREF{E}[$e$]^{\beta}$`. The view renders `HREF` as an `<a>` and
MathJax (v3, `static/vendor/mathjax/tex-svg.js`, default
`includeHtmlTags`) will not typeset across an element, so the formula
falls apart on the page while `audit_table T170` and `audit_table T170
--links` both say "Nothing to report": the slug resolves, which is all the
rule checks. Same shape as the asterisk and backtick faults of T169: the
document is valid and the rendering is not, and no rule looks at the
rendering.

What to do instead: add a rule that flags `HREF{` or `CITE{` preceded in
the same field by an odd number of unescaped `$` (or inside `\(...\)`),
in `numberdb_app/management/commands/audit_table.py`; a `<a>` from
`_reference_href` inside math can never render. The lesson for the table
author is in `agents/lessons/PROPOSALS.md`.

Evidence: T170 head 4ee3f1b0, 2026-09-09; `/tmp/crit170_out.txt` has the
audit output and the HTML; `agents/critiques/T170.md` finding 1.

## A generator directory name is not enough to skip a proposal

What happened: this run was asked for the highest-ranked proposal in
`agents/table-ideas/BATCH-2026-09-09T1518.md` that no generator answered yet.
It first treated `generators/power-sum-polynomials/` as answering proposal 1,
because the directory name matched the batch heading. Reading the generator
and table document showed that it fills T119, the power sum symmetric
polynomials $p_k(x_1,\ldots,x_n)$, while proposal 1 was for
$S_p(n)=\sum_{k=1}^{n}k^p$ as a polynomial in $n$. The run corrected course
before writing the wrong table, but only because the docstring and
`table.yaml` were read.

What to do instead: when the stage-two task says "no generator answers yet",
read the candidate generator's docstring, table id and `table.yaml` title
before counting it as coverage. A path is an aid to finding the file, not a
claim about the family it answers.

Evidence: `generators/power-sum-polynomials/generate.py` begins "Power sum
symmetric polynomials" and points to T119 at
`Power_sum_symmetric_polynomials`; proposal 1 in the 2026-09-09T1518 batch
names the sums $S_p(n)=\sum_{k=1}^{n}k^p$.

## Django and the client package both use the top-level name `numberdb`

What happened: a stored-value check for draft T182 needed Django models to
read the private draft and also tried to import the table generator, which
imports `numberdb.sage`. With `sys.path.insert(0, "/app")`, Django settings
were importable but `import numberdb.sage` resolved to the Django project
package and failed with `ModuleNotFoundError: No module named
'numberdb.sage'`. With `/app` appended after the client path, the client
package won the name and Django could not import `numberdb.settings`.

What to do instead: keep those checks in separate processes when using
`agents/sage.sh`: run the generator's `verify()` with the client package and
the API key, then run database-readback checks through Django without
importing the generator or `numberdb.sage`. If one process truly needs both,
handle `sys.modules["numberdb"]` deliberately rather than relying on
`sys.path` order.

Evidence: `/tmp/mahler_stored_check.py`, 2026-09-09, first failed while
loading `/work/generate.py` with `No module named 'numberdb.sage'`, then
failed during `django.setup()` with `No module named 'numberdb.settings'`.
The final version read T182 through Django only and reported `stored checks:
Touchard relation and A000296 through n=50`.

## A repair can see a private draft through the API but not its rendered page

What happened: the T182 repair prompt required both `GET /api/table?id=T182`
and the rendered page at `/T182`. The zeta3 bearer token read the private
draft through the API, but the rendered page and `/preview/T182` use the
site-session `request.user` guard rather than bearer authentication, so both
answered 404 from this unattended repair environment.

What to do instead: for private drafts, use the authenticated API document and
`audit_table`/generator verification as the checkable sources, and record that
the rendered page was unreachable unless the run has a browser login session.
Do not infer that the draft does not exist from a 404 on the rendered route.

Evidence: T182, 2026-09-09; authenticated `GET /api/table?id=T182` returned
the Mahler polynomial draft, while authenticated `GET /T182` returned 404.

## A repair cannot infer findings when the critique file is missing

What happened: the T183 repair task named `agents/critiques/T183.md`, but the
checkout did not contain that file and no run artifact contained a T183
critique. The authenticated API read of draft T183 succeeded, the rendered
route still answered 404 because the draft was private, `audit_table T183`
reported nothing, and the generator verified 31/31 stored entries. There was
therefore no original finding list to line up with the required repaired
report.

What to do instead: check that `agents/critiques/<TID>.md` exists before
repairing. If it is absent, do not reconstruct a critique from memory, logs or
the local generator; read the live table if possible, run the mechanical
checks that still apply, and write a single `left for a person` line in
`agents/critiques/<TID>-repaired.md` saying the original report is missing.

Evidence: T183, 2026-09-09; `agents/critiques/T183.md` was absent,
authenticated `GET /api/table?id=T183` returned the Bateman polynomial draft,
`GET /T183` returned 404, `audit_table T183` printed "Nothing to report", and
`generators/bateman-polynomials/generate.py` verified 31/31 entries.

## A silent `agents/sage.sh` run can be blocked before the remote command starts

What happened: after an interrupted Kummer draft-create attempt, a one-line
smoke test through `agents/sage.sh` printed nothing for more than thirty
minutes. Tracing the wrapper showed that it had not reached the remote lock,
Docker or Sage at all; it was blocked at the first `scp` that copies the
mounted script. At the same time, `curl https://numberdb.org/` through the
configured SOCKS proxy failed with "Failed to receive SOCKS5 connect request
ack", and the same curl with proxy variables unset timed out. No database
write could be checked from this session, because the allowed route to the
server never got as far as starting.

What to do instead: when a smoke test is silent, trace one no-key
`agents/sage.sh` call before assuming a Sage computation or a table lock is
slow. If the trace stops at `scp`, no throwaway container or database action
has begun; interrupt the diagnostic, report remote connectivity as the
blocker, and do not invent a draft id from the surrounding context.

Evidence: 2026-09-10, `bash -x agents/sage.sh /tmp/sage_smoke_kummer.py`
stopped after printing the `scp -q ... linode:/tmp/agent-run-...` command;
the earlier untraced smoke test was interrupted after more than thirty minutes
with no output.

## The LMFDB gate is about the rate through this proxy, and 90 seconds between requests keeps it open

What happened: the abelian-variety proposals needed rows from the LMFDB's
API for elliptic curves, genus 2 curves, abelian varieties over finite
fields and Maass forms. Through the SOCKS proxy, the first two requests of
a burst answered and the third was the reCAPTCHA page, as the T160 note
above found for `nf_fields`; ten knowl pages fetched in one loop a few
minutes later were all gated, including the ones that had answered singly.
A background script that slept 75 to 90 seconds between requests fetched
eleven API answers and object pages in a row without a gate, while the
foreground did nothing else outbound. The gate counts requests from this
address, so a screen run, an OEIS loop and an LMFDB fetch at the same time
share one budget.

What to do instead: put every LMFDB fetch of a run into one background
script with `sleep 90` between requests, writing each answer to `/tmp` as it
arrives, and do no other LMFDB request while it runs; use `_fields` so one
request carries what a hundred would otherwise; and never fetch a knowl in a
loop, since the knowl pages are gated like the API and the definitions they
hold are one hand fetch each. Foreground `sleep` is refused to an agent
here, so the pacing has to live in a `nohup` script.

Evidence: `/tmp/lmfdb_paced.out` and `/tmp/lmfdb_paced2.out`, 2026-09-11,
eleven answers at 00:17 to 00:32 local; the ten-knowl loop at 00:20 in the
same session, every body `RecaptchaChallengePageUi`.

## `audit_table` has no rule for an undefined TeX control sequence

What happened: the T212 critique found `\Sha` in a formula and in the
rigour note. It is the LMFDB's macro, absent from the bundle in
`static/vendor/mathjax/tex-svg.js` and from `static/js/load-mathjax.js`,
so MathJax's `noundefined` extension prints it in red on the page.
`audit_table T212 --links` says "Nothing to report": the document is
valid and no rule looks at what the typesetter knows.

What to do instead: a rule in
`numberdb_app/management/commands/audit_table.py` that extracts
`\word` control sequences from every `$...$` span and compares them
against the macro names the served bundle defines (the bundle is one
line; the names can be listed once and kept beside the rule) would have
caught this, and would catch the other LMFDB shorthands `\Q`, `\Z`,
`\F`, `\C` the moment somebody copies a knowl.

Evidence: `/tmp/crit212_out.txt`, 2026-09-11, audit output and rendered
HTML; `agents/critiques/T212.md` finding 1.

## A live table build can pass Sage once and then lose both write transports

What happened: the Maass-coefficient build reached the approved Sage runner
once, and `dry_run.py` completed on all 150 scratch entries. After a small
comment-only generator change, two more `agents/sage.sh` runs printed
nothing for about two minutes each and were interrupted before any script
output appeared. A one-line `agents/sage.sh` smoke test also stayed silent
before reaching Python. The HTTPS API route was unavailable from the session
too: `urllib` through `agents.api_edit.use_socks_proxy_if_set()` timed out
during the TLS handshake, and `curl -I --max-time 20 https://numberdb.org/api/docs`
timed out with no bytes received. No draft was created and no generator
published entries during this failure.

What to do instead: after a successful private dry run, do a short no-key
`agents/sage.sh` smoke test and a short HTTPS API smoke test before creating
the draft. If both stay silent or time out, stop before live table creation,
report transport as the blocker, and keep only scratch artifacts in `/tmp`.
This is an environment failure, not a table convention to teach in the public
skill.

Evidence: 2026-09-11. `/tmp/run_dry_maass.py` first reported 150 entries,
exact values, no prose warnings and an 88.2 KB block. Later runs of the same
wrapper and `/tmp/sage_smoke_maass.py` were interrupted after silence. The
HTTPS smoke test raised `URLError: <urlopen error _ssl.c:980: The handshake
operation timed out>`, and the curl probe exited 28 after 20 seconds.

## The laptop's root filesystem can be full, and a run cannot free it

What happened: the 2026-09-11T1148 stage-one run tried
`python3 -m pip download database_knotinfo` into `/tmp` to read KnotInfo's
Chern-Simons column, and pip died with `OSError: [Errno 28] No space left
on device`. `df -h /` showed 234 GB used of 234 GB, 82 MB available; `/tmp`
itself held 269 MB, none of it this run's (scratch from earlier runs, PDFs,
HTML copies). The pip cache and the earlier runs' scratch are the user's
files, so the run deleted nothing, skipped the check, and wrote the batch
(40 KB) and two lesson files, which fitted.

What to do instead: check `df -h /` in the first minute alongside the
network preflight; below a few hundred megabytes, do not start a download
or a large Sage export, say in the batch what was skipped for want of
space, and leave cleanup to a person. SnapPy's Rolfsen and census tables
are already installed under `~/.local` and need no download, so the
volume checks still ran; only the KnotInfo comparison was lost.

Two smaller findings from the same run. The KnotInfo site
(`knotinfo.math.indiana.edu`) is unreachable through the SOCKS proxy
(`URLError` from `source_names_it`), so a KnotInfo description page cannot
be screened from a run session; cite it and say it was not read. And
Wikipedia's *Hyperbolic Coxeter group* is a redirect to the
Coxeter-Dynkin diagram page, which no longer holds the hyperbolic simplex
tables; the volumes are on *Uniform honeycombs in hyperbolic space* and
*Paracompact uniform honeycombs*, so `source_names_it` must be pointed at
those.

Evidence: shell output in the 2026-09-11T1148 run; `df -h /` printed
`/dev/nvme0n1p5 234G 222G 82M 100% /`.

## SnapPy is installed on the host, not in the Sage wrapper

What happened: the closed Hodgson-Weeks census volume build needed SnapPy's
`OrientableClosedCensus` to extract the two sub-unit-volume triangulations.
Host Python had SnapPy 3.3.2, but the approved `agents/sage.sh` runner raised
`ModuleNotFoundError: No module named 'snappy'`. SnapPy's rigorous
`verify_hyperbolicity()` also refused on the host with `SageNotAvailable`,
so the build extracted the gluing rows and approximate shapes on the host,
stored them in `/tmp/closed_census_data.py`, and then used the Sage wrapper
only for the arb-ball Krawczyk certificate and value computation.

What to do instead: do not switch to the production container or invent a
Docker command to get SnapPy inside Sage. For table builds in this environment,
use host SnapPy only to extract static data, mount that data through
`agents/sage.sh`, and do the proof in the wrapper. If a future table needs
SnapPy's own Sage-backed verification, the wrapper image needs SnapPy installed
before the run starts.

Evidence: 2026-09-11. `python3 -c "import snappy; print(snappy.version())"`
reported 3.3.2 on the host, while `agents/sage.sh /tmp/check_snappy_sage.py`
reported `ModuleNotFoundError No module named 'snappy'`.

## Rendering a full draft through `/preview?table=...` can exceed the URL limit

What happened: the T219 repair had the authenticated draft document from
`/api/table?id=T219` and tried to render that exact YAML through the live
preview route, because `/T219` is a private draft and answers 404 outside a
session. The preview route takes the table from `request.GET`, so the full
document became a query string and the server answered HTTP 414
`Request-URI Too Large`. A minimal preview of the affected formula rendered
correctly and was enough to check the MathJax failure, but a whole-table
render needs the RequestFactory owner-view path already described above.

What to do instead: for a private draft, render the page in the throwaway with
`RequestFactory` as the draft owner, or preview only the small field whose
rendering is under test. Do not use `/preview?table=...` for a full document
once the YAML is more than a small scratch example.

Evidence: 2026-09-11, T219 repair. `/tmp/render_t219_preview.py` turned
`/tmp/T219-live-auth.json` into YAML and called the live preview endpoint; the
response was HTTP 414.

## The Sage wrapper can hang before it reaches the remote lock

What happened: during the 2026-09-11T1148 Coxeter simplex build, several
`agents/sage.sh` runs succeeded first and computed the tetrahedron volume
controls in arb. After an interrupted dry-run attempt, even
`agents/sage.sh /tmp/sage_hello.py` produced no output. Running the same
command under `bash -x` showed that it stopped at the first `scp` of the
main script to `linode:/tmp/agent-run-...`, before the remote lock, Docker
container or Sage process could start. Retrying after a two-minute pause gave
the same trace.

What to do instead: treat this as a transport outage, not as a table or Sage
failure. Do not create a NumberDB draft that still needs `dry_run.py`,
`verify()` or a generator fill through the wrapper. Wait for the copy path to
recover, then rerun a one-line `agents/sage.sh` probe before restarting the
official dry run.

Evidence: 2026-09-11. `bash -x agents/sage.sh /tmp/sage_hello.py` reached
`scp -q ... /tmp/sage_hello.py linode:/tmp/agent-run-...sage_hello.py` and
then remained silent until interrupted.

## OEIS entry and search pages answer 403 here; b-files still answer, and arXiv's TeX source stands in for a missing PDF reader

What happened: the 2026-09-12T1831 ideas run wanted OEIS names for Pisot and
Mahler-measure constants. `curl https://oeis.org/A060006` and
`https://oeis.org/search?q=id:A060006&fmt=json` both answered 403, with a
Cloudflare "Just a moment..." challenge page, with or without a browser
User-Agent. `https://oeis.org/A060006/b060006.txt` answered 200. Earlier runs
(2026-09-09) read entry pages from this machine, so this is new, and it may
be this address rather than OEIS for everyone.

The same run could not read an arXiv PDF. This runner has no `pdftotext`, no
`pip` and no `python3 -m pip`, so the lesson "arXiv PDFs can be read here
with curl and pdftotext" does not hold on it. `curl -L
https://arxiv.org/e-print/<id>` returned the gzipped TeX source, and grepping
the `.tex` gave the theorem tables and displayed formulas verbatim
(arXiv:1103.2995 and arXiv:1004.5344).

What to do instead: take OEIS evidence from b-files, or from the OEIS numbers
Wikipedia prints beside a value, and say the entry page was not read. For a
paper on arXiv, read the e-print source rather than looking for a PDF tool.

Evidence: 2026-09-12, `/tmp/b1831/`: HTTP codes 403, 403, 200 for the three
OEIS URLs above; `src_1103.2995/densities.tex` and `src_1004.5344/braids.tex`.

## `git add agents/lessons/PROPOSALS.md` exits 1 and stages the file anyway

What happened: `agents/lessons/` is matched by a `.gitignore` pattern, but
`PROPOSALS.md` in it is tracked. `git add` on it prints "The following paths
are ignored by one of your .gitignore files", exits 1, and stages the change
all the same. The `git add ... && git commit ...` chain stopped after the add,
and the commit never ran, though the change was already staged: `git
status` showed `M `.

What to do instead: after a failed add of a tracked file under
`agents/lessons/`, check `git status --short` and commit. Do not add `-f`
out of habit, because that would also stage ignored batches if the path is
widened.

Evidence: 2026-09-12, committing the `clebsch_gordan` lesson: exit code 1 from
`git add`, `M  agents/lessons/PROPOSALS.md` in `git status --short`, and a
plain `git commit` then succeeded (d3f23a5).

## The API key is also in the environment as `NUMBERDB_API_KEY`, so `env | grep NUMBERDB` prints it

What happened: the 2026-09-12T1922 ideas run ran
`env | grep -i "^NUMBERDB" | sed 's/KEY_FILE=.*/KEY_FILE=(set)/'` to see
which host `agents/sage.sh` would use. It masked `NUMBERDB_KEY_FILE`, as the
prompt's rule about the key file suggests, but the runner also exports the
key itself as `NUMBERDB_API_KEY`. The key was printed into the run's
transcript and log at about 19:42 UTC.

What to do instead: never list the environment by prefix. Ask for the
variable you need by name (`printenv NUMBERDB_REMOTE`). **The zeta3 key
printed in that run should be rotated.** The prompt says the key is "in the
file named by `NUMBERDB_KEY_FILE`", and a run that believes that has no
reason to expect it elsewhere. Either stop exporting `NUMBERDB_API_KEY` into
ideas runs, which only read, or say in the prompt that it is there.

Evidence: `agents/runs/20260912T192218Z-ideas.log`, the tool call above.

## `source_names_it` ignores words under three letters, so "q,t-Catalan numbers" is screened as "catalan"

What happened: `screen._distinguishing` keeps words longer than two letters,
and the hyphen and comma split "q,t-Catalan" into `q`, `t` and `catalan`.
`source_names_it('q,t-Catalan numbers', 'https://en.wikipedia.org/wiki/Catalan_number')`
passed. The raw wikitext of that page never contains "q,t". The family is
real and the page is the wrong source, and the screen cannot tell. The same
will happen to any name whose distinguishing part is a short symbol:
$q$-analogues, $j$-invariants, $p$-adic families, $E_8$.

What to do instead: when a name's short symbols are what distinguish it,
confirm the source by hand, for example with `curl ...&action=raw | grep`,
and cite a page whose title carries the whole name (here
arXiv:1003.0916, *q,t-Catalan numbers and knot homology*). A fix in
`screen.py` would search for the name's longest hyphenated token as a
phrase as well as for its words.

Evidence: 2026-09-12, `/tmp/b1922/screen_run.py` (pass) and the `grep -i
"q,t"` of the raw page (no match).

## numberdb.org stopped answering from this runner for over twenty minutes while other hosts answered

What happened: at about 19:40 UTC on 2026-09-12, `search_text` raised
`TransportError: ... The handshake operation timed out`. curl through
`ALL_PROXY` and with `--noproxy '*'` both returned `000` after 20 s, on
every attempt from 19:42 to at least 20:04. Wikipedia, arXiv's export API,
OEIS b-files and GitHub answered through the same proxy throughout.
`agents/sage.sh` was running locally (`NUMBERDB_REMOTE=local`) with load
average 0.00, so the Sage checks were not loading the site's machine.

What to do instead: a stage-one run can still finish its batch, since every
check except `already_here` and `search_text` is external. It should say
which corpus searches it could not make, because an unreachable corpus and
an empty answer read the same way.

Evidence: `agents/runs/20260912T192218Z-ideas.log`; the polling loops at
19:42, 19:51 and 20:02.

## `source_names_it` passes almost any Wikipedia page for a name whose words sit in navigation boxes

What happened: screening "Poincaré polynomials of finite Coxeter groups",
I took the 46 hits of a Wikipedia search for *Poincare polynomial Coxeter
group* and ran `source_names_it` on each. 43 passed. They included
*Straightedge and compass construction*, *Dimension*, *Cyclic group* and
*Timeline of mathematics*. The raw wikitext of the likely candidates (*Weyl
group*, *Root system*, *Kazhdan–Lusztig polynomial*, *E8*) contains
"Poincaré" only as *Poincaré duality* or in a citation title, and none of
them names the family. The words "finite", "coxeter" and "groups" are
common, and "poincar" turns up in footers and navigation templates, so the
substring test succeeds on unrelated pages. The earlier notes cover a
false fail (plurals, common nouns) and a short symbol; this is a false pass
from the words being everywhere.

What to do instead: a pass means little when every distinguishing word is
common. Grep the raw page (`...&action=raw`) for the family's name as a
phrase before citing it. Here no Wikipedia page did, and the citable source
was an arXiv abstract (1411.3233) plus Humphreys §1.11. A fix in
`screen.py` would strip navigation boxes and references before matching,
or require the words within a short window of each other.

Evidence: 2026-09-12, `/tmp/ideas/scr4.py` (43 `PASS` lines) and the
`grep -i poincar` of the raw wikitext of nine pages.

## On the local builder, `audit_table` needs either a deployed `.env` or the on-server wrapper cannot start compose

What happened: a T220 build needed `manage.py audit_table T220`. Host
`python3 manage.py audit_table T220` failed because Django is not installed
in the runner's Python. `agents/on-server.sh` first inherited
`NUMBERDB_REMOTE=local`, which it did not support; after adding the same
local-mode branch that `agents/sage.sh` has, it reached Docker Compose but
Compose refused because this checkout has no `.env`. The usual SSH targets
`local` and `linode` were not resolvable from this runner either, so the
management command could not be run against the live database from here.

What to do instead: when the run is on a builder checkout rather than the
deployed checkout, either provide a `NUMBERDB_RPATH` whose compose project has
`.env`, or run the audit through an API-backed helper. `agents/on-server.sh`
now understands `NUMBERDB_REMOTE=local`; that only solves the transport half,
not the missing deployment configuration.

Evidence: 2026-09-12, `python3 manage.py audit_table T220` raised
`ModuleNotFoundError: No module named 'django'`; `NUMBERDB_REMOTE=linode
agents/on-server.sh manage.py audit_table T220` and the inherited local value
both failed DNS; `NUMBERDB_REMOTE=local agents/on-server.sh manage.py
audit_table T220` reached compose and failed on missing
`/home/ubuntu/numberdb-website/.env`.

## A `sage.sh` process interrupted while Django is starting can leave its container holding the lock

What happened: trying to run `audit_table` through `agents/sage.sh` with a
small Django script produced no output. Sending Ctrl-C ended the local
command, but `docker ps` still showed
`numberdb-agent-run-1789254969-43101-8483` running `sage -python -u
/work/audit_t220.py`, and a later `agents/on-server.sh` command sat behind
the lock until that stale container was removed.

What to do instead: after interrupting a silent `agents/sage.sh` run, check
`docker ps` for a surviving `numberdb-agent-run-*` container before assuming
the lock is free. If the container is yours and the command was the one just
interrupted, remove it; otherwise leave it alone.

Evidence: 2026-09-12, `docker ps` showed the stale `audit_t220.py` container
five minutes after Ctrl-C, and `docker rm -f
numberdb-agent-run-1789254969-43101-8483` released the lock.

## A private draft's prose renders through `/preview` in pieces under 4094 bytes

What happened: the T221 critique needed the rendered page of a private
draft on a runner with no Django, so the `RequestFactory` path above was
closed. The whole prose section of the document sent to `/preview?table=...`
was 6.3 KB URL-encoded, and the server answered 400 "Request Line is too
large (6355 > 4094)". This is the limit behind the 414 in the T219 note.
Six requests did work, each carrying the title, one or two sections and one
entry. The sections were Links with anything that `CITE`s a link, and
Formulas with anything that `CITE`s a formula label; each piece was 1.1 to
2.5 KB. The rendered HTML showed the escaping, the `CITE`/`HREF` targets and
the entry anchors. MathJax runs in the browser and not in that HTML, so the
TeX was checked separately with `npm install mathjax-full@3` in `/tmp` and a
node script converting every `$...$` fragment. A control fragment with an
unclosed brace did raise an error.

Two more things from the same run. First, the SOCKS proxy on 127.0.0.1:1080
answered once and then refused every connection, with `ALL_PROXY` empty and
no `ssh -D` process running. numberdb.org answered `curl` directly, so the
proxy is not always what reaches the site. Second, the docstring of
`audit_table` lists "notation used in a formula and defined nowhere in the
table" among its checks, but no code in the command makes that check. T221
uses $\zeta_K$ undefined and the audit will pass it.

What to do instead: render a private draft through `/preview` in pieces kept
under 4 KB after URL-encoding, carrying the Links and Formulas that the
section's `CITE`s need. Typeset the TeX in node rather than inferring it.
Try `curl` without the proxy before concluding the site is down. Either
implement the notation check or remove it from the docstring.

Evidence: 2026-09-13, T221 critique. `/tmp/T221_p[a-f].html`, all 200;
`/tmp/crit221_mj/check.js` reported "checked 367 errors 0" and the control
"checked 3 errors 1"; `curl --socks5-hostname 127.0.0.1:1080` gave
"Failed to connect ... Couldn't connect to server".

## `agents/sage.sh` does not provide the Django checkout for `audit_table`

What happened: after repairing T221 through the API, the required
`manage.py audit_table T221` could not run in either local Python or the
Sage helper. Host `./manage.py audit_table T221` used `/usr/bin/env python`,
but this runner has no `python` executable. `python3 manage.py audit_table
T221` then failed because Django is not installed. A Sage helper script run
through `agents/sage.sh` showed that `/app/manage.py` is absent inside that
helper environment, so the helper is useful for Sage computations and API
work but not for invoking this checkout's Django management commands.

What to do instead: do not route `audit_table` through `agents/sage.sh` unless
the helper image has been changed to mount the Django app. On this runner,
use an API-backed audit helper or a deployed checkout with Django installed.
When neither is available, run the deterministic JSON checks locally and say
explicitly that the official management command did not run.

Evidence: 2026-09-13, T221 repair. `./manage.py audit_table T221` reported
`/usr/bin/env: 'python': No such file or directory`; `python3 manage.py
audit_table T221` reported `ModuleNotFoundError: No module named 'django'`;
`agents/sage.sh /tmp/run_audit_t221.py` printed `exists /app: False` and
`helper image has no /app/manage.py`.

## A `/preview` piece shows no values unless `Parameters` is sent with `Numbers`

What happened: the T225 critique rendered its private draft through
`/preview?table=` in pieces, as the T221 note describes. The draft's
`Numbers` is a mapping keyed by census name. The pieces that carried
entries without the `Parameters` section answered 200. They printed only
the row names (`m004`, `m009`) with no value, no comment and no row label,
which reads exactly like an entry that failed to render. The same entries
sent with `Parameters` rendered in full, comment and links included.

What to do instead: include `Parameters` in every preview piece that carries
entries of a table with named parameters. Do not read a bare list of keys as
a rendering fault in the table.

Evidence: 2026-09-13, `/tmp/crit225/p_g.html` without `Parameters` and the
same rows after `Parameters` was added. Both answered 200.

## OEIS search pages answer 403 with a Cloudflare challenge from this runner

What happened: on 2026-09-13 every `curl "https://oeis.org/search?q=...&fmt=json"`
through `ALL_PROXY` answered `403 text/html` with a "Just a moment..."
Cloudflare challenge, for seventeen different queries. JSON parsing then
failed on every one, so an unguarded script reads it as "no OEIS match"
rather than as "OEIS not reached". Wikipedia's `index.php?action=raw` answered
throughout.

What to do instead: check the HTTP status before parsing an OEIS answer. To
get a constant's OEIS number, read the raw wikitext of the Wikipedia article
that tabulates it (`grep -oE 'A[0-9]{6}'`). Wikipedia cites the A-number beside
the digits. Say in the batch that the digits were compared with Wikipedia's
and not with OEIS's.

Evidence: `/tmp/o.txt` from the ideas run 2026-09-13T0847: `403
text/html; charset=UTF-8`, `<title>Just a moment...</title>`.

## `already_asked` runs out of GitHub's unauthenticated search budget after about nine names

What happened: `screen.already_asked` calls `api.github.com/search/issues`
without a token. In one run, screening fourteen names, the tenth and later
calls returned `could not ask GitHub (HTTPError)`. The search API allows
ten unauthenticated requests a minute. The screen does say that it failed,
so nothing was hidden, but the remaining names went unscreened.

What to do instead: redo the failed names with `gh search issues --repo
numberdb/numberdb-data "<words>"`, which is authenticated. Or pause for a
minute after every eight names. Longer term, `already_asked` could use `gh`
or a token when one is present.

Evidence: ideas run 2026-09-13T0847. The names from "Euler-Lehmer constants"
onward, in `/tmp/scr.py`'s output.

## `agents/on-server.sh` with `NUMBERDB_REMOTE=local` needs a local `.env`

What happened: while finishing T226, `agents/on-server.sh manage.py
audit_table T226` did not reach Django. This runner had
`NUMBERDB_REMOTE=local`, so the wrapper used the local checkout and local
Docker Compose file. Compose then stopped because `/home/ubuntu/numberdb-website/.env`
was absent. The direct host path was not available either, since `python3
manage.py audit_table T226` failed earlier with `ModuleNotFoundError: No
module named 'django'`.

What to do instead: if the wrapper is meant to audit the deployed checkout,
set `NUMBERDB_REMOTE` and `NUMBERDB_RPATH` for that environment before
running it. If the run is confined to this local checkout, use the API-backed
document checks and say explicitly that the official management command did
not run.

Evidence: 2026-09-13, T226 build. The wrapper reported `env file
/home/ubuntu/numberdb-website/.env not found`.

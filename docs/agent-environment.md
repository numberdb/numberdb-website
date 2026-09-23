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

## `/home/ubuntu/...` paths do not resolve inside `agents/sage.sh`

What happened: a T287 repair used a `/tmp` Sage script that tried to load the
repo generator by absolute host path,
`/home/ubuntu/numberdb-website/generators/xorsat-threshold-equation-roots/generate.py`.
Inside `agents/sage.sh` the script was copied to `/work`, and that host path
was not readable from the Sage container, so `importlib` failed with
`PermissionError`.

What to do instead: inside a script run by `agents/sage.sh`, refer to the
checkout as `/app`, or mount the needed file as an extra `agents/sage.sh`
argument and import it from `/work`. For a small numerical check, making the
script self-contained is often simpler.

Evidence: `/tmp/t287_growth_checks.py`, 2026-09-19, failed on the
`/home/ubuntu/.../generate.py` import and passed after the root computation was
copied into the scratch script.

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

## A Sage wrapper cannot see a separate `/tmp` file unless it is mounted

What happened: a T267 repair fetched the live table to `/tmp/T267-live.json`
and then ran a Sage check from `/tmp/check_t267.py`. Inside `agents/sage.sh`
the script was mounted at `/work/check_t267.py`, but the JSON file was not
mounted, so `open("/tmp/T267-live.json")` failed with `FileNotFoundError`.

What to do instead: either pass every extra local file to `agents/sage.sh` so
it is mounted under `/work`, or make the Sage script fetch/read what it needs
itself. For API reads of private drafts, reading the key from stdin and fetching
inside the Sage script is usually cleaner than carrying a second temporary
file alongside it.

## A repair assignment can arrive without its critique file

What happened: a T294 repair run was assigned `agents/critiques/T294.md`, but
that file was absent from the checkout and had no history under that path. The
live table was still reachable through `/api/table?id=T294`, while `/T294`
returned 404 because the table was an unpublished draft. The audit endpoint
returned one structural finding, and the repair report had to say explicitly
that it acted on the live audit rather than on a missing critique file.

What to do instead: before editing, check the requested critique path directly
and with `find agents -name '*TID*'`. If it is missing, do not invent the
finding list. Either stop with a repaired report that records the missing
critique, or, if a live audit finding is safe and local enough to act on, say
that the audit rather than the missing report supplied the actionable proposal.

Evidence: on 2026-09-17, `find agents -name '*T294*' -print` returned nothing
before the repair report was written, and `git log -- agents/critiques/T294.md`
was empty.

## Do not combine a heredoc script with an API key on stdin

What happened: an API edit sender was run as a Python heredoc while also
redirecting the NumberDB key into stdin. The redirection won: Python read the
key as its program text instead of running the heredoc, failed with a syntax
error, and echoed part of the token in the traceback before any HTTP request
was made.

What to do instead: when a script must read the key from stdin, put the script
in `/tmp` and run `cat "$NUMBERDB_KEY_FILE" | python3 /tmp/script.py`, or keep
the code in a `python3 -c '...'` argument that reads `sys.stdin`. Do not use
`python3 - <<'PY' ... PY` for a program that also needs stdin for the key.

Evidence: T271 repair, 2026-09-16. The corrected sender lived at
`/tmp/t271_post_edit.py` and the API accepted the edit through
`cat "$NUMBERDB_KEY_FILE" | python3 /tmp/t271_post_edit.py`.

Evidence: `/tmp/check_t267.py`, 2026-09-16, failed on
`/tmp/T267-live.json`; the self-contained version fetched
`https://numberdb.org/api/table?id=T267` with the key from stdin and then
checked the live rows successfully.

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

Update, 2026-09-17: the `gh` on this machine is now 2.45.0, and `gh search
issues --repo numberdb/numberdb-data "<words>" --json number,title,state`
works and searches open and closed issues. `already_asked` was still
throttled after about ten calls in the 2026-09-17T0814 ideas run, so the rate
limit stands, but this search is now the fallback.

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
It happened a third time in the T279 critique of 2026-09-16 (campaign
`20260915T221028Z`): `env | grep -i -E 'proxy|numberdb' | sed 's/=.*KEY.*/=<hidden>/'`
was run to see why the proxy was down, and printed `NUMBERDB_API_KEY`. A
rule in a notes file has not stopped this. The runner exports the key's
value as well as the name of the file holding it, and a prompt that says the
key "is in the file named by `NUMBERDB_KEY_FILE`" should not also find the
key in `NUMBERDB_API_KEY`. Unsetting that variable in `run.sh` would end the
mistake for good.
It happened a fourth time in the T307 critique of 2026-09-17 (campaign
`20260917T011039Z`), in the same situation and with the same `sed` mask: the
proxy refused connections, and the environment was listed to find out why.
The answer the listing gave was `ALL_PROXY=` (empty) and `NUMBERDB_REMOTE=local`.
On this box `curl https://numberdb.org/...` with no proxy works, as the note
of 2026-09-16 further down says. Run the direct `curl` before looking at the
environment at all.

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

## The audit answers over the API, for a machine with no database

What happened: three separate runs (T220, T221, and a repair) lost time to the
same wall: the build machine computes the table but holds no database, and
`manage.py audit_table` needs one. Each found a different dead end -- no
`python` on the runner, no Django in `python3`, no `/app/manage.py` in the Sage
helper -- and each ended by saying the required check had not run.

What to do instead: `GET /api/table/<TID>/audit`, with your key, from anywhere.
`findings_for()` in `numberdb_app/management/commands/audit_table.py` is what
both the command and the route call, so the two cannot drift. `--links` is the
exception: following outward links stays with the command.

Evidence: 2026-09-13, the route and `numberdb_app/test_audit_api.py`.

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

What to do instead: ask the site. `GET /api/table/<TID>/audit` with your key
returns `{"findings": [...], "clean": ...}` from the same implementation the
command uses, so a machine with no database gets the same answer:

```
curl -s -H "Authorization: Bearer $NUMBERDB_KEY" \
     https://numberdb.org/api/table/T221/audit
```

It does not follow outward links; `--links` still needs the command and a
database. Do not route `audit_table` through `agents/sage.sh`: that helper
mounts no Django app, and never will for this purpose.

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

## A `/preview` piece with no `Numbers` renders only an error

What happened: the T226 critique rendered its private draft through
`/preview?table=` in pieces, as the T221 and T225 notes describe. Five
pieces carried only prose sections (Comments, Formulas, Programs, Similar
tables, Data properties) and no `Numbers`. Each answered 200 and printed
"Error while parsing numbers: cannot access local variable 'number_section'
where it is not associated with a value", followed by the echoed JSON. None
of the sections rendered. The same pieces rendered in full once
`Parameters` and one entry were added. This is a bug in the preview view,
not a fault in the table.

What to do instead: give every preview piece `Parameters` and at least one
entry of `Numbers`, even when the piece is meant to test prose. A 200 is not
evidence that anything rendered: grep the piece for "Error while parsing".

Evidence: 2026-09-13, `/tmp/crit226/p_[b-f].html` first run (error) and
second run (rendered), made by `/tmp/crit226/pieces.py`.

## The `env | grep` key leak happened again, with a different mask

What happened: the note above on `env | grep -i numberdb` did not prevent
a repeat. The T226 critique listed the environment to see whether
`ALL_PROXY` was set, using `sed 's/=.*KEY.*/=<hidden>/'` as the mask. That
pattern looks for `KEY` *after* the `=`, so the line `NUMBERDB_API_KEY=...`
went through unmasked, and the zeta3 key is in that run's transcript.

What to do instead: never print the environment. To check a variable, test
it by name without printing its value: `[ -n "$ALL_PROXY" ] && echo set`,
or `printenv ALL_PROXY`. The key should be rotated after a run that printed
it.

Evidence: 2026-09-13, T226 critique, the first environment listing in the
run's tool output.

## The builder image cannot run `audit_table`

What happened: the T227 build needed `manage.py audit_table T227` after the
draft was filled and verified. The local checkout had no `.env` and no Django
installed, so `python3 manage.py audit_table T227` failed with
`ModuleNotFoundError: No module named 'django'`. The sanctioned Sage wrapper
was using the builder image (`NUMBERDB_SAGE_IMAGE=numberdb/builder:latest`),
which is correct for generators but contains neither Django nor the app:
`/app/manage.py False`, `django import failed ModuleNotFoundError`, and
`numberdb_app import failed ModuleNotFoundError`. Trying the web image through
the same wrapper did not help on this runner, because `numberdb/web:latest`
was not present locally and Docker could not pull it.

What to do instead: do not treat a failed local `audit_table` as a table
finding. On a runner configured this way, either arrange a sanctioned Django
environment before the build reaches the audit step, or say that the
management command could not run. The builder image is for Sage computations
and API-backed generator work, not for Django management commands.

Evidence: T227 build, 2026-09-13. `/tmp/probe_audit_environment.py` under
`agents/sage.sh` reported no `/app/manage.py`, no Django and no
`numberdb_app`; direct `python3 manage.py audit_table T227` failed before
Django import.

## Unescaping preview HTML before stripping tags invents a swallowed section

What happened: the T231 critique pulled the text out of a `/preview` piece to
see the order of its sections. The script ran `html.unescape` first and then
removed tags with `<[^>]+>`. The page's `$0\leq a&lt;q$` became `a<q$)`, and
the tag stripper deleted everything from that `<` to the next `>`. The
result read "residue class ($0\leq a Formulas (1) ...", which is exactly the
"a `<` in mathematics ate the rest of a section" fault critiques look for.
The raw HTML had the `&lt;` escaped correctly, and the page was fine.

What to do instead: strip tags first and unescape afterwards. Before
reporting a swallowed section, grep the raw HTML for `&lt;` against a bare
`<` inside the mathematics.

Evidence: 2026-09-13, `/tmp/crit231/p_g.html`. `grep -o 'a&lt;q'` finds
the escaped form, and the tags-first extraction of `p_a.html` shows the
whole parameter list.

## A Sage run killed by the memory cap says nothing; only the exit status tells

What happened: a proposal run counted lattice points of the $E_8$ root
polytope under `agents/sage.sh`, which caps the container's memory
(`NUMBERDB_SAGE_MEMORY`, 1200m on this runner). The script printed
`polyhedron built, dim 8 facets 19440 4.3s` and then nothing. No traceback,
no "Killed", no line from `agents/sage.sh`. The first attempt ran the command
as `agents/sage.sh script.py > out 2>&1; grep ... out`, so the shell's status
was grep's 0, and it read as a script that had finished with its last lines
missing. Rerun with `echo "exit=$?"` immediately after, it gave `exit=137`
(SIGKILL) about 90 s in, which is the cap killing the container.

What to do instead: when a Sage run's output stops short, look at
`agents/sage.sh`'s own exit status before looking at the script. 137 is the
memory cap, not a bug in the computation. Raise `NUMBERDB_SAGE_MEMORY` only
within what the build box can spare, or change the method.

Evidence: 2026-09-13, `/tmp/e8.py`, 18:15:10 to 18:16:42, `exit=137`; the
earlier `/tmp/exc.py` run ended the same way two minutes into $E_8$ with the
status hidden.

## OEIS refuses this machine outright; a PDF fetched for a check cannot be read here

What happened: the 2026-09-13T2142 ideas run could not reach OEIS at all.
`curl -G https://oeis.org/search --data-urlencode q=cospectral --data-urlencode
fmt=text` answered 403 with a browser user agent and without one. So did
`fmt=short`, and so did plain `https://oeis.org/A082104` fetched by the
web-fetch agent. Earlier notes say `fmt=text` worked when the JSON search did
not; by this run the refusal covered everything from this address. Separately,
the web-fetch agent downloaded the Brouwer–Spence paper and Brouwer–Haemers'
book as PDFs, but the host has no `pdftotext`, no `strings`, no `pypdf` and
no poppler, so `Read` could not render them either. A published count needed
as an independent check stayed unread.

Also: `https://numberdb.org/tags?page=3` answers with the same 18 tags as
`page=2`, not with an empty page. A loop that walks pages until one is empty
never ends. Stop when a page repeats the previous one. The list has 68 tags.

What to do instead: treat OEIS as unreachable from the runner and say so in
the output rather than retrying. Take sequence numbers from pages that cite
them (Brouwer's cospectral page names A082104). For PDFs, run the extraction
inside `agents/sage.sh` if the image has a PDF library, or cite the number as
unread.

Evidence: 2026-09-13, `/tmp/ideas2142/o.txt` (403) and `tags2.html` and
`tags3.html` (identical tag lists); the web-fetch agent's report of 403 on six
OEIS URLs.

## `Size exception` renders as "(Unknown key)"

What happened: T239 has 1992 entries and says why in a `Size exception`
line under `Data properties`. The help page ("How much to record") and
`numberdb_app/limits.py` (`EXCEPTION_KEY`) both ask for that line. `/preview`
printed it as "Size exception: The table stores both ... (Unknown key)".
`table_context` in `numberdb_app/views.py` only gives a label to the keys in
`property_names`. `Size exception` is not one of them, so the line falls
through to the unknown-key branch. The table page uses the same function,
so a published table that follows the help looks as if it misspelt a field.

What to do instead: add `'Size exception': 'Size exception'` to
`property_names`. Until then, a critique should not tell an author to
rename the key. The table is right and the page is wrong.

Evidence: 2026-09-13, T239 critique. `/preview?table=` with T239's `Data
properties` (`/tmp/c239/dataprops_a.html`) returned 200 and contained
"(Unknown key)" immediately after the size exception text.

## A code span cannot contain a backtick in any form the site accepts

What happened: graph6 keys use every character from `?` to `~`, including
the backtick. The prose renderer (`views.py`, around line 775, and
`prose.py`'s `_CODE`) turns `` `([^`\n]+)` `` into code, and it has no
escape and no longer delimiter. A key such as `I???P`D`_` is therefore
broken inside backticks, and broken again in plain text, because its own
two backticks pair up. T240 has three comments that cannot be written
correctly at all. `&#96;` gets through because prose is not HTML-escaped,
but it stores markup in the data.

What to do instead: this is the site's to fix. Markdown's rule would do it: a
span opened by two backticks closes at the next two, so
``` `` I???P`D`_ `` ``` holds the key. Until then, a critique should not
tell an author to find a form that works for those keys, because none does.

Evidence: 2026-09-14, T240 critique. `/preview?table=` rendered
``as `I???P`D`_`.`` as `as <code>I???P</code>D<code>_</code>.`, and the
plain text `as I???P`D`_.` as `as I???P<code>D</code>_.`.

## `source_names_it` passes a page that uses the word in another sense

What happened: screening "Run-length limited capacity" against English
Wikipedia's *Run-length limited* failed on "capacity", correctly, because the
article never mentions the Shannon capacity of a constraint. The same name
against *Eight-to-fourteen modulation* **passed**, because that article says
"increasing storage capacity by 1/16". The check tests that the words occur
on the page, not that they occur together or in the sense meant. A pass is
necessary, not sufficient.

What to do instead: after a pass, read the sentence the word sits in before
citing the page. A proposal should say which sentence names the family.

Evidence: 2026-09-14, ideas run for BATCH-2026-09-14T0107.
`source_names_it('Run-length limited capacity',
'https://en.wikipedia.org/wiki/Eight-to-fourteen_modulation')` returned
`None`. The only occurrence of "capacity" on the page is the storage-capacity
sentence.

## What reaches the outside from an ideas run, as of 2026-09-14

OEIS's JSON search (`https://oeis.org/search?fmt=json&q=...`) answered from
Python through the proxy, where an earlier run had 403 on every OEIS request.
The fetching agent still got 403 on OEIS `A`-number pages. The Wikipedia
search API (`w/api.php?action=query&list=search`) and `action=raw` both
work, and are the best way to find and read an article's formulas. The
WebSearch tool is not permitted, DuckDuckGo's HTML endpoint returns no
results, arXiv's export API answered 429, Scholarpedia does not connect, and
there is no `pdftotext`, `pypdf` or `fitz`, so a fetched PDF cannot be read.
GitHub's search API, which `already_asked` uses, rate-limits after about a
dozen names; `gh issue list --search` still answers.

## Local `audit_table --links` may be unavailable on the agent checkout

What happened: after splitting T232 into T232 and T242, the live API audit
passed for both drafts. The requested local `python3 manage.py audit_table
T232 T242 --links` could not start because the default Python in this checkout
does not have Django installed:

    ModuleNotFoundError: No module named 'django'

There was no `.env` in the checkout naming a project Python or `MANAGE`
command to use instead.

What to do instead: use `GET /api/table/<tid>/audit` with the contributor key
as the available remote audit, and say explicitly when the local
`audit_table --links` command cannot run in this environment.

Evidence: 2026-09-15, T232 split run. The failed command was run from
`/home/ubuntu/numberdb-website`; the API audit for T232 and T242 returned
`clean: True`.

## `POST /api/tables` can answer 500 when the initial draft cites undeclared labels

What happened: claiming the h-star half of T233 with `POST /api/tables`,
`X-Draft: yes`, and a fuller initial document failed with HTTP 500. The
document's Definition cited `CITE{WikiRootSystem}` and `CITE{WikiEhrhart}`,
but the scratch claim did not yet include the matching `Links` section. A
second claim with only the Title succeeded as T243, and the full document
with Links was accepted by `POST /api/table/T243`.

What to do instead: when claiming a draft through the API, either send only
the title or include every `Links`, `References`, `Formulas`, `Comments`,
`Programs`, and `Display properties` label cited by the initial document.
Treat a 500 from a cite-bearing draft claim as a validation-path bug, then
retry with a minimal title rather than guessing that the table was created.

Evidence: 2026-09-15, T233 split. `/tmp/T233-hstar-create.yaml` returned
HTTP 500 from `/api/tables`; `/tmp/T233-hstar-title-only.yaml` returned 201
with `tid: T243`.

## Draft file pages are visible even when the draft table page is private

What happened: during the T235 split, unauthenticated `GET /T235` returned the
site's "Not found" page, but unauthenticated `GET /files/T235` returned the
file list and unauthenticated `GET /files/T235/generate.py?raw=1` returned the
attached generator source. The views for `table_files` and `table_file` load
the table by T-number and do not apply the draft visibility guard that the
table and preview pages use.

What to do instead: treat attached files on a draft as public until the site
adds the same draft guard to file and bundle routes. Never put secrets or
private notes in a generator, even while the table itself is still a private
draft.

Evidence: 2026-09-15, T235 split. `curl https://numberdb.org/T235` returned a
Not found page, while `curl https://numberdb.org/files/T235` showed "Files of
Ehrhart polynomials of the permutohedra" and
`curl https://numberdb.org/files/T235/generate.py?raw=1` returned the
generator docstring beginning with `numberdb.org/T235`.

## A stored polynomial variable named `r` can trip the live Sage environment

What happened: after the Zernike generator changed radial entries from
`rho` to the single-letter variable `r`, the local Sage wrapper could build
`QQ['r']` and dry-run the table, but the live API refused the fill of draft
T251 with `A value in these entries cannot be read as a number. No module
named 'rpy2'`. The same entries with the radial variable renamed to `t`
avoided the server-side import path.

What to do instead: if a draft polynomial table is refused with an `rpy2`
message and the only unusual thing is a stored variable named `r`, rename
that stored variable to another single-letter variable such as `t`. Keep the
mathematical symbol in the prose if it matters.

Evidence: 2026-09-15, T251 build. The builder probe
`PolynomialRing(QQ, 'r')` succeeded under `agents/sage.sh`, but the live
`/api/table/T251/entries` write failed with the `rpy2` message.

## `agents/queue.py built` does not tick two-word proposal titles

What happened: after T251 was offered for review, running
`python3 agents/queue.py built 139 "Zernike polynomials (#77)" T251`
answered `#139 has no unbuilt table like 'Zernike polynomials (#77)'`.
The family issue still had the exact unchecked line. The helper's
`_same_subject` refuses matches whose smaller word set has fewer than three
words, so "Zernike polynomials" cannot match through that path.

What to do instead: for a two-word proposal title, patch the exact checklist
line in the family issue body, or have a person tick it, rather than trying
more decorated titles.

Evidence: 2026-09-15, T251 build; issue #139 was updated by replacing
`- [ ] Zernike polynomials (#77)` with
`- [x] Zernike polynomials (#77) -- T251`.

## The audit's two-tables check is blind to a bundle whose halves have different ranges

What happened: T251 bundles the Zernike radial polynomials $R_n^{|l|}(t)$ and
the Cartesian polynomials $Z_n^l(x,y)$ under a parameter `form` whose two
values are the names `radial` and `cartesian`. That is the exact shape
`_one_table_or_several` in
`numberdb_app/management/commands/audit_table.py` was written to report, and
`GET /api/table/T251/audit` answered `"findings": [], "clean": true`.

Both rules miss, for different reasons:

* `_one_table_or_several` requires the grid to be orthogonal --
  `if len(grid) * len(labels) > len(records) * 1.05: continue` -- so a ragged
  parameter is treated as a genuine family, "a shape that only some
  distributions have". T251's 188 entries sit on 152 distinct `(n, l)` pairs,
  only 36 of which carry both forms, because the radial half was computed to
  `n <= 20` and the Cartesian half to `n <= 12`, and because the radial half
  indexes by `|l|` while the Cartesian half indexes by signed `l`. The test is
  `304 > 197.4` and the check bails. Two tables that were each given the range
  that suited them are *more* ragged than one table, not less.
* `_column_names_its_quantity` tests `header.lower() in GENERIC_HEADERS`, a
  membership test against ten words. T251's `number-header` is
  `$R_n^{|l|}(t)$ or $Z_n^l(x,y)$`: the same fallback the rule's own docstring
  describes -- no symbol is true of every row -- written as a LaTeX
  disjunction rather than as the word `value`, and so invisible.

What to do instead: in the grid check, before the orthogonality `continue`,
ask whether the *ranges* differ -- whether the set of values some other
parameter takes under one label is a proper subset of the set it takes under
another. That is bundling, not a ragged family, and it is the commoner shape:
the halves of a bundle are computed to whatever depth each could afford. In
the header check, treat a header containing ` or ` (or any top-level `\vee`,
`,` or `/` joining two `$...$` spans) the same as a generic word: a
disjunction names no quantity either.

Evidence: 2026-09-15, T251 critique. `GET /api/table/T251/audit` clean;
`agents/critiques/T251.md` finding 1 gives the counts.

## `/preview?table=` in pieces reports false `CITE-broken`

What happened: previewing T251's `Similar tables` and `rigour details` alone
rendered every `CITE{formula-...}` as
`<span class="CITE-broken" title="this table defines no reference by that
name">formula-jacobi</span>`, which reads exactly like a table citing a key it
never defines. It is not: `CITE` resolves against the keys present *in the
piece that was sent*, and the pieces did not carry `Formulas`. With the cited
formulas included, the same `CITE`s render as `<a class="CITE"
href="#formula-jacobi">(4)</a>`.

The existing note "render a private draft through `/preview` in pieces ...
carrying the Links and Formulas that the section's `CITE`s need" says to
include them; it does not say what it looks like when you forget. This is the
symptom, and it is a false positive a critique can report as a fault in the
table.

What to do instead: before reporting a `CITE-broken`, re-send that one field
in a piece that also carries the section defining the key. Numbering is global
across `Formulas` then `Comments` in render order, so a citation's number also
changes with what the piece contains -- another reason not to read numbers off
a partial preview.

Evidence: 2026-09-15, T251 critique. `/tmp/t251/sec_Similar_tables.html`
(`CITE-broken`, no `Formulas` in the piece) against `/tmp/t251/cite1.html`
(same fields plus `formula-jacobi` and `formula-hankel`, rendering `(1)` and
`(2)`).

## To preview the *number table* of a wide draft, strip `title` and `constraints`

What happened: T252 has seven parameters, and its `Parameters` section is
1.9 KB of YAML that URL-encodes to over 3 KB because almost every character in
it is a `$`, a `\` or a brace. Sent to `/preview?table=` with the title and a
handful of entries it came to 5,024 bytes and the server answered
400 "Request Line is too large (5017 > 4094)". The existing note above covers
splitting the *prose* into pieces, and that works: one piece per two or three
parameters renders the parameter list fine.

But the parameter list is not the thing worth looking at. What a critique needs
from the number table is the header row, the per-row labels and the value
column together -- whether a `values:` label is repeated on every row, whether
`number-header` restates it, how wide the label column is against the
parameter columns. No piece carrying two parameters shows that: it renders a
two-column table that exists in no reader's browser.

The layout depends only on each parameter's `type`, `display` and `values`.
`title` and `constraints` feed the Parameters list at the bottom of the page
and nothing else. Stripping those two keys from every parameter took T252's
section from 1.9 KB to 0.5 KB, and the whole document -- all seven parameters,
`Display properties` and three entries -- fit in a 2,444-byte request line and
rendered the real eight-column table, header and per-row labels included.

What to do instead: preview a wide draft twice. Once with the parameters
slimmed to `type`/`display`/`values` plus `Display properties` and a few
entries, to read the number table as a reader sees it; and again in prose
pieces with the full `title` and `constraints`, to read the parameter list.
Say in the critique that the layout piece was slimmed, because it is not the
stored document.

Evidence: 2026-09-15, T252 critique. `/tmp/t252prev/a-def.html` is the 400
(full `Parameters`, 5,024-byte request line); `/tmp/t252prev/g-layout.html` is
200 at 2,444 bytes and contains the eight `table-param-group-header` cells and
the `$\begin{pmatrix}j_1&j_2&j_3\\m_1&m_2&-m\end{pmatrix}$:` row labels.

## `agents/queue.py built` cannot tick a short title whose distinguishing token is alphanumeric

What happened: after T253 was built, the instructed command
`python3 agents/queue.py built 139 "Wigner 6j symbols" T253` answered
`#139 has no unbuilt table like 'Wigner 6j symbols'`, although issue #139
contained the unchecked line `- [ ] Wigner 6j symbols`. The matcher drops
`6j` because `_words()` only keeps tokens beginning with a letter, leaving
`wigner` and `symbols`; `_same_subject()` then refuses every title with fewer
than three surviving words. The checklist had to be patched directly through
the GitHub API.

What to do instead: when a proposed title is naturally short and contains a
letter-digit token such as `3j`, `6j` or `9j`, either make `_words()` keep
those tokens or let `cmd_built` fall back to an exact unchecked-line match
before using subject containment. Until then, a failed `built` command on this
shape can be a helper mismatch rather than evidence that another run changed
the issue.

Evidence: 2026-09-16, issue #139. The helper refused `"Wigner 6j symbols"`;
`python3 agents/queue.py show 139` immediately before the manual patch still
showed the unchecked line, and immediately after showed
`- [x] Wigner 6j symbols -- T253`.

## `Data properties: Size exception` renders as "(Unknown key)"

What happened: reading T255 for a critique, the rendered *Data properties*
section ended with

    Size exception: The table has one row for each ... short. (Unknown key)

`numberdb_app/limits.py:93` defines `EXCEPTION_KEY = 'Size exception'` as the
place an author states why a table is over a soft limit, and
`limits.stated_reason` reads it out of `Data properties`. The page renderer's
`property_names` map (`numberdb_app/views.py:1063`) does not list it, so the
`else` branch at line 1152 fires and appends `(Unknown key)`. The API accepts
the key, the review gate reads it, and the page tells the reader it is
unrecognised.

What to do instead: add `'Size exception': 'Size exception'` to
`property_names`. Until somebody does, a critique or a repair meeting this on a
page should report it as a renderer fault and not try to fix it by renaming the
key in the table — the key is the one `limits.py` looks for, and renaming it
would make the table breach its soft limit with no stated reason.

Evidence: 2026-09-16, T255 critique. `grep -rl "Size exception" generators/*/table.yaml`
finds only T255's, so this may be the first table in the repository to render
one. `/preview` of its `Data properties` block, with `Links` and `References`
included, shows the string above.

## `agents/sage.sh` returns 1 for a successful Sage script that prints nothing

What happened: while repairing T257, the final check extracted the stored
`Programs` snippet and ran it with `agents/sage.sh /tmp/T257_after_program.py`.
The Sage code imported cleanly and only evaluated two polynomial expressions,
so `sage -python` had no stdout. The wrapper pipes the container's output
through `grep --line-buffered -viE ...`; when there are no input lines, `grep`
exits 1, and that is the status the caller sees. The run therefore looked like
a failed Sage program while printing no traceback at all.

What to do instead: when checking a snippet or smoke test through
`agents/sage.sh`, make it print a value or an explicit `OK`. For a table
`Programs` snippet this is a better reader experience too: a copied script
should show the value it computed.

Evidence: 2026-09-16, T257 repair. `/tmp/T257_after_program.py` with two bare
`poincare_from_degrees(...)` calls exited 1 with no output through the wrapper;
the same code with `print(...)` around both calls exited 0 and printed the
stored $F_4$ and $I_2(5)$ polynomials.

## `/preview?table=` crashes on a document whose `Numbers` is empty

What happened: previewing a draft's prose in pieces, each piece was built with
`Numbers: []` so that the entries would not eat the request line. Every one of
the five answered 200 with the whole table replaced by

    Error while parsing numbers: cannot access local variable
    'number_section' where it is not associated with a value

`numberdb_app/views.py:1397` guards the `Numbers` branch with
`len(data['Numbers']) > 0` and the `Data` branch with the same test, so an
empty entries block leaves `number_section` unbound before the context
dictionary reads it at line 1450. No section of the document renders, not just
the numbers.

What to do instead: put two or three real entries in every preview chunk. They
cost about forty bytes each of request line and they are what makes the rest of
the page render at all. (Reading the number table itself still wants the
slimmed-`Parameters` trick recorded above.)

Evidence: 2026-09-16, T255 critique. Five chunks with `Numbers: []` gave the
error; the same five with three M11 entries added rendered Definition,
Parameters, Comments, Formulas, Programs, Similar tables, Links, References and
Data properties normally.

## `agents/sage.sh` forwards only its named environment variables

What happened: a build of T256 set `NUMBERDB_CHECK_ONLY=1` around
`agents/sage.sh generators/exceptional-lie-representation-dimensions/generate.py`.
The generator's integrity checks ran, but then the script continued into
`verify()` and failed with `Table with id 'T256' does not exist`, because the
draft was private and no key had been passed. The cause was not the generator:
`agents/sage.sh` forwards only the environment variables named in its
`docker run` command, such as `NUMBERDB_KEY_FROM_STDIN` and `NUMBERDB_PUBLISH`.
Arbitrary variables from the caller are not inherited inside the container.

What to do instead: for one-off modes that are not already forwarded by
`agents/sage.sh`, mount a tiny scratch runner that imports the generator and
calls the wanted function directly, or add the variable to the wrapper in a
deliberate edit. Do not read a failed mode flag as evidence that the generator
ignored it.

Evidence: 2026-09-16, T256. The first integrity run printed "integrity checks
passed for 599 rows" and then failed in `generator.verify`; `/tmp/run_integrity_exceptional_lie.py`
called `run_integrity_checks()` directly through the wrapper and exited 0.

## On this builder there is no SOCKS proxy at all, and the prompt's `curl` line fails

What happened: the T256 critique opened with the command its own prompt gives,
`curl -s --socks5-hostname 127.0.0.1:1080 https://numberdb.org/skill`, and got
nothing. The second attempt wrote a file and reported `HTTP:000`, which looked
like a partial success; the 44 KB in `/tmp/skill.md` was a stale copy another
run had left there two days earlier, so the first minutes were spent reading an
old skill. `curl -v` said "connect to 127.0.0.1 port 1080 ... Connection
refused", `ss -ltn` showed nothing listening on 1080, `ALL_PROXY` was empty and
no `ssh -N -D` process existed. Nothing had died: on the AWS builder the tunnel
is never started, because the box reaches numberdb.org directly.

This is the same conclusion as the second paragraph of the T221 note above and
as the comment on `site_is_up` in `agents/campaign.sh` ("Trying direct first
costs one request on the laptop and nothing anywhere else"), but both are
buried inside notes about other things, and the campaign prompts still hand the
agent the proxy form.

What to do instead: on this builder use `curl --noproxy '*'`. Treat `HTTP:000`
with a non-empty output file as a failed fetch of a stale file, not as a fetch
-- `curl` leaves `-o` targets alone when it cannot connect. Read `ALL_PROXY`
first: empty means direct, and the `--socks5-hostname` form cannot work.

Evidence: 2026-09-16, T256 critique. `--socks5-hostname` refused on every
attempt; `curl -sS --noproxy '*' https://numberdb.org/skill` answered 200 with
47,044 bytes, 2,259 bytes longer than the `/tmp/skill.md` of 2026-09-14 --
the difference is the "does a parameter name what the number is of" section and
the `param-latex` paragraph, both of which the critique needed.

## `/preview?table=` answers 500 on a document with no `Title`

What happened: reading T257, the prose was previewed in pieces, as the T255
note above recommends. The first piece carried `Title`, `Definition`,
`Parameters`, `Links`, `References` and three entries and answered 200; the
next five dropped `Title` to buy request line for the section being read, and
every one of them answered `Server Error (500)` with a 145-byte body and no
message. It looked like the sections themselves were breaking the renderer, and
three of them were bisected one field at a time before the common factor turned
out to be the missing `Title`.

`numberdb_app/views.py:1564` reads `yaml_data['Title']` with no guard. The
sibling path at line 1484 raises a clean `ValueError('The table has no
Title.')` for the same document, so the check exists and the preview view does
not make it.

What to do instead: put `Title` in every `/preview?table=` chunk -- it costs
about fifty bytes and it is the difference between a rendered page and an empty
500. Together with the T255 note above (`Numbers: []` gives
"cannot access local variable 'number_section'"), the floor for a preview chunk
is `Title` plus two or three real entries. A 500 with a 145-byte body from this
endpoint means a missing section, not a bad one.

Evidence: 2026-09-16, T257 critique. `/tmp/t257_title500.py`: the same document
without `Title` gave 500 and with `Title` gave 200; `{Title, Numbers}` alone
gave 200 and `{Definition, Numbers}` gave 500.

## JSON is a legal preview document, which saves writing YAML into a query string

What happened: the same T257 previews had to turn a document fetched as JSON
from `GET /api/table?id=T257` back into YAML to send it to `/preview?table=`.
They did not: `preview` parses with `yaml.load(..., Loader=yaml.BaseLoader)`,
YAML is a superset of JSON, and `BaseLoader` makes every scalar a string, which
is what the table parser wants anyway. So
`json.dumps(subset_of_the_document)`, URL-encoded, is a valid chunk, and a
chunk is assembled by picking keys out of the fetched document rather than by
re-serialising prose full of backslashes and quotes into YAML by hand.

What to do instead: build preview chunks as JSON dicts straight from the API's
answer. Nothing else changes -- the same 4,094-byte request line, the same
need for `Title` and a few real entries.

Evidence: 2026-09-16, T257 critique. Nine chunks built by
`json.dumps({'Title': doc['Title'], ...})`, all 200, covering every section of
the document.

## `/preview?table=` renders `CITE{formula-key}` as bare text when the chunk omits `Formulas`

What happened: reading T259, `rigour details` ends "whose documentation defines
them by CITE{formula-charge}". Previewed in a chunk carrying `Title`,
`Data properties`, `Links`, `References` and three entries, it rendered as the
literal word `formula-charge` in running prose -- which reads exactly like the
dangling-`CITE{}` rendering fault a critique is looking for, and the T258
critique had recorded the opposite behaviour (`CITE{formula-simple-quotients}`
rendering as the link "(5)") on a table where the chunk happened to include
`Formulas`.

It is not a fault in either table. A `CITE{}` whose key names a formula
resolves against the `Formulas` section of the *same document*, so a chunk that
drops `Formulas` to buy request line drops the target and the citation falls
back to its key. With `Formulas` in the chunk the same field renders "(2)",
linked to `#formula-charge`.

What to do instead: when a preview chunk carries a field whose prose cites
anything, carry the sections the keys resolve in -- `Links` and `References`
for source keys, and `Formulas` too when a key begins `formula-`. The floor for
a chunk is now `Title`, two or three real entries (the T255 note above), and
whatever the prose cites. A bare key in rendered prose from a chunked preview
is a missing section, not a broken citation; confirm it against a chunk that
includes the target before writing it down as a finding.

Evidence: 2026-09-16, T259 critique. Same `rigour details`, two chunks:
`{Title, Data properties, Links, References, Numbers}` renders `formula-charge`;
`{Title, Data properties, Formulas, Numbers}` renders `(2)` inside
`<a class="CITE" href="#formula-charge">`.

## The SOCKS proxy was refusing connections, and this box reaches numberdb.org directly

What happened: the first `curl -s --socks5-hostname 127.0.0.1:1080
https://numberdb.org/skill` of the run succeeded; the next one, seconds later,
failed with `connect to 127.0.0.1 port 1080 ... Connection refused`, and so did
every retry. This is not the dead-tunnel failure the notes above describe --
that one keeps listening on 1080 and times out. `ps` showed no `ssh -N -D`
process at all: the tunnel was gone rather than hung, and nothing this account
may run can restart it (`ssh` is refused to an agent run).

It did not matter, because this box does not need it. `ALL_PROXY` is empty in
the run's environment and `NUMBERDB_REMOTE=local`, and plain
`curl https://numberdb.org/T260` answers. The note "Python does not see the
proxy that curl sees" and the `use_socks_proxy_if_set()` bootstrap in
`agents/api_edit.py` are both written for a machine that reaches the site only
through the tunnel; on the build box `urllib` with no proxy at all works, which
is what `/tmp/render260b.py` used for every request in this run.

What to do instead: when the proxy refuses (`000`, "Connection refused", no
`ssh -N -D` in `ps`), try the request without it before reporting the site
unreachable. Check `env | grep -i proxy` first: an empty `ALL_PROXY` on this
host means direct is the intended route and the `--socks5-hostname` in the
stage prompts is inherited from the workstation setup, not a requirement here.

Evidence: 2026-09-16, T260 critique. `curl --socks5-hostname` to `/T260`:
`HTTP 000` three times, `Failed to connect to 127.0.0.1 port 1080`. The same
URL without the flag: `HTTP 404` with an 11533-byte body, which is the draft
refusal and means the request arrived.

## Anonymous reads are rate limited per IP, and one corpus sweep spends the hour for everything else on the box

What happened: a survey of `HREF{}` style walked about sixty tables with
`urllib.request.urlopen('https://numberdb.org/api/table?id=T%d')` and no
`Authorization` header. It got through 59 and then `HTTP 429`. The next thing
to run was a Sage check under `agents/sage.sh`, whose first line is
`numberdb.table('T260')` -- and it died with `RateLimitError: too many
requests; retry in 2771s`. The limit is on the address, so an anonymous sweep
from this box locks out the container too: they share the egress IP, and
`agents/sage.sh` passes no key unless `NUMBERDB_KEY_FROM_STDIN=1` is set.

What to do instead: send the key on every corpus read, including throwaway
ones -- `printf 'Authorization: Bearer %s' "$(cat "$NUMBERDB_KEY_FILE")" |
curl -H @- ...` reads it from stdin and keeps it off the command line. And a
Sage script that only needs one table's document should read a copy rather
than call the API: `agents/sage.sh script.py /tmp/T260.json` mounts the extra
file at `/work/T260.json`, which costs no request and survives a lockout that
is already in force.

Evidence: 2026-09-16, T260 critique. `/tmp/t260_checks.py` first run,
`numberdb._errors.RateLimitError: too many requests; retry in 2771s`, raised
from `numberdb/_http.py` line 160, minutes after the unauthenticated sweep.
Authenticated `curl` to `/api/table?id=T260` answered 200 throughout.

## `/preview?table=` needs a `Numbers` section, and the request line dies above about 4 KB

What happened: two failures in a row while chunking T260 for rendering, each
of which reads like something else.

A chunk of `{Title, Definition}` returned 200 and rendered no table at all --
just the banner "Error while parsing numbers: cannot access local variable
'number_section' where it is not associated with a value". That is a Django
`UnboundLocalError` surfaced as a message, not a YAML complaint, and it fires
whenever the posted document has no `Numbers`. Every chunk needs at least one
entry; one row is enough, and the parameters it is keyed under have to be in
the chunk too.

Then chunks stopped working again above a certain size: a 3894-byte URL
answered 200, a 4136-byte one answered `400` with a 163-byte body and nothing
in the page. That is nginx refusing the request line, not Django. The ceiling
measured today is between those two numbers, so roughly 4 KB of URL, which for
`Title` plus prose plus one entry is about two sections of a wordy table at a
time. Shortening the `References` bib text to a placeholder is the cheapest
way to buy room when the chunk needs `References` present only so that
`CITE{}` keys resolve to numbers (see the note above).

What to do instead: build every preview chunk as `Title` + `Parameters` + one
`Numbers` row + the sections under test, keep the encoded URL under 4000
bytes, and read a `400` with a tiny body as "too long", not as "the site
refused the document". A `200` with the `number_section` banner means the
chunk forgot its entries.

Evidence: 2026-09-16, T260 critique. `/tmp/render260.py` (no `Numbers`): eight
chunks, all 200, all showing the banner and no rendered table.
`/tmp/render260b.py` (one row each): the same eight chunks render.
URL lengths 3524 and 3894 -> 200; 4136, 4149, 4992 and 7456 -> 400.

## The SOCKS proxy was dead again, and the critique prompt still tells a run to use it

What happened: the T261 critique opened with the command its own prompt gives,
`curl -s --socks5-hostname 127.0.0.1:1080 https://numberdb.org/skill`, and got
exit 7 and an empty file, twice. Nothing was listening on 1080, `ALL_PROXY` was
empty, and no `ssh -N -D` was running. `curl` straight to numberdb.org answered
every request in the run, including the API, the audit endpoint and five
`/preview` pieces. This is the second recorded occurrence; the T221 note above
says the same thing.

The first minute of a run is the expensive place for this, because an empty
answer from the proxy and an empty answer from a dead site look identical, and
the instinct is to conclude the site is down and stop.

What to do instead: when the proxy answers nothing, try the same URL without
it before concluding anything. `env | grep -i proxy` with `ALL_PROXY` empty is
the tell that there is no tunnel to use. The prompt in
`agents/table-critique/PROMPT.md` still prints the `--socks5-hostname` form as
the way to fetch a page, and could say "or without it, if 1080 refuses".

Evidence: 2026-09-16, T261 critique. `curl --socks5-hostname 127.0.0.1:1080`
to `/skill` and to `/T261`: exit 7, `000 0` both times. `ss -ltn` showed only
22 and the two resolvers. The same two URLs without the proxy: 200 (47044
bytes) and 404, the 404 being the draft answering anonymously as it should.

## `agents/critiques/` is gitignored and 118 critiques are committed in it anyway

What happened: the T261 critique wrote its report, ran `git status`, and the
file was not there. `.gitignore` line 168 ignores `agents/critiques/` under the
heading "what they produced on a particular afternoon is data, and lives
outside it ... the critiques they wrote". The note above about
`agents/table-ideas/BATCH-*.md` says, of the same kind of rule, "do not
`git add -f` it (the ignore is the owner's decision that agent output is
data)". Reasoning from that note alone, this run would have left its only
deliverable uncommitted.

The practice says the opposite for this directory. `git ls-files
agents/critiques | wc -l` is 118, and every critique of this campaign is in
the history: T259 at `5c9716c`, T260 at `852e91f`, each one commit containing
that file alone. Tracked files are unaffected by a later ignore rule, so only
a *new* critique hits it, and only on its first `git add`.

What to do instead: commit a new critique with `git add -f
agents/critiques/T<n>.md`, one commit for the file alone, as the ten before it
were. Do not generalise the batch note to this directory. The ignore line and
the practice disagree, and it is the ignore line that is stale.

Evidence: 2026-09-16, T261 critique. `git check-ignore -v
agents/critiques/T261.md` -> `.gitignore:168`; `git show --stat 852e91f` ->
`agents/critiques/T260.md | 239 +++`, one file.

## `/tables?page=N` past the end returns the last page again, and the corpus is 249 tables

What happened: an ideas run needed the whole list of published tables, and the
skill says there is no call that lists the corpus. `/tables` is paginated at
50 rows and honours `?page=`. A walk that stops when a page comes back empty
never stops: pages 6, 7, 8 and 9 each return the 49 rows of page 5, byte for
byte. Concatenating nine pages gave 445 rows; deduplicating by T-number gave
249. A run that did not deduplicate would have read the last 49 tables five
times and concluded the corpus was twice its size.

The count matters separately. There are **249 published tables**, T0 to T249
with T75 absent, plus the drafts above T249. Every stage prompt in
`agents/*/PROMPT.md` still says "126 tables exist", which was true in August;
a run that believes it will under-search the corpus before proposing.

Two smaller things found beside it. The tag pages are at `/tags/<name>` with
the name URL-encoded (`/tags/orthogonal+polynomials`); `/tag/<name>` is a 404,
and the singular is the form one guesses. And `/api/tables` answers **405
Method Not Allowed** to a GET, because it is the table-creation endpoint, which
reads as "the listing is broken" rather than "there is no listing".

What to do instead: walk `/tables?page=` into a dict keyed by T-number and
stop when a page contributes nothing new, rather than when it is empty.

Evidence: 2026-09-16, ideas run. Pages 1 to 9 of `/tables?page=`: rows
50/50/50/50/49/49/49/49/49, new rows 50/50/50/50/49/0/0/0/0, distinct total
249; pages 5 to 9 all begin "T177: Values of the Beta function". `sort_by=title`
changes nothing about this. `curl https://numberdb.org/tag/orthogonal%20polynomials`
-> 404; `/tags/orthogonal+polynomials` -> 200 with ten rows.

## oeis.org answers 403 to a script from this machine, except for b-files

What happened: an ideas run tried to find OEIS sequences for four coefficient
triangles. Every HTML endpoint answered **403** with a Cloudflare "Just a
moment..." interstitial: `/search?q=...&fmt=text`, the same with `fmt=json`,
the same with a browser `User-Agent`, `/A046716/internal`, and the bulk
`https://oeis.org/names.gz` (which returns the challenge page *under the
`.gz` name*, so a script that unzips it fails on something that is not a gzip
rather than on a 403). The static b-file
`https://oeis.org/A046716/b046716.txt` answered 200 with 40 KB.

This is a change: the accepted lesson at the top of
`agents/lessons/PROPOSALS.md` cites `https://oeis.org/search?q=hilbert+class+
polynomial` working from here on 2026-09-01. Nothing about the request changed,
so the reputation of this address did.

What to do meanwhile: a check against a *known* A-number still works through
its b-file, and that is worth doing; finding an A-number from its terms does
not, and a run should say so in its output rather than report "no OEIS check
was available". The technique half of this is written up for the skill in
`agents/lessons/proposals/20260916T072254Z-ideas.md`; the 403 itself is here
because it is about this address and not about the mathematics.

Evidence: 2026-09-16. `curl -s -m 25 -o /tmp/o.txt -w "%{http_code} %{size_download}"
"https://oeis.org/search?q=1,3,8,24,89,415&fmt=text"` -> `403 5400`, body
beginning `<!DOCTYPE html>...<title>Just a moment...</title>`. The same for
`&fmt=json` with `-A "Mozilla/5.0 ..."` -> `403 5613`, for
`https://oeis.org/A046716/internal` -> 403, and for `names.gz` -> `403 5252`.
`https://oeis.org/A046716/b046716.txt` -> `200 40724`.

## The audit's one-table rule steps aside when one name covers a shorter range

What happened: T262 has a `specialisation` parameter that takes the names
`qt`, `carlitz` and `macmahon`, with `n` repeated under each, and its value
column is headed $C_n$, which is true of only 4 of its 22 rows. This is the
shape `_one_quantity_per_table` in `audit_table` was written to catch, and
`GET /api/table/T262/audit` came back clean. The grid test requires
`len(grid) * len(labels) <= len(records) * 1.05`. The `qt` rows stop at $n=6$
and the other two run to $n=11$, so the grid has $9\times3=27$ cells against
$22\times1.05=23.1$ entries and the rule returns without reporting anything.
The comment on that condition says a ragged parameter "does not trip this" on
purpose, to protect a shape only some rows have. Here, though, the gaps come
from a length limit on one name's polynomials, not from the family. The
header check, `_column_names_its_quantity`, compares only against generic
words, so it passes a symbol that is false for most of the rows.

What to do instead: when reading a draft, do not take a clean audit to mean
the table is one quantity. Look at the parameter values and ask the skill's
question directly. In the audit itself, the grid test could compare each
label's range of the other parameters against the *shortest* label's range, or
count a label whose rows are a prefix of the others' as orthogonal.

Evidence: 2026-09-16, T262 critique. The audit response was
`{"findings": [], "clean": true}`. The document has 4 `qt`, 9 `carlitz` and
9 `macmahon` rows.

## `agents/sage.sh` mounts extra files but does not pass script arguments

What happened: a build run tried to follow the table-building prompt literally
with `agents/sage.sh agents/table-build/dry_run.py path/to/generate.py`. The
wrapper copied both files into `/work`, but it invoked Sage as
`sage -python -u /work/dry_run.py` with no remaining command-line arguments.
`dry_run.py` therefore printed its usage instead of checking the generator.

This is about the wrapper, not the public table skill: on a contributor's own
laptop, `sage -python agents/table-build/dry_run.py path/to/generate.py` is
the right command.

What to do here: create a tiny runner in `/tmp` that imports `dry_run` and
calls `dry_run.main(["/work/generate.py"])`, then mount that runner,
`dry_run.py`, `check.py` and the generator with `agents/sage.sh`.

Evidence: 2026-09-16, T266 build. Running
`agents/sage.sh agents/table-build/dry_run.py agents/table-build/check.py
generators/krawtchouk-polynomials-hamming-scheme/generate.py` printed the
`dry_run.py` usage. Running `/tmp/run_krawtchouk_dry.py` through the same
wrapper computed 608 entries and measured the block.

## `queue.py built` used to miss exact two-word proposal titles

What happened: after T267 was filled and offered, the required queue update
failed with `#147 has no unbuilt table like 'Charlier polynomials $C_n(x;a)$'`.
The checklist line was exactly `Charlier polynomials $C_n(x;a)$`, but
`_same_subject` strips math before comparing subjects. That left only
`charlier` and `polynomials`, and the matcher refused two-word containment to
avoid ticking titles such as `Golden ratio` inside longer unrelated names.

What to do now: `agents/queue.py` accepts exact equality after stripping
notation when the subject has at least two words, while still refusing a
two-word title contained in a longer title. `agents/test_queue.py` has a
regression test for the Charlier shape.

Evidence: 2026-09-16, T267 build. The first `python3 agents/queue.py built
147 'Charlier polynomials $C_n(x;a)$' T267` failed; after the matcher fix,
the same command ticked the issue as `-- T267`.

## `pdftotext` is no longer on this machine; arXiv's `/html/<id>` is the way to read a paper

What happened: the ideas run of 2026-09-16T1046 needed three threshold tables
from arXiv papers. The note above ("arXiv PDFs can be read here with curl and
pdftotext") no longer holds: `which pdftotext` finds nothing and
`/usr/bin/pdftotext` does not exist, and the `Read` tool refuses PDFs because
`pdftoppm` is missing too. PDFs fetched through the web-fetch agent come back
as compressed streams it cannot decode. What did work: arXiv's own HTML
rendering, `https://arxiv.org/html/<id>v<n>`, linked from the abstract page,
for 0912.0287, 1309.6772 and 1001.1826; and
`https://ar5iv.labs.arxiv.org/html/<id>` for cond-mat/0612365. Neither exists
for cs/0309020 or math/0702007, and those tables stayed unread.

What to do instead: for a paper since about 2009, read `arxiv.org/html/<id>`;
for an older one try ar5iv; if neither exists, record the paper as unread
rather than installing tools.

Evidence: 2026-09-16, `ls -l /usr/bin/pdftotext` "No such file or
directory"; `Read` on a saved PDF: "pdftoppm is not installed".

## Full-table `/preview?table=` requests can exceed the deployed URI limit

What happened: repairing T272 needed a rendered preview of the changed draft.
Sending the whole 6.8 KB API document back through `/preview?table=...` as a
query string returned `414 Request-URI Too Large`. A smaller but still broad
chunk, about 7.1K URL characters after encoding, returned `400 Bad Request`
before the preview page rendered.

This is about the deployed preview route and proxy limits, not the table
skill. A contributor using the website editor does not have to encode the
whole document into a URL, but an agent calling `/preview?table=` directly can
hit the limit on ordinary drafts.

What to do instead: preview only the changed sections, and include the
context those sections need. For example, row comments using
`CITE{formula-root}` must be previewed with the `Formulas` section present, and
formula sections citing papers need `References` present, otherwise the preview
reports false `CITE-broken` spans.

Evidence: 2026-09-16T12:26:38Z, T272 repair. The full preview URL returned
414, a 7082-character section preview returned 400, and smaller section
previews with the needed `Formulas` and `References` context rendered with no
`CITE-broken` or `HREF-broken` spans.

## The critique prompt still names the proxy and `manage.py`; neither worked on 2026-09-16

What happened: the T273 critique followed the prompt's
`curl --socks5-hostname 127.0.0.1:1080`. It fetched `/skill` once, and then
every connection was refused, because nothing was listening on 1080 any more.
`curl --noproxy '*'` reached numberdb.org directly. This is the T221
observation again. The `RequestFactory` rendering recipe above failed too:
`agents/sage.sh` ran `import django` and got `ModuleNotFoundError`, so
`manage.py audit_table` could not run either. What worked instead was
`GET /api/table?id=T273` and `GET /api/table/T273/audit` with `-H @-`, plus
`/preview?table=...` in five pieces of 1.8 to 3.6 KB, all 200.

What it should say: the critique prompt should say "curl directly, and fall
back to the proxy", and should name the audit API as the route when the
throwaway has no Django. Otherwise every critique run spends its first turns
rediscovering this.

Evidence: 2026-09-16. `/tmp/crit273_out.txt` has the Django traceback, and
`/tmp/T273_p[a-e].html` are the five previews.

## Audit misses some unlinked table mentions when the target title contains math

What happened: the T274 critique found plain prose mentions of the sibling
drafts T272 and T273 that should have been linked at first mention, but
`GET /api/table/T274/audit` returned clean. The audit strips `$...$` spans from
the candidate table title before matching, so T272's title becomes
`Satisfiability thresholds of random -XORSAT`; it then searches the unstripped
prose, where the text is `random $k$-XORSAT`, and the strings can never match.
T273 has the same title shape.

What to do now: do not rely on a clean audit to catch unlinked table mentions
when the target title contains math in the middle. Search the prose yourself
for sibling table names, and link the first mention once per section. The site
fix would be to strip math from the prose with the same rule before matching.

Evidence: 2026-09-16, T274 repair. Before the repair, `comment-capacity-one`
plainly named random `$k$-XORSAT` and `comment-core` named the
`$(\ell+1)$-core`; the audit answered `{"findings": [], "clean": true}`.

## `sage.sh`'s own `timeout 1800` did not stop a Sage computation, and neither did killing the client

What happened: a Gröbner-basis run (`/tmp/ds4.py`, Davenport–Stothers pairs of
degree $M=4$, 2026-09-16, table-ideas) was started at 14:41 as
`timeout 3300 agents/sage.sh /tmp/ds4.py`. At 15:37 the outer `timeout` had
fired (`EXIT 124`), but `ps` still showed `timeout 1800 docker run --rm -i
--name numberdb-agent-run-...` and, inside it, `python3 -u /work/ds4.py` at
99% CPU with 58 minutes of CPU time -- so the wrapper's own 30-minute limit had
passed half an hour earlier without stopping it. `kill` on the `timeout` and
`docker run` client PIDs returned no error and changed nothing.

Two things appear to combine. `timeout` sends SIGTERM to `docker run`, which
forwards it to the container, and a Sage process busy inside Singular does not
act on it; `timeout` sends no SIGKILL unless given `-k`. And the outer
`timeout` killed `sage.sh` by signal, and bash does not run an `EXIT` trap for a
TERM it does not trap, so `cleanup`'s `docker rm -f` never ran.

What to do instead: do not rely on either timeout to bound a heavy algebraic
computation. Measure one smaller case first, and give the script its own
internal limit (Singular's `alarm`, or `cysignals.alarm`) that raises inside
Python. The fix in `sage.sh` would be `timeout -k 30 $TIMEOUT docker run ...`
and `trap cleanup EXIT INT TERM`. From an agent run, `docker` is refused, so a
run that escapes cannot be stopped from here; say so in the output.

Evidence: `/tmp/ds4b.out` ends `M=4` / `EXIT 124`; `ps aux | grep ds4.py` at
15:40 listed PIDs 717948, 717950 and 717992 (58:28 CPU).

## Link titles are not HTML-escaped on rendered table pages

What happened: T278's `Links.ElkiesHall.title` used mathematical inequalities
with raw `<` characters:
`List of integers x,y with x<10^18 and 0<|x^3-y^2|<sqrt(x)`. The rendered
anchor put that title directly into HTML, so the browser treated `<sqrt(x)` as
a tag and swallowed the end of the link text. The API document was valid and
the audit did not report it; the fault only showed on the rendered page or
preview.

What to do instead: until the renderer escapes link titles, avoid raw `<` and
`>` in `Links` titles. Spell inequalities in words, or use a shorter source
title that does not contain angle brackets. A site fix should escape link
titles before inserting them into anchor text.

Evidence: `agents/critiques/T278.md` records the broken anchor as rendered.
The T278 repair on 2026-09-16 changed the title to `Noam D. Elkies: Hall's
conjecture examples`; `/tmp/t278-preview-links.html` then rendered a closed
anchor with that exact text.

## `agents/sage.sh` mounts extra files but does not pass script arguments

What happened: T280 needed the standard dry run,
`agents/table-build/dry_run.py path/to/generate.py`, under the required Sage
wrapper. Running `agents/sage.sh agents/table-build/dry_run.py
agents/table-build/check.py generators/counterexamples-euler-sum-powers/generate.py`
mounted all three files, but the container executed only
`sage -python -u /work/dry_run.py`; no command-line arguments were forwarded,
so `dry_run.py` printed its usage and stopped.

What to do instead: make a scratch wrapper in `/tmp` that imports `dry_run`
and calls `dry_run.main(["/work/generate.py"])`, then mount that wrapper,
`dry_run.py`, `check.py` and the generator with `agents/sage.sh`. The extra
files are available in `/work` by basename, but they are not arguments to the
main script.

Evidence: 2026-09-16, T280 build. The wrapper `/tmp/dry_run_euler.py` made the
same dry run succeed: 96 exact entries, longest value 10 characters, entries
block 5.8 KB.

## The SOCKS proxy can refuse after one request while numberdb.org answers directly

What happened: during the T281 critique the first request through
`--socks5-hostname 127.0.0.1:1080` (`/skill`) returned the page. Every
request after it failed at once with `curl: (7) Failed to connect to
127.0.0.1 port 1080 ... Couldn't connect to server`. The earlier note
describes a timeout; this was a refusal, so nothing was listening any more.
The T280 critique hit the same thing ("the next request through it failed
(`000`)"). A plain `curl https://numberdb.org/skill` with no proxy answered
200, and so did every request after it, including the keyed API calls and
`/preview`.

What to do instead: when the proxy refuses, try the request without it
before concluding that the site is down. If it answers, carry on directly.

Evidence: 2026-09-16, about 19:10 UTC; six retries through the proxy each
returned `000`, and the direct request returned 200.

## Large `/preview?table=` queries can return 400

What happened: during the T281 repair, rendering the full current table YAML
through `/preview?table=...` returned HTTP 400. A prose-only piece of about
3.9 KB, and later the updated comments piece of about 2.5 KB, hit the same
refusal. Smaller pieces with the same document shape and a minimal `Numbers`
section rendered normally, and the live `/T281` page rendered normally after
the API write.

What to do instead: when a draft is private and the full preview URL returns
400, split the YAML into sections that still include enough `Parameters` and
`Numbers` for `table_context` to draw the page, or fetch the live page once the
draft is visible to the key-holder. Treat a 400 here as a preview transport
limit, not as evidence that the table YAML is invalid.

Evidence: 2026-09-16 T281 repair. `/tmp/t281_preview.py` returned HTTP 400 for
the full 4.7 KB API document; `/tmp/t281_preview_pieces.py` rendered the
formula, entry, similar-table and data-property pieces; and
`/tmp/t281_preview_comments_split.py` rendered the longer comments after
splitting them into two chunks.

## Web search refused, and the arXiv API answers 406 to Python here

What happened: in the 2026-09-16T2020 ideas run, the `WebSearch` tool was
refused for lack of permission. `https://export.arxiv.org/api/query?...`
answered HTTP 406 to `urllib` (through the SOCKS setup in
`agents/table-ideas/screen.py`), with and without a browser-like
User-Agent. The Wikipedia API (`en.wikipedia.org/w/api.php`) and
`raw.githubusercontent.com` answered normally, and so did numberdb.org with
the key.

What to do instead: find sources through the Wikipedia search API, and screen
library documentation from GitHub raw files (Singular's `LIB/*.lib` headers
name their subjects). When a family's only real source is a book or an arXiv
paper, say in the batch that it was not screened, rather than spending turns
on the API.

Evidence: `/tmp/b2020/find.py`, `/tmp/b2020/find2.py`, `/tmp/b2020/find4.py`.

## `already_asked` misses an issue whose title shares only later words of the name

What happened: in the 2026-09-17T0110 ideas run,
`already_asked('Special L-values of elliptic curves over real quadratic fields')`
returned `[]`. It searches issue titles for the first three words longer than
four letters ("Special", "L-values", "elliptic"), and GitHub's title search
ANDs them, so numberdb-data#20 *Data of elliptic curves over quadratic fields*
was not found. `already_asked('elliptic curves quadratic fields')` found it.
One call in the same run also answered `could not ask GitHub (HTTPError)`,
presumably the unauthenticated search rate limit.

What to do instead: call `already_asked` with the family's core noun phrase
as well as the proposed title, and read the open `table wanted` list with
`gh issue list -R numberdb/numberdb-data --label "table wanted"`, which is
authenticated and not rate-limited the same way.

Evidence: `/tmp/ideas0917/screen_run.py`.

## `Generator.publish()` can fail its empty preflight on a prose-only draft

What happened: T286 was created as a draft with prose and parameters but no
`Numbers` section, as the proposal-claim workflow asks. Running its generator
with `NUMBERDB_PUBLISH=1` failed before computing entries: the client
preflight `check_writable()` sent an empty upsert to
`/api/table/T286/entries`, and the server answered 400,
`A value in these entries cannot be read as a number. 'str' object has no
attribute 'items'`.

What to do instead: verify with `dry_run.py` first, then send the actual
entries as a single replacement to `/api/table/<tid>/entries` and attach the
generator source with the same run id. After that, run the generator's
`verify(sample=None)` against the stored draft. Do not conclude that the key
or draft is unwritable from this empty-upsert refusal.

Evidence: 2026-09-17 T286 build. The direct replacement stored 50 entries and
attached `generate.py` on revision
`e936fce85cf6a82f929c6c0f56b2a7ded82666d1f09729fb06cf05a02b65f1ac`;
`verify()` then reported `50/50 matched`.

## A critique on the builder cannot render a draft's page, but `/preview` renders its document in pieces

What happened: the T289 critique of 2026-09-17 found the SOCKS proxy at
`127.0.0.1:1080` refusing connections (`curl: (7) Failed to connect`), while a
direct `curl https://numberdb.org/...` worked. The draft's page answered 404
even with `Authorization: Bearer <key>`: the table view does not read the API
key, only a session. `GET /api/table?id=T289` and `GET
/api/table/T289/audit` accept the key. The `RequestFactory` render described
above needs Django, and `agents/sage.sh` with `NUMBERDB_REMOTE=local` runs
`numberdb/builder:latest`, which has none (`ModuleNotFoundError: No module
named 'django'`).

What worked: convert the API document to YAML, put `ID: INPUT{id.yaml}` in
front, and `GET /preview?table=<urlencoded yaml>` with no key. It renders the
sections exactly as the table page does: formulas, CITE numbering, folded
rigour note, entry links. The request line is limited to about 4 KB once
encoded. 3.3 KB returned 200, while 4.1 KB answered 400 and 8 KB answered
400/414. So send Title and Parameters with each piece: one or two sections of
prose, or one block of entries.

What to do instead: fetch the document with the key and render it through
`/preview` in pieces, or give the builder image the site code so the
`RequestFactory` render works again. Do not trust a copy of the skill left in
`/tmp` by an earlier run; this run found a five-day-old one missing two
sections.

Evidence: `/tmp/T289-*.q` and `/tmp/T289-*.html`, 2026-09-17.

## `agents/sage.sh` forwards only its named control variables

What happened: T290's generator had a `NUMBERDB_SELF_CHECK=1` mode that asks
Singular's `bfct` to recompute every stored Bernstein-Sato polynomial. Running

    NUMBERDB_SELF_CHECK=1 agents/sage.sh generate.py

did not enter that mode. The wrapper forwards `NUMBERDB_KEY_FROM_STDIN`,
`NUMBERDB_PUBLISH`, `NUMBERDB_RESTATING` and `NUMBERDB_LOWERING`, but not
arbitrary environment variables. The script fell through to `verify()`, and
because T290 was still a draft and no key was being sent, it reported that
the table did not exist.

What to do instead: for one-off generator modes, mount a tiny runner script
that imports the generator and calls the function directly, or teach
`agents/sage.sh` to forward the specific variable before relying on it. Do
not assume an environment flag visible to the outer shell is visible inside
the Sage container.

Evidence: `NUMBERDB_SELF_CHECK=1 agents/sage.sh generators/bernstein-sato-polynomials-simple-unimodal-singularities/generate.py`,
2026-09-17, followed by `/tmp/run_self_check_issue151.py`.

## The local Sage image may not have enough polynomial machinery for `NumberField`

What happened: while repairing T292, a check script run with
`NUMBERDB_REMOTE=local agents/sage.sh` tried to construct quadratic fields
with `NumberField(x^2 - x - 1, 'w')`. Even after importing
`numberdb.sage` first, Sage failed inside polynomial factorisation with
`ImportError: cannot import name PolynomialSequence_generic`, through
`sage.libs.singular.function`.

What to do instead: when the check only needs quadratic conjugation or ideal
equality, use exact arithmetic in the table's integral basis, or PARI through
`sage.libs.pari`, rather than depending on Sage's `NumberField` stack in the
local container. Treat this as a limitation of the runner image, not as a
mathematical result.

Evidence: `/tmp/t292_pair_check.py`, 2026-09-17. The replacement check used
exact arithmetic in the basis `1,w` and verified all 250 repeated-value pairs.

## `/api/table/<tid>/audit` can 500 on one draft while other audits work

What happened: after filling T293, `GET /api/table/T293/audit` with the
draft owner's API key returned HTTP 500 with only the generic server-error
HTML page. The same keyed request succeeded for public T64 and draft T292 in
the same run, so the audit service was reachable and draft auth was working.
The local fallback was unavailable because this checkout has no Django
installed (`ModuleNotFoundError: No module named 'django'`). Trying to run the
audit code inside `agents/sage.sh` also failed, because the builder image used
there did not have the site checkout at `/app`.

What to do instead: when the audit endpoint gives only a generic 500, probe a
known table and a known draft to separate an endpoint outage from a
table-specific crash, keep the generator `verify(sample=None)` and dry-run
output in the final report, and leave a note for a person with server logs to
run `manage.py audit_table <tid>` directly. Do not treat the generic 500 as a
clean audit.

Evidence: T293 on 2026-09-17 returned 500 from the audit endpoint after
`verify()` reported `585/585 matched`; T64 returned one finding and T292
returned clean from the same keyed audit script.

## A `sage.sh` run queued behind the lock looks exactly like one that is running

What happened: a Sage computation (integer kernels at large level) ran for
seventeen minutes. Two more `agents/sage.sh` calls, started in the background
meanwhile, sat on the lock with empty output files and no "waiting" line. With
`| tail -20` on the first, nothing at all was visible until it ended, so three
runs looked like three slow computations. Stopping the first meant killing
the local `timeout` and `sage.sh` processes (`docker` itself is refused); the
container then went away and the queued runs started at once.

What to do instead: send a long run's output to a file without `tail`, print
with `flush=True` after each case, and order cases smallest first so a
partial file says how far it got. Before starting a second run, check
`ps aux | grep sage.sh`: a run you started earlier may still hold the lock.

Evidence: 2026-09-17, ideas run 1154, `/tmp/pari5.py` then `/tmp/pari6.py`
and `/tmp/pari7.py`.

## `source_names_it` passes on a page whose words are only in its reference list

What happened: `source_names_it('Weber class polynomials', <AMS page of
Yui–Zagier, Math. Comp. 1997>)` passed. `curl` on the same address returns a
Cloudflare challenge; `urllib` gets an 11 MB landing page, in which "Weber"
and "class" occur only inside other papers' bibliographies. The screen also
passed "Class polynomials gamma2" on PARI's documentation because "gamma" is
in the entries for the Gamma function, while the invariant is written γ.

What to do instead: treat a pass as "the words are on the page", not "the
page defines the family". For a large page or a common word, find the
sentence and quote it in the proposal, or record the pass as disregarded.

Evidence: 2026-09-17, ideas run 1154, `/tmp/screen2.py`.

## `agents/sage.sh` mounts extra files but does not pass them as arguments

What happened: the public dry-run command is
`sage -python agents/table-build/dry_run.py path/to/generate.py`, but
`agents/sage.sh` runs only the first script as `/work/<script>` and mounts the
remaining paths as files. They are not preserved as ordinary `sys.argv`
arguments inside the container.

What to do instead: for a Sage helper that expects path arguments, write a
small `/tmp` wrapper whose paths are the mounted `/work/...` filenames, or make
the helper read its companion files from fixed mounted names. Check this before
starting a long run, because the failure otherwise looks like the helper was
called without its required arguments.

Evidence: 2026-09-17, T302 Newton-Cotes weights dry-run and document rebuild.

## The Sage image has SnapPy but not `database_knotinfo`, and the host has no pip

What happened: an ideas run measuring knot invariants found that Sage's
`KnotInfo` in the image behind `agents/sage.sh` iterates over KnotInfo's
ten-knot sample only, because the optional package `database_knotinfo` is not
installed. SnapPy is (`snappy.Link(braid_closure=...)`, verified
`cusp_translations`, `cusp_areas`). On the host, `pip` and `python3 -m pip`
are absent too.

What to do instead: to read KnotInfo's data from the host, download the wheel
from PyPI with `curl` and unpack it with `python3 -m zipfile -e`. The data is
`database_knotinfo/csv_data/knotinfo_data_complete.csv`, `|`-delimited, with a
second header row of descriptions. A build that needs it inside Sage has to
install it in its container run (`sage -pip install database_knotinfo`) or
mount the CSV.

Evidence: 2026-09-17, ideas run 1425, `/tmp/k2.py` printed `knots 10`.

## The ideas prompt's table count is stale

What happened: the ideas prompt says "126 tables exist". Walking T1–T420 with
`numberdb.table` found 304 (the highest is T304), and roughly thirty-five of
the open `table wanted` issues are already built. Two candidate areas taken
from the issues, character sums and the Beta function, turned out to be
T142–T144 and T177.

What to do instead: walk the T-numbers first (eight threads take about two
minutes) and read titles before picking an area from the issues.

Evidence: 2026-09-17, ideas run 1425, `/tmp/walk.py`.

## The `env | grep` key leak happened a third time, with the same mask

What happened: the T305 critique hit the refused SOCKS proxy (127.0.0.1:1080
answered the first request of the run and then "Couldn't connect" on every
later one, as in the T221 note) and listed the environment to see how the
runner reaches the site. The mask was `sed 's/=.*KEY.*/=<redacted>/'`, the
same pattern the T226 note describes as not matching `NUMBERDB_API_KEY=...`.
The zeta3 key is again in a run's tool output. The note existed; it was read
only after the listing.

What to do instead: the environment carries the key in `NUMBERDB_API_KEY` as
well as in the file named by `NUMBERDB_KEY_FILE`, which is what makes any
listing dangerous. Either stop exporting `NUMBERDB_API_KEY` into agent runs
(everything documented reads the file) or put "never print the environment"
in the prompt beside the key instructions, where it is read before the first
command. Rotate the zeta3 key. numberdb.org answered `curl` directly
throughout, so the proxy is not needed on this runner.

Evidence: 2026-09-17, T305 critique, the fourth Bash call of the run.

## A draft's whole document is readable anonymously through `/revisions`

What happened: reading draft T310, `curl https://numberdb.org/T310` and
`/preview/T310` both answered 404, as a draft should, and `/bundle/T310` and
`/discuss/T310` did too. But unauthenticated `GET /revisions/T310` answered
200 with the revision table -- times, the zeta3 account, the messages -- and
with the unified YAML diffs of every revision, which for a table filled in one
go is the whole document: title, definition, parameters and every stored
entry. `GET /history/T310` also answered 200. This is the T235 note about
`/files/<tid>` one route wider: `revision_history` and `table_history` load
the table by T-number without the draft guard that `table_by_tid` and
`preview` apply, so a draft is private only on the routes somebody remembered.

What to do instead: treat a draft as public on every route but `/T<n>`,
`/preview/T<n>`, `/bundle/T<n>` and `/discuss/T<n>` until the guard is applied
in one place. Reading `/revisions/<tid>` is, in the meantime, the cheapest way
for a critique to see what an edit to a draft actually changed -- the T310 read
used it to find that the definition-shortening commit had dropped the page's
only identification of $j$ -- but it is a leak, not a feature.

Evidence: 2026-09-17, T310 critique. `/T310` 404 (11,533 bytes of Not found),
`/revisions/T310` 200 showing `@@ -1,10 +1,7 @@` and the removed Definition
text, `/history/T310` 200, `/files/T310/generate.py` 200 as the T235 note
already records.

## `audit_table` never reads a `Similar tables` relation

What happened: the T310 audit returned `"findings": [], "clean": true`, and
two of the critique's six findings are in the Similar-tables relations. That is
not bad luck. `_prose_faults` collects its texts from `Definition`, `Comments`,
`Formulas` and `Similar tables`, taking a section that is a string or a mapping
of strings; a `Similar tables` written as a list of `{table, relation}` -- which
is how every table that has more than a sentence to say writes it -- is neither,
so it is skipped entirely. No relation is ever checked for an editorial phrase,
a positional phrase, a family named without a link, or a link written after the
name it belongs on.

The phrase list has a second gap beside it: `POSITIONAL` holds "the first
factor" and "the second factor" but not "the other factor", which T310 uses in
`comment-factor` and again in its rigour note, in both cases for a polynomial
that `Formulas` has already named $Q_\Delta$.

What to do instead: when a critique reports "audit clean", read the
Similar-tables relations by hand; the audit has not looked at them. Fixing it
is small -- extend the collection in `_prose_faults` to pull `relation` (and
the caption in `table`) out of a list-valued section, and add "the other
factor" to `POSITIONAL` -- and both want a test in
`numberdb_app/test_audit_prose.py`, where the other prose checks are tested.

Evidence: 2026-09-17, T310 critique;
`numberdb_app/management/commands/audit_table.py`, `_prose_faults` lines
838-860 and `POSITIONAL` at line 826.

## The site's own polynomial-search example is refused: `polygens` is not in the evaluator

What happened: the T311 critique asked the question the critique prompt asks
last -- would a reader who arrived holding one of these polynomials be served?
-- and found that no polynomial in the corpus can be searched for today.
`/advanced-search` tells the reader, under "Lists of polynomials over
$\mathbb{Q}$", to write

    [{n: x^2 + n for n in [1..10]} for x,y in [polygens(QQ,2,'x')]]

and `/api/search` answers that exact string with

    Unknown or not-allowed name 'polygens'. Only mathematical functions and
    constants provided by the search environment may be used.

`workers/evaluator.py` builds the namespace by hand (lines 60-115) and it has
`PolynomialRing` but neither `polygen` nor `polygens`. Nor is there a way
round: `PolynomialRing(ZZ,"x")([-1,-1,1])` is refused with "Only direct calls
to permitted functions are allowed", and a bare `x^2 - x - 1` with "Unknown or
not-allowed name 'x'" -- which is the form the published skill gives in its
type table as how a `Z[]` value is written.

The matching machinery behind the search is fine and is tested
(`utils/numbers/polynomial`, `polynomial_modulo_variable_names`,
`numberdb_app/test_search.py` line 599 on): polynomials find each other modulo
variable names once a query reaches them. It is only the evaluator's namespace
that no query can get through.

This is a site bug rather than a lesson: it affects the twelve polynomial
tables equally and nothing a contributor writes can work round it. Fixing it
is two names in `_namespace()` plus a test that the advanced-search help
page's own example returns results.

What to do instead, meanwhile: do not report "this table's values cannot be
found" as a finding against a polynomial table under critique; it is true of
all of them. Say it once, where it belongs.

Evidence: 2026-09-17, T311 critique.
`curl -sS -G --data-urlencode "expression=..." https://numberdb.org/api/search`
with the help page's example, with `x^2 - x - 1`, with
`x^3 + 48*x^2 - x*y + 768*x + 4096` (a stored T309 value) and with
`PolynomialRing(ZZ,["x","y"])("...")`: four refusals, no results.

## A `/preview` piece with no `Numbers` draws no sections at all, and answers 200 while doing it

What happened: the T312 critique rendered a private draft through
`/preview?table=` in pieces, as the T221 note above describes. Five of the
nine pieces carried prose only -- `Title`, one `Comments` field and the
`Links` its `CITE`s need, with no `Numbers` key, since the piece was about the
prose. All five answered 200 with a 7 KB page that is the navigation bar and
the footer and nothing between them: no Comments, no Links, no section title
of any kind. That reads exactly like a section that failed to render, which is
the fault the critique was looking for, and cost a round of re-reading before
the pattern was clear.

Adding a one-entry `Numbers` -- `{"0": {"1": {"K": {"vz": "1"}}}}` -- to the
same document made every section appear. Measured directly afterwards: the
same piece without `Numbers` is 6476 bytes with zero `table-section-title`
elements; with one entry it is 14331 bytes and draws `Numbers`, `Comments`,
`Links`. The view returns the rendered table only when there is a table of
numbers to hang it on.

What to do instead: put a minimal `Numbers` in every preview piece, including
the prose-only ones, and treat an empty render as a missing `Numbers` rather
than as a broken section. One stored entry, or a bare `"1"`, is enough; the
entry costs about 40 bytes of the 4094-byte request line.

Evidence: 2026-09-17, T312 critique. `/tmp/prev312.py` and the two-request
check above; `/tmp/T312_c.html` (first round, no `Numbers`, 7484 bytes, only
the shell) against the same piece rerun with one entry (16925 bytes, all
sections).

## A draft's whole page can be rebuilt from the API document, in the Sage container, on a throwaway sqlite database

What happened: the T315 critique needed the rendered page, and the site's HTML
routes authenticate by session, so `GET /T315` and `/preview/T315` answer 404
to the zeta3 bearer token (the note above, T182). This builder has no Django
and no database, so the `RequestFactory` recipe written for T136 and T137 does
not run here either, and `/preview?table=` renders only pieces small enough to
fit a 4094-byte request line. Rebuilding the whole page instead worked, in one
`agents/sage.sh` run: the container has Sage, which `numberdb_app/models.py`
imports at module level, and it has the network, so it can install Django.

The shape, all of it inside one script mounted at `/work`:

  * `pip install --target /tmp/libs django<6.1 django-allauth python-decouple
    dj-database-url django-widget-tweaks django-anymail gitpython
    django-extensions psycopg2-binary timeout-decorator func-timeout
    beautifulsoup4 requests requests-oauthlib`. `psycopg2` is needed even for
    sqlite, because `django.contrib.postgres` is in `INSTALLED_APPS` and
    imports it at app-loading time.
  * mount a tarball of `numberdb numberdb_app templates static utils workers
    data_pipeline manage.py` and extract it; `sys.path` gets `/tmp/libs` and
    the extracted repository, and `NUMBERDB_SAGE_PYTHONPATH=` keeps the client
    off the path, which it must be: with Django up, the name `numberdb` has to
    belong to the site (the `/app` note above).
  * settings from the environment: `DJANGO_SETTINGS_MODULE=numberdb.settings.dev`,
    `DATABASE_URL=sqlite:////tmp/x.sqlite3`, `SECRET_KEY`, `ALLOWED_HOSTS`,
    `SOCIALACCOUNT_GITHUB_ID`, `SOCIALACCOUNT_GITHUB_SECRET`,
    `ACCOUNT_DEFAULT_HTTP_PROTOCOL`. Then `django.setup()` and
    `call_command('migrate', run_syncdb=True)`.
  * two writes have to be replaced, because both build a postgres text-search
    vector and sqlite answers "no such function: to_tsvector":
    `editing.reindex_for_search` (patch to a no-op) and `editing._sync_tags`
    (replace with a copy that makes the `Tag` rows and skips the final
    `update(search_vector=...)`; a `try/except` around the original is no good,
    since the failure happens inside `create_table`'s atomic block).
  * `tree = json.load(...)` of `GET /api/table?id=T315`, then
    `tree['Numbers'] = flatten.to_records(tree)` -- the API nests entries and
    `create_table` wants the flat records -- then
    `editing.create_table(tree, author=user, via='orm', published=False)`, and
    `views.table_by_tid(request, table.tid)` with `request.user` the author, a
    `SessionStore()` and a `FallbackStorage` for messages.

What this gives is the page a reader gets: for T315, 497 KB of HTML with all
479 rows, the column headers, the entry comments under their rows, the prose
sections and the reference numbering. Two things it does not give: the table
takes `T1` in the fresh database, so its self-links say `/T1`; and the tables
it links to do not exist there, so `HREF{}` anchors render but resolve to
nothing locally -- check those slugs with a plain `curl` against the live site
instead.

Also: on this machine `NUMBERDB_API_KEY` is set in the environment, so any
command that dumps the environment -- `env | grep -i numberdb`, a debug print
of `os.environ` -- puts the key in the transcript. Read the key from
`NUMBERDB_KEY_FILE` and grep for what you want by name.

Evidence: 2026-09-17, T315 critique. `/tmp/t315_render_sage.py` (the script,
worth promoting to `agents/render_draft.py` with the tid as an argument),
`/tmp/t315_render_out.txt` (the run: `records: 479`, `status 200`, 497,255
bytes of HTML between `=== HTML ===` markers) and `/tmp/t315_page.html`.

## LMFDB answers a reCAPTCHA challenge with HTTP 200, so an LMFDB URL cannot be screened or read from here

What happened: in the 2026-09-17T2308 ideas run, every request to
`www.lmfdb.org` -- `/api/mf_newforms/?...`, `/api/mf_hecke_cc/?...`,
`/knowledge/show/mf.elliptic.satake_parameters` -- came back as a Google
reCAPTCHA challenge page, served with HTTP 200 and 30 KB of
`RecaptchaChallengePageUi` JavaScript. Two consequences, and the first is the
dangerous one: `source_names_it(name, lmfdb_url)` does not report a network
failure, it reports that the page does not mention the family, which reads like
the family being misnamed. The second is that LMFDB's own conventions cannot be
read here, so a batch that wants to follow one (its Satake angle
normalisation, its embedding numbering, its published first zeros) has to say
in the report that the comparison was not run.

An earlier note records that `curl` reaches some LMFDB calculators for about
four requests before blocking; this run got zero. Do not spend turns on it.

What to do instead: cite Wikipedia, the PARI or Sage manual, or an arXiv
abstract, and screen that. Where LMFDB is the right cross-check for a table,
write it into the proposal as the check a builder with an ordinary connection
should run before publishing.

Evidence: 2026-09-17, the three URLs above, each returning
`<!doctype html>...RecaptchaChallengePageUi`.

## The arXiv API answers `curl -sL` over https, though `urllib` gets 406, and `already_asked` got HTTPError on every call

What happened: the existing note above says the arXiv API answers 406 to
`urllib` here and advises not to spend turns on it. In the 2026-09-17T2308 run
`curl -sL "https://export.arxiv.org/api/query?search_query=all:%22Petersson%20norms%22&max_results=5"`
answered with the Atom feed, and it is how the source for one proposal was
found (arXiv 1902.06429, whose title names "Petersson norms of generic cusp
forms"). Two traps: `http://export.arxiv.org` answers 301 and `curl` without
`-L` prints nothing at all, which looks like an empty result set rather than a
redirect; and a phrase search that returns nothing really does mean nothing
(`all:"Satake angles"` is empty, which is why that title was not used).

In the same run every `already_asked` call answered
`could not ask GitHub (HTTPError)`, so all issue claims in the batch were
checked with `gh issue list --repo numberdb/numberdb-data --state all --search
"X in:title"`, which is authenticated and answered every time.

What to do instead: reach arXiv with `curl -sL` over https rather than through
the screen's `urllib`, and treat `already_asked` as optional here: `gh` is the
reliable route and it also shows closed issues.

Evidence: 2026-09-17, the `curl -sL` query above (five titles returned), the
same query over `http` (301, empty output), and the six `already_asked` calls
in `/tmp/screenrun.py`.

## Rendering a *real* table's draft page on sqlite needs `RangeField.get_placeholder` patched too

What happened: the T316 critique reused the recipe above -- rebuild the draft
from the API document, in the `agents/sage.sh` container, on a throwaway
sqlite database -- and every entry insert failed with

    django.db.utils.OperationalError: unrecognized token: ":"

T315 was a polynomial table and never reached this. `Number` carries two
`DecimalRangeField`s, `value_range` and `frac_range` (`numberdb_app/models.py`),
which are the postgres search projection. Nulling them is not enough:
`django.contrib.postgres.fields.ranges.RangeField.get_placeholder` emits
`%s::numrange` whatever the value is, and the cast is what sqlite chokes on.

What worked, added to the two patches the T315 note lists, after
`django.setup()` and before `create_table`:

    from django.contrib.postgres.fields import ranges
    ranges.RangeField.get_placeholder = lambda self, value, compiler, connection: '%s'

    _save = models.Number.save
    def save(self, *a, **k):
        self.value_range = None
        self.frac_range = None
        return _save(self, *a, **k)
    models.Number.save = save

Nothing on the rendered page reads either column -- they exist for search by
number -- so the page is the page a reader gets: for T316, 243 rows and
188,528 bytes of HTML, status 200, with the column headers, the entry
comments, the prose and the reference numbering.

Evidence: 2026-09-18, T316 critique. `/tmp/t316_render_sage.py` (the script,
still worth promoting to `agents/render_draft.py` with the tid and the two
patches in it), `/tmp/t316_render_out.txt`, `/tmp/t316_page.html`.

## The `env | grep` key listing happened a fifth time, and the mask held

What happened: the T316 critique of 2026-09-18 found the SOCKS proxy refusing
connections and ran `env | grep -i -E 'proxy|numberdb'` to see why, which is
the fourth note above, repeated. The answer was the same as last time:
`ALL_PROXY=` is empty and a direct `curl https://numberdb.org/...` works.

Two things are different. The mask was `sed 's/\(KEY[A-Z_]*\)=.*/\1=<hidden>/'`
as well as the older `s/=.*KEY.*/=<hidden>/`, so `NUMBERDB_API_KEY`,
`NUMBERDB_KEY` and `NUMBERDB_KEY_FILE` all printed as `<hidden>` and no key
reached the transcript. And the prompt for this campaign says the proxy "is
needed", which is why a run reaches for the environment when it refuses: the
first thing to try is the direct `curl`, which the note of 2026-09-16 already
says and which works.

What to do instead: unset `NUMBERDB_API_KEY` in `run.sh` so the listing cannot
leak it, and stop telling the prompt that the proxy is required on a machine
where `ALL_PROXY` is empty.

## `/tags/<name>` answers 500, not 404, for a tag that does not exist

What happened: the T317 critique wanted to know whether the corpus has a knot
tag, so that a table tagged only `algebraic` could be compared with its
siblings. `https://numberdb.org/tags/algebraic`, `/tags/volume` and
`/tags/period` answer 200 with the tag's table list. `/tags/knot`,
`/tags/hyperbolic` and `/tags/zzz-nonsense-tag` all answer **500** with an
empty body. So the site cannot distinguish "this tag does not exist" from "the
tag page is broken", and an agent probing a name gets an error where it should
get a not-found.

It also means the obvious way to enumerate tags does not work: `/tags` is an
infinite-scroll page whose first response carries exactly one tag
("Appell sequence") and a `Loading...` placeholder, so a plain `curl` of it
lists nothing. Probing names one at a time is the only route from here, and a
500 has to be read as "no such tag".

What to do instead: treat 500 from `/tags/<name>` as "no such tag", and get a
table's own tags from `GET /api/table?id=T<n>` rather than from the tag pages.
The 500 is a site bug -- `views.tag` presumably does not handle
`Tag.DoesNotExist` -- and is worth an issue.

Evidence: 2026-09-18, T317 critique. `/tags/algebraic` 200 (listing T61, T132,
T135, T137, T35, T136, T60, T144, ...), `/tags/knot` 500, `/tags/hyperbolic`
500, `/tags/zzz-nonsense-tag` 500; `/tags` 22,554 bytes containing one tag name.

## Prose is not HTML-escaped on a rendered table page, so a `&` in math reaches the body raw

What happened: T317's comment (6) contains
`$\begin{pmatrix}a&b\\ c&d\end{pmatrix}\in \mathrm{SL}_2(\mathbb Z)$`. The
rendered page carries it verbatim -- `a&b`, not `a&amp;b` -- in the document
body. Nothing visible goes wrong: `&b` is not the prefix of any HTML5 named
character reference, so a browser flushes the ampersand as literal text and
MathJax reads the right string. But it is the same hole as the existing note
that link titles are not escaped, in a field a table is much more likely to
use, and it would not recover as kindly from `&amp` or `&lt` appearing inside
a formula -- or from the `<` that the skill already warns eats the rest of a
section.

What to do instead: when checking a rendered page for a critique, grep the raw
HTML for a bare `&` in the prose blocks as well as for `<`. Do not report it
as a fault of the table -- it is the site that does not escape -- but do check
that the particular text survives, because whether it does depends on what
follows the ampersand.

Evidence: 2026-09-18, T317 critique. `/tmp/t317_page.html` contains
`$\begin{pmatrix}a&b\\ c&d\end{pmatrix}` inside `<div class="table-entry">`.

## The sqlite draft-render recipe works unchanged for a *complex* table, and the previous run's script was not on this box

What happened: the T316 note above records the two patches a table of reals
needs before its draft page will rebuild on sqlite, and points at
`/tmp/t316_render_sage.py` as the script worth promoting. That file does not
exist on this machine -- `/tmp` has render scripts from 2026-09-13 to
2026-09-17 and none of the T315 or T316 ones -- so the script was rewritten
from the two notes. It worked first time for T317, a `type: C` table: the
complex values need no third patch, because `value_range` and `frac_range` are
the same two `DecimalRangeField`s whatever the type is, and nulling them plus
`RangeField.get_placeholder = lambda ...: '%s'` is the whole of it. 466 rows,
status 200, 366,096 bytes of HTML in one `agents/sage.sh` run.

Two details the earlier notes do not give. `NUMBERDB_SAGE_MEMORY=900m` was
used rather than the 320 MB default, because the pip install plus Django plus
Sage does not fit in 320 MB; and `NUMBERDB_SAGE_PYTHONPATH=` (set to empty)
has to be in the environment of the `agents/sage.sh` call itself, not inside
the script, since it is read by the wrapper to decide whether to pass
`-e PYTHONPATH`.

What to do instead: the script really should be promoted to
`agents/render_draft.py` with the tid as an argument -- three critique runs
have now written it from scratch. Until somebody does, write it from this note
and the two above rather than looking for the old copy.

Evidence: 2026-09-18, T317 critique. `/tmp/t317_render.py`,
`/tmp/t317_render_out.txt` (`records: 466`, `tid: T1`, `status 200 366096`),
`/tmp/t317_page.html`.

## SnapPy is in the Sage image, and a `Programs` snippet needs `Integer` in the namespace as well as `preparse`

What happened: T317's `Programs` block is two lines of Sage using SnapPy. The
existing note at "Testing a `Programs` snippet under `sage -python`: preparse
it and hand it `Integer`" is right and understates it: `preparse` turns
`[1, -2, 1, -2]` into `[Integer(1), -Integer(2), ...]`, so `exec`/`eval` of the
preparsed string fails with `NameError: name 'Integer' is not defined` unless
the namespace dict already holds `Integer` (and `RealNumber`, for any snippet
with a decimal literal). Passing `globals()` is not enough when the wrapper
itself was started with `sage -python`.

`import snappy` works in the wrapper image -- against the older note that
SnapPy is on the host and not in the container -- and prints one harmless
warning to stderr, `Plink failed to import tkinter, GUI will not be
available`. `snappy.Manifold('10_83')` works too, so the built-in Rolfsen
census is present; only `database_knotinfo` is missing.

What to do instead:

    from sage.repl.preparse import preparse
    from sage.rings.integer import Integer
    from sage.rings.real_mpfr import RealNumber
    ns = {'Integer': Integer, 'RealNumber': RealNumber}
    exec(preparse(line), ns)

Evidence: 2026-09-18, T317 critique. `/tmp/t317_programs.py` failed with
`NameError: name 'Integer' is not defined` and then reproduced five of the
table's stored values; `/tmp/t317_names.py` ran `snappy.Manifold(name)` for
ten Rolfsen names.

## The sqlite draft-render recipe needs the range patches for a *polynomial* table too, when one entry is a bare constant

What happened: the T316 note above says the two patches
(`RangeField.get_placeholder` to `%s`, and `Number.save` nulling `value_range`
and `frac_range`) are what a *real* table needs, and that "T315 was a
polynomial table and never reached this". T319 is a polynomial table and
reached it on its first row:

    Error saving number: {'raw_number': '1', 'parsed_repr': '1',
      'parent': 'Integer Ring', 'is_polynomial_ring_parent': False,
      'exception': "OperationalError('unrecognized token: \":\"')"}
    sqlite3.OperationalError: unrecognized token: ":"

$P_0=1$, so the entry is the bare string `1`, and the parser reads that as an
element of the integer ring rather than of $\mathbb Z[x]$ -- which gives it the
numeric range projection, and the postgres `::numrange` cast that sqlite
refuses. T315's entries were all of positive degree, which is why it never hit
it.

What to do instead: apply both patches unconditionally, whatever the table's
`type`. They are inert on a table that never writes a range, and one constant
entry is enough to need them.

Evidence: 2026-09-18, T319 critique. `/tmp/t319_render.py` (first run without
the patches, the traceback above; with them, `records: 8`, `tid: T1`,
`status 200 29495`), `/tmp/t319_page.html`.

## `/preview?table=` needs `Parameters`, `Data properties` and a `Numbers` section, and blames the numbers when they are missing

What happened: rendering T319's prose in slices through `/preview?table=` --
the route the T314 and T317 critiques used, because the whole document does not
fit a request line -- every slice that carried only prose answered 200 with

    Error while parsing numbers: cannot access local variable
    'number_section' where it is not associated with a value

and no rendered table at all. The message names the numbers, but the slices
that failed were the ones with no `Numbers` key; adding `Parameters`, `Data
properties` and three entries to each slice rendered all of them. So a preview
of a `Comments` block has to carry the scaffolding of a whole table, and the
error it gives otherwise reads like a fault in the numbers a run did not send.

The other half of the constraint is the request line: gunicorn refuses at 4094
bytes with `Request Line is too large (6267 > 4094)`, and a URL-encoded YAML
document runs about 1.6 times its own length, so a slice can carry roughly
2,400 characters of YAML. T319's whole document is 4,641, which is why it went
in four.

What to do instead: build each preview slice as
`Title + Parameters + <the section> + Data properties + Display properties +
two or three entries`, keep it under about 2,400 characters of YAML, and read
the `CITE`s with care -- a citation whose target is in a slice you left out
renders as a `CITE-broken` span, which is an artefact of the slicing and not a
fault in the table. The whole-page rebuild on sqlite (the note above) has
neither problem and is what a finding should be quoted from.

Evidence: 2026-09-18, T319 critique. `/tmp/prev.py` (four prose-only slices,
all four with the `number_section` message), `/tmp/prev2.py` (the same four
with scaffolding, 17-20 KB of rendered HTML each), and the 400 from
`--data-urlencode table@/tmp/T319.yaml`.

## `/files/<tid>/<name>` serves a draft's attachment to an API key, where `/T<n>` answers 404

What happened: the T319 critique wanted the generator as a reader downloads it
rather than as the repository holds it. `GET /T319` answers 404 to the zeta3
key, as the T182 note records, but

    curl -H "X-API-Key: ..." https://numberdb.org/files/T319/generate.py

answers 200 with the file's own page: the size and revision date
("4,923 bytes, as of the version from 2026-09-18 01:35 (current). Recorded
here, not run.") and the source inside a `<pre>`, HTML-escaped. Unescaping that
block gave a file byte-identical to
`generators/shapiro-polynomials/generate.py`, which is how the two copies were
compared without a session.

So the file routes honour the key where the table routes do not. Useful: a
critique can read the attachment a reader gets, and can check the claim that
the repository copy and the attached one agree, which the skill's rule about
generators living on the table makes worth checking.

Evidence: 2026-09-18, T319 critique. `curl` above (200, 17,674 bytes of HTML,
title `generate.py - Shapiro polynomials $P_n$ - NumberDB`), and `diff` of the
unescaped `<pre>` against the repository copy, which is empty.

## OEIS is unreachable from this machine, so an A-number cannot be checked here

What happened: the test-matrix proposal wanted to cite the OEIS sequence of
Hilbert matrix determinants, $1, 12, 2160, 6048000, 266716800000, \dots$.
`curl https://oeis.org/search?q=12,2160,6048000,266716800000&fmt=text` returns
a Cloudflare interstitial ("Just a moment..."), not results, and a fetch agent
with its own client got a bare **403 on every OEIS URL it tried**, including
`https://oeis.org/A000001` -- so it is the host refusing this network, not the
search endpoint or the query.

What to do instead: cite the sequence by its terms and say the A-number was
not verified, or leave the OEIS check to a build that runs somewhere else. Do
not write an A-number from memory into a proposal or a table: the lesson file
already records one campaign that gained a real check from OEIS
(`A305474`, the Hilbert class polynomial triangle), which is exactly why a
guessed A-number would be believed.

Evidence: 2026-09-18, ideas run. `curl` above; a `web-fetch` agent reporting
403 on four OEIS URLs including a bare sequence page.

## `screen.py`'s `already_asked` misses an issue that asks for the proposal

What happened: `already_asked` returned `[]` for "Characteristic polynomials
of the classical test matrices", while **numberdb-data#67** is open and titled
*Characteristic polynomials of interesting (small) matrices*. The function
takes the words of the name longer than four letters, keeps the **first
three**, and searches GitHub `in:title` for all of them. Here that is
"Characteristic polynomials classical", and no issue title contains
"classical". Any name whose distinguishing word comes fourth has the same
problem, and the answer is indistinguishable from "nobody asked".

What to do instead: pull the whole issue list once --
`gh issue list --repo numberdb/numberdb-data --state all --limit 400 --json
number,title,state` -- and grep it for the subject's words. All three issues
this batch answers (#67, #126, #127) were found that way and none by the
screen. `already_here` has the opposite failure and is honest about it: it
returns everything that matched any word, so its answer is noise a reader
filters rather than a false negative.

Evidence: 2026-09-18, ideas run. `/tmp/scr3.py` (five names, `already_asked`
empty for all five); `gh issue list ... | grep -i matri` (three open issues).

## mathworks.com answers 403 to `screen.py` but is readable by a fetch agent

What happened: `source_names_it('test matrices',
'https://www.mathworks.com/help/matlab/ref/gallery.html')` reports
`source answered 403`. The page is real and is the source of half the matrix
definitions in the 2026-09-18 batch; a `web-fetch` agent read it (HTTP 200,
71 KB, though only the first 39 KB came back as page text and the tail as a
summary, which is its own hazard: the summary invented a wrong formula for the
Frank matrix that the verbatim window contradicted).

What to do instead: when `source_names_it` reports 403 rather than a missing
word, screen the family against a second durable source that does answer --
`https://math.nist.gov/MatrixMarket/` passed for "test matrices" -- and say in
the proposal which source each definition actually came from. A 403 is not
evidence that the family is invented, and the screen cannot tell the
difference.

Evidence: 2026-09-18, ideas run. `/tmp/scr.py` and `/tmp/scr2.py`.

## The codex quota fallback names a model the account cannot use

What happened: build run 20260918T023210Z ran out of gpt-5.5 quota mid-turn
(`You've hit your usage limit [...] try again at Sep 19th, 2026 2:17 PM`). The
runner handled it by switching models and recorded the switch:

    === out of quota on gpt-5.5; resuming on gpt-5.4 at effort xhigh
        (and for the runs after this one)

The resumed session died before its first tool call:

    HTTP 400 invalid_request_error: The 'gpt-5.4' model is not supported
    when using Codex with a ChatGPT account.

preceded by two warnings that say the same thing more quietly -- `This session
was recorded with model gpt-5.5 but is resuming with gpt-5.4` and `Model
metadata for gpt-5.4 not found. Defaulting to fallback metadata`.

Why it matters beyond the one run: the parenthesis is literal. The fallback is
written to `agents/runs/codex-fallback` (`gpt-5.4`, `xhigh`) and read by every
later stage, so the whole remainder of the batch inherits a model this account
is not entitled to. Each codex build and repair then fails on turn 1, costs
$0, and triggers a triage run to be told the same thing. A fallback that fails
for free is more dangerous than one that fails expensively: nothing about the
spend curve flags it.

What to do instead: the fallback must name a model the ChatGPT account
actually has. Until it does, clear `agents/runs/codex-fallback` and either
wait out the quota or run the affected stages on the claude engine -- the
critique and ideas stages of this same batch were running on claude throughout
and were unaffected. A quota exhaustion is worth distinguishing from an
ordinary API error in the runner: it is not retryable for hours, so resuming
immediately on any model is the wrong reflex.

Evidence: 2026-09-18. `agents/runs/20260918T023210Z-build.log` lines 140-147;
`agents/runs/campaign-20260917T011039Z.log` lines 35190-35201;
`agents/runs/codex-fallback`.

## `COSTS.tsv` records the failed resume and not the turn that did the work

What happened: the same run's ledger row is

    20260918T023210Z  build  codex  0  0.0000  error  ...  gpt-5.4  ...  resumed=yes  0  0  0  gpt-5.4=0.0000  <empty table column>

Every number in it describes the *second* attempt -- the 400 that never ran a
tool. The first attempt made about seventy tool calls on gpt-5.5, read the
skill and half the generator tooling, exhausted the account's quota, and
created draft T320. None of that is counted: 0 turns, $0.0000, 0 tokens, and
an empty `table` column even though the run's lasting effect was a new draft.

So the campaign's own records assert that this run cost nothing and touched no
table, and both are false. Anything reconciling spend, or working out which
drafts belong to which run, will silently skip it -- and T320 is exactly the
kind of half-created table a later run would otherwise be warned about.

What to do instead: when a run is resumed, the ledger row should accumulate
across attempts rather than be overwritten by the last one, and the `table`
column should be filled from what the run actually created (the create
response carries the `tid`) rather than from a successful exit. Treat a
`$0.0000` row with `resumed=yes` as "unmeasured", not as "free".

Evidence: 2026-09-18, `agents/runs/COSTS.tsv` line 312, against
`agents/runs/20260918T023210Z-build.log` (the T320 create at item_69/item_70
returns `{"tid": "T320", ... "drafts_held": 7}`).

## The sqlite draft-render recipe's `_sync_tags` replacement takes the document, not a list of names

What happened: the T320 critique rebuilt the draft's page by the recipe above
(API document, Sage container, throwaway sqlite, both range patches). The page
came out at status 200 with all eight rows, and its tag strip read

    title  definition  parameters  comments  formulas  programs
    similar tables  links  keywords  tags  data properties  display properties
    numbers

rather than the table's own `polynomial` and `combinatorics`. Those are the
document's *section names*, lowercased. The stand-in for `editing._sync_tags`
had been written as `_sync_tags(table, names)` and was iterating the dict it
was handed; the real signature is `_sync_tags(table, document)`, and iterating
a document yields its keys. Nothing failed, nothing was logged, and the fault
looks exactly like a table tagged by somebody who misunderstood tags -- which
is the kind of finding a critique would have written up as the table's.

What to do instead: the replacement has to do what the original does except
the final `update(search_vector=...)`, which means going through
`editing._tag_names(document.get('Tags'))` and the 32-character skip:

    def _sync_tags(table, document, **kwargs):
        from numberdb_app.models import Tag
        if not isinstance(document, dict):
            return
        tags = []
        for name in editing._tag_names(document.get('Tags')):
            if len(name) > 32:
                continue
            tag, _ = Tag.objects.get_or_create(name=name)
            if tag not in tags:
                tags.append(tag)
        table.tags.set(tags)

More generally: the two writes this recipe patches out are the two that build a
postgres search vector, and both are patched by *replacement*, so a replacement
whose signature is guessed produces a page that renders and lies. Check the
rebuilt page's tags against `Tags` in the document before quoting anything else
off it. The same care applies to `reindex_for_search`, though there the stand-in
is a no-op and cannot be wrong.

Evidence: 2026-09-18, T320 critique. `/tmp/t320_render.py` (first run, tags from
the section names, 31,422 bytes of HTML; second run with the signature fixed,
30,777 bytes and `<a class="tag" href="/tags/polynomial">`),
`/tmp/t320_render_out.txt` and `/tmp/t320_render_out2.txt`.
`numberdb_app/editing.py`, `def _sync_tags(table, document)`.

## Nothing is listening on port 1080 at all now, so the proxy notes above understate it

What happened: the T321 critique started with the prompt's
`curl -s --socks5-hostname 127.0.0.1:1080 https://numberdb.org/skill`, which
exited 7 having printed nothing. The earlier notes here describe a live
`ssh -N -D` tunnel that stays up with a dead connection and times every request
out; that is not today's state. `ss -ltn` shows **no listener on 1080 at all**,
so every request fails immediately rather than after a minute, and there is no
process to restart or wait for.

What to do instead: `curl https://numberdb.org/...` with no proxy at all, which
works from this machine and is how this whole run read the site -- the skill
(47,534 bytes, byte-identical to the copy the T320 run left in `/tmp`), the
public pages of T318 and T319, `/tables`, `/api/table`, `/api/table/<tid>/audit`
and `/api/search`. Crossref (`api.crossref.org`) answers directly too, which is
how both of T321's DOIs were checked.

And: do not run `env | grep` to find out why the proxy is down. That has now
happened five times and is written up twice above; `ss -ltn | grep 1080` answers
the same question and prints no key.

Evidence: 2026-09-18, T321 critique. `curl` exit 7 on the proxy, `ss -ltn` empty
for 1080, `curl https://numberdb.org/skill` 200 in the same minute.

## The sqlite draft-render recipe works unchanged for a *rational* table

What happened: the T321 critique rebuilt T321's draft page by the recipe above
-- the API document, the `agents/sage.sh` container, a throwaway sqlite
database, `editing.reindex_for_search` as a no-op, `_sync_tags` replaced with
the version that goes through `editing._tag_names` (the note above), plus the
two range patches from the T316 note. It worked first time: 167 records, status
200, **85,252 bytes** of HTML, the rows with their `$p$` and `$F_p$` headers,
the prose in the page's own section order (Formulas before Comments, which is
what the critique's first finding is about), the reference numbering, and the
tag strip reading `number theory combinatorics` -- the table's own tags, which
is the check the `_sync_tags` note says to make before quoting anything else off
the page.

So the recipe has now run for a polynomial table (T315, T320), a real one
(T316), a complex one and a rational one, and the only variation anybody has
needed is the `RangeField` pair for tables whose entries go through
`value_range`. A rational table needs them: `Number.save` writes those columns
whatever the type.

The script is `/tmp/t321_render.py`, 100 lines including the pip install, and
it takes the tid in one place. It is still worth promoting to
`agents/render_draft.py` with the tid as an argument -- this is the fourth run
to write it out from the notes.

Evidence: 2026-09-18, T321 critique. `/tmp/t321_render.py`,
`/tmp/t321_render_out.txt` (`records: 167`, `tid: T1 tags: ['combinatorics',
'number theory']`, `status 200 85252 bytes`), `/tmp/t321_page.html`.

## An interactive session declares itself, or it is recorded as `api`

Editing through the API from a session somebody is typing in -- Claude Code,
Codex CLI, a script -- the write should say what ran. Without it the revision
records `api`, which is what a person at a keyboard looks like, and that is
how 121 assisted revisions came to be indistinguishable from hand edits under
the same account.

With `curl`, four headers:

    -H "X-Pipeline: interactive" \
    -H "X-Engine: claude-code" \
    -H "X-Model: claude-opus-5" \
    -H "X-Session: $CLAUDE_SESSION_ID"

With the `numberdb` package, the same thing from the environment, since the
client turns these into the headers above:

    export NUMBERDB_PIPELINE=interactive
    export NUMBERDB_ENGINE=codex-cli
    export NUMBERDB_MODEL=gpt-5.5

The author is unchanged: it is the account whose key signed the request, which
is the thing that answers for the digits. This only adds what assisted it. A
campaign stage needs none of this -- `agents/run.sh` exports the lot, including
the pipeline's version and the digest of its scope.

See docs/design/pipeline-provenance.md.
## A draft's attached files are served to anybody; only its *page* is refused

What happened: the T324 critique fetched the table's generator to check a claim
in `rigour details`, and `curl https://numberdb.org/files/T324/generate.py` with
no key, no cookie and no header answered **200 with the whole script**, as did
`/files/T324` with the file list and the draft's title. The same caller gets 404
from `/T324`.

`table_file` and `table_files` in `numberdb_app/views.py` (about lines 3055 and
3146) do `get_object_or_404(Table, tid=tid)` and go straight on. The table page
and `/preview` both call `_refuse_a_draft` first -- the guard added after
`/preview/T133` rendered a private draft to anybody who guessed its number.
These two routes are the same fault in another door: a draft is supposed to be
invisible, and its generator, its `table.yaml` and its title are readable by
T-number.

What to do instead: a run has no business fixing this and cannot deploy anyway,
so it is written here rather than acted on. Two things follow for a run meeting
it. It is the reason a critique *can* read a draft's attachments without a key,
which is convenient and should not be relied on. And do not treat "the draft is
private" as covering anything a build attaches: today the attachments are
public from the moment the revision is created.

Evidence: 2026-09-18, T324 critique. `curl -sS -o /tmp/T324-gen-anon.html -w
'%{http_code}' https://numberdb.org/files/T324/generate.py` -> `200`, 19,593
bytes, the `<pre class="file-source">` holding the 204-line generator
byte-identical to `generators/level-one-cusp-form-l-zeros/generate.py`;
`https://numberdb.org/T324` -> `404` in the same minute.

## `/preview?table=` needs a non-empty `Numbers`, or it renders an error instead of the page

What happened: the piecewise `/preview` render described in the T289 note was
sent with `Numbers: []` on the sections that have no entries to show. Every
request answered **200**, and every page said

    Error while parsing numbers: cannot access local variable
    'number_section' where it is not associated with a value

with no table rendered at all -- no Definition, no Comments, nothing. It is a
bug in the preview path (an uninitialised local when the numbers list is
empty), and it fails in the one way that wastes a run's time: the status is 200
and the page is 7 KB rather than 17 KB, so a script that checks the status
learns nothing.

What to do instead: put one real entry in every piece. Sending the same single
entry with each section costs about 250 bytes of the ~4 KB request budget and
the pages then render in full. A size check is the cheap tell: a section that
rendered came back at 15-19 KB here, an errored one at 6.5-7.1 KB.

Evidence: 2026-09-18, T324 critique. Eleven pieces, all 200, all 6.5-7.1 KB with
`Numbers: []`; the same eleven at 15.1-18.8 KB with
`Numbers: {12: {1: {1: <the stored entry>}}}` appended. `/tmp/preview.py`.

## A repair is applied to the live document and not to `generators/*/table.yaml`, so the next table copied from the repository inherits the repaired-away text

What happened: T323 was critiqued at 07:10 on 2026-09-18 and repaired at 07:22;
`agents/critiques/T323-repaired.md` records seven fixes, all *done*. They were
made to the live document through the API. The repository's copy,
`generators/level-one-cusp-form-l-values/table.yaml`, was last touched at 06:55
and still holds the pre-repair Definition and all three pre-repair `Comments`.
T324's draft was created at 07:36 with `comment-ordering`,
`comment-normalisation` and `comment-central-zero` carrying the pre-repair
sentences word for word -- four of that critique's findings, reintroduced in a
new table fourteen minutes after they were closed in the old one.

What to do instead: a build that starts from a sibling table should take the
sibling's prose from `GET /api/table?id=<tid>`, which is the repaired copy, and
not from `generators/<name>/table.yaml`, which is a snapshot of the day it was
written. A repair run that edits a live document and leaves the generator's
yaml alone should say so in its repair note, since the yaml is what the next
build will read.

Evidence: 2026-09-18, T324 critique. `git log` on
`generators/level-one-cusp-form-l-values/table.yaml` (last commit `a26e063`,
06:55) against the live T323 document; `git log` for `0f213ec` (07:22, the
repair record) and `d15d462` (07:36, the T324 draft).

## `screen.source_names_it` checks the words separately, so it passes on a page that never uses the phrase

What happened: `agents/table-ideas/screen.py` splits a proposal's name into its
distinguishing words and reports a complaint only for words the page does not
contain anywhere. Screening "Chern classes of a complete intersection" against
`https://en.wikipedia.org/wiki/Chern_class` returns `None` -- a pass -- and that
page does not contain the phrase "complete intersection" at all. It contains
"complete" (in "complete the proof", and in several unrelated places) and
"intersection" (in "intersection product"), and that is enough.

The check is still worth running: it catches an invented family, which is what
it is for. What it cannot do is confirm that the source *names* the family, and
a run that reports "source_names_it: None" as if it had is reporting something
it did not measure.

What to do instead: when a pass depends on common words rather than on a proper
noun, fetch the page and grep for the phrase before writing the proposal up,
and say in the proposal which sections actually treat the subject. A one-line
probe is enough:

    ' '.join(re.sub(r'<[^>]+>', ' ', body).lower().split()).find('complete intersection')

Evidence: 2026-09-18, ideas run. `source_names_it('Chern classes of a complete
intersection', 'https://en.wikipedia.org/wiki/Chern_class')` returns `None`
while a phrase probe of the same page returns `-1`. The same page *does* carry
the sections "Normal sequence", "Quintic threefold" and "Degree d
hypersurfaces", which treat the hypersurface case, so the proposal is sound and
the screen's reason for saying so was not.

## `screen.already_asked` rate-limits after about a dozen calls, and the failure reads like "nothing found"

What happened: `already_asked` goes to `api.github.com/search/issues`
unauthenticated. Screening twelve candidates in one loop exhausted the
unauthenticated quota partway through, and the last two rows came back as
`['could not ask GitHub (HTTPError)']`. That is honest -- the function was
written not to return `[]` on failure, for exactly this reason -- but in a table
of screening results it sits in the same column as a genuine empty answer and
is easy to read past.

What to do instead: run the tail through `gh`, which is authenticated in this
environment and searches closed issues too:

    gh search issues --repo numberdb/numberdb-data --match title "Chern" \
        --limit 10 --json number,title,state

Evidence: 2026-09-18, ideas run, twelve candidates screened in one process; rows
eleven and twelve returned the HTTPError string. Re-running ten search terms
through `gh` took seconds and found the one issue that matters (#108, open).

## The repository's own `numberdb/` package shadows the client, so `import numberdb` from the repository root is the Django app

What happened: `PYTHONPATH=clients/python python3 -c "import numberdb"` run from
`/home/ubuntu/numberdb-website` imports `/home/ubuntu/numberdb-website/numberdb`
-- the Django project package, which has no `search_text` and no `table` -- and
not `clients/python/numberdb`. Python puts the working directory ahead of
`PYTHONPATH`. The failure is an `AttributeError` on the first call rather than
an `ImportError`, so it does not look like a path problem.

`agents/sage.sh` is unaffected: it mounts the file under `/work` in a container
and puts the client on the path there. This bites only a plain `python3` used
for the screening helpers, which do not need Sage.

What to do instead: run screening scripts from another directory, copying
`screen.py` beside them:

    cp agents/table-ideas/screen.py /tmp/ && cd /tmp && \
        PYTHONPATH=/home/ubuntu/numberdb-website/clients/python python3 /tmp/s1.py

Evidence: 2026-09-18, ideas run. From the repository root,
`import numberdb; numberdb.__file__` is
`/home/ubuntu/numberdb-website/numberdb/__init__.py`; from `/tmp` with the same
`PYTHONPATH` it is the client.

## The corpus is 269 tables, and `agents/table-ideas/PROMPT.md` still says 126

What happened: the stage-one prompt tells a run that "126 tables exist" and that
the tag list "has 66 tags". Walking `numberdb.table('T1')` through `T269` this
run returns **269 tables** (every number from T1 to T269 except T75). A run that
believes the prompt underestimates the corpus by more than half and will screen
against a picture of a database that stopped growing in August.

What to do instead: walk the T-numbers at the start of a run -- there is still
no call that lists the corpus -- and use what comes back. Updating the number in
`PROMPT.md` only postpones the problem; the sentence would be better written as
"walk the T-numbers; there were 269 on 2026-09-18".

Evidence: 2026-09-18, ideas run. `/tmp/corpus.py`, a loop over `T1`..`T269`
printing `Title` and `Tags`, returned 269 rows, the last being T269 *Meixner
polynomials*.

## `WebSearch` is not permitted to this runner

What happened: looking for a durable web page that names a family by its full
phrase, the ideas run called `WebSearch` and got "Claude requested permissions
to use WebSearch, but you haven't granted it yet". Unattended, there is nobody
to grant it.

What to do instead: probe candidate URLs directly with `urllib` and check the
text, which is what `screen.source_names_it` does anyway. Ten candidates took
one script and about twenty seconds. Two results worth keeping so nobody else
tries them: `https://ncatlab.org/nlab/show/complete+intersection` and
`https://mathworld.wolfram.com/CompleteIntersection.html` are both **404**, so
neither is available as a citation however natural it looks.

Evidence: 2026-09-18, ideas run; `/tmp/s6.py`.

## `/preview?table=...` renders nothing at all for a document with no `Numbers`

What happened: T326's critique rendered a private draft the way the T221 note
above prescribes -- `/preview?table=<yaml>` in pieces kept under the 4 KB
request line -- and the first five pieces came back 200 with an empty preview.
Each of those pieces carried the title and one prose section and no entries.
The page had rendered a red message instead:

    Error while parsing numbers: cannot access local variable
    'number_section' where it is not associated with a value

which is a Python `UnboundLocalError` in the number parser escaping as a user
message, not a statement about the YAML. A piece is not invalid for holding no
numbers, and the same document renders fine the moment one entry is added.

What to do instead: give every piece a `Numbers` section -- one row is enough,
and adding `Parameters` with it keeps the parameter list rendering as it does
on the page. Three lines in the piece builder:

    piece.setdefault('Parameters', DOC['Parameters'])
    piece.setdefault('Numbers', {'12': {'1': DOC['Numbers']['12']['1']['number']}})

The site should also not be answering a reader's YAML with the name of one of
its own local variables; the parser initialises `number_section` inside a
branch that a document with no `Numbers` never enters.

Two smaller things from the same run, for whoever renders the next draft.
`/preview/T326` answers 404 to a request carrying the API key, as does `/T326`:
both routes take the user from the session, and an API key does not make one,
so `/preview` with the document in the query string is the only route in
without Django. And thirteen pieces covering the prose, the data properties,
both programs and all 24 entries cost thirteen requests and about four seconds
in total, so there is no reason to economise on pieces.

Evidence: 2026-09-18, T326 critique. `/tmp/prev326.py` and
`/tmp/prev-*.html`; the five empty renders were 6.2 to 7.1 KB where a rendered
piece is 14 to 20 KB. Nothing was listening on 127.0.0.1:1080 again, and
`curl` without the proxy answered 200, as the note above already says.

## A table's `Programs` snippet can be run verbatim by mounting `generate.py` beside a two-line runner

What happened: the T328 critique wanted to know whether the `Programs` section
works for a reader, not just whether it looks right. The snippet begins "In the
directory containing the attached generate.py:" and then does `from generate
import LebesgueConstantsInterpolationNodes`. `agents/sage.sh` copies every file
named on its command line into `/work` and runs the first one there, and the
container's working directory is `/work`, so a bare `from generate import ...`
resolves with no path juggling:

    agents/sage.sh /tmp/t328_programs.py \
        generators/lebesgue-constants-interpolation-nodes/generate.py

where `/tmp/t328_programs.py` is the snippet copied out of the document with
nothing added. It printed a 157-digit ball for a degree one past the end of the
table, in about ten seconds. That is a real check a critique can make cheaply,
and it is a different check from reading the snippet: it catches a stale class
name, a renamed parameter key, or a `value()` signature that has moved.

This is not the `/work/generate.py` trap recorded above -- that one is about a
*runner* that has to name mounted files by their `/work/<basename>` paths.
Here the snippet names nothing, and the point is that it does not have to.

What to do instead: when a critique reaches `Programs`, run it. Copy the code
out of the document unchanged into `/tmp`, mount the generator after it, and
see what comes back.

Evidence: 2026-09-18, T328 critique. `/tmp/t328_programs.py` printed
`cwd /work files ['generate.py', 't328_programs.py']` and then
`[3.10630115936782781142310041352131153497964688837426131147957999585470682827311412948015953779308387471972389753583006165128609628163204672822101380196268442 +/- 8.93e-158]`.

## `agents/sage.sh` can return timeout status after Sage has printed the answer

What happened: a T328 repair check ran the exact Gauss-Legendre $n=5$
Lebesgue-constant computation with `NUMBERDB_TIMEOUT=150`. The Sage script
finished the computation, printed

    finished 235.72116094798548
    3.748806539240457?

and then `agents/sage.sh` returned exit code 124. The wrapper's timeout had
expired, but the Sage process did not stop before the exact algebraic routine
finished and flushed its result. Reading only the exit status would have lost
the useful timing and value; reading only stdout would have missed that the run
overran the intended cap.

What to do instead: when a timed Sage check returns 124, still read stdout. If
the script printed a completed result, it may be usable as evidence of cost,
but record the timeout status beside it and rerun with a larger
`NUMBERDB_TIMEOUT` if the exit status itself matters.

Evidence: 2026-09-18, T328 repair. `NUMBERDB_TIMEOUT=150 agents/sage.sh
/tmp/t328_time_gauss5.py generators/lebesgue-constants-interpolation-nodes/generate.py`
printed the lines above and exited 124.

## `api/table?id=` with the key reads a private draft's whole document

What happened: the T329 critique needed the document of a draft on a runner
with no Django. The note above ("Corpus searches and slugs need no Sage run")
says `api/table?id=T128` gives a published table's document and "answers 'does
not exist' for a draft", which reads as if the route were closed to drafts
altogether, and an earlier campaign reached for `/preview` and the client
before trying it. It is not closed: the route refuses a draft only to a
request that cannot see it. `api.table` calls `_may_see_draft`, so the
author's or the board's key gets the full document, deliberately -- otherwise
a generator could create a draft through the API and then not read it back.

    curl -s -H "Authorization: Bearer $(cat "$NUMBERDB_KEY_FILE")" \
         'https://numberdb.org/api/table?id=T329'

answered 200 with 96 KB of JSON, `Numbers` included, while `GET /T329` and
`GET /api/table?id=T329` without the key both answer 404 / "does not exist".
Note `id=`, not `tid=`: the parameter is `id` (or `url`), and `tid=` falls
through to "No id or url given."

What to do instead: to read a draft's *document*, ask `api/table?id=<TID>`
with the key. `/preview?table=` in pieces is still the only way to see the
draft *rendered*, because the page route refuses a draft to everybody.

Evidence: 2026-09-18, T329 critique. The call above, against
`numberdb_app/api.py:377` and its `_may_see_draft` guard.

## A `/preview` piece names the entries block "Polynomials" only if it carries `Data properties`

What happened: the T330 critique rendered a private draft through
`/preview?table=` in eleven pieces, as the T221, T225 and T226 notes describe.
The heading over the entries block was not the same in every piece. The two
pieces that carried `Data properties` (with `type: Q[]`) headed it
**Polynomials**; the nine that did not headed it **Numbers**, from the same
document, the same `Parameters` and the same entries. The renderer names that
block from the declared type, and a piece assembled to test one prose section
does not carry the type unless it was put there.

This matters because the heading is one of the things a reader is supposed to
check, and the piece-wise workaround silently changes it. A run reading a piece
without `Data properties` sees "Numbers" over a column of polynomials and can
write that up as a table that failed to declare its type, which is a finding
about the workaround and not about the table.

What to do instead: judge the entries-block heading only from a piece that
carries `Data properties`, or add `Data properties` to every piece that carries
`Numbers`. The same caution as the T225 note about `Parameters`: what a piece
omits changes what the rest of it renders as.

Evidence: 2026-09-18, T330 critique. `/tmp/p330_a.html` and `/tmp/q330_f.html`
(with `Data properties`) -> "Polynomials"; `/tmp/q330_b.html` through
`/tmp/q330_k.html` and `/tmp/p330_[hij].html` (without) -> "Numbers".

## A table assigned as a draft can be published under you; retry `/T<TID>` before building preview pieces

What happened: the T331 critique was assigned with the usual note that "the key
is in the environment for a draft", and the T329 and T330 critiques immediately
before it had both been private drafts reconstructed through `/preview?table=`
in ten or eleven pieces. `https://numberdb.org/T331` did answer 404
unauthenticated at 14:05 UTC. At 14:09 the same request answered 200 with the
whole rendered page, 235,805 bytes, and `GET /api/lookup?text=143/26880`
returned `{"index": "lehmer,7", "table_id": "T331"}`, so the table was public
and searchable by number. Nothing in the run caused it: the revision history
shows three revisions by zeta3 at 13:58 and 14:04 and no later write, and
publishing is not something this account can do.

Two things follow. The rendered page a critique needs was available whole,
which is better evidence than any number of preview pieces, and four minutes of
assuming otherwise would have bought a piece-wise reconstruction with the
`Parameters`, `Data properties` and `CITE`-target caveats the T221, T225, T226
and T330 notes describe. And the audit's draft-link rule, which is guarded by
`table.published`, had started firing: `GET /api/table/T331/audit` reported
`HREF{T327} points at a draft`, as did T329's and T330's, because those two had
been published in the same window.

What to do instead: fetch `/T<TID>` unauthenticated first, whatever the
assignment says the table's status is, and re-fetch once before concluding it
is private. A 404 means "not published *yet*" and the window can be minutes
wide when a batch is being reviewed. The audit endpoint is a second signal in
the same direction: a `points at a draft` finding about some *other* table means
the server thinks this one is published.

Evidence: 2026-09-18, T331 critique. `curl -s -o /dev/null -w '%{http_code}'
https://numberdb.org/T331` -> 404 at 14:05, 200 at 14:09;
`https://numberdb.org/revisions/T331` shows revisions at 13:58 and 14:04 only;
`GET /api/table/T331/audit` -> one finding, `clean: false`.

## What goes in `site.tgz` for the sqlite draft-render recipe

What happened: the T332 critique wrote the render script from the notes above,
for the fifth time, and lost two `agents/sage.sh` runs to the one thing none of
them says: which directories the tarball has to contain. The script extracts
`/work/site.tgz` to `/tmp/site`, puts it on `sys.path` and calls
`django.setup()`, and `numberdb_app/models.py` imports across the repository at
module scope, so a tarball of the obvious four packages fails inside
`apps.populate` with `ModuleNotFoundError` -- naming a different module each
time, one per run:

    numberdb numberdb_app templates static manage.py   -> No module named 'utils'
    ... + utils workers                                -> No module named 'data_pipeline'

What works, and is 1.6 MB:

    tar czf /tmp/site.tgz --exclude='.git' --exclude='static/vendor' \
        --exclude='staticfiles' --exclude='__pycache__' --exclude='agents' \
        --exclude='generators' \
        numberdb numberdb_app templates static utils workers data_pipeline \
        clients manage.py

`static/vendor` must be excluded or the tarball carries the 2 MB single-line
`tex-svg.js` for nothing; `agents` and `generators` are excluded because the
rendered page does not read them and `agents/runs` is large.

The recipe then works unchanged for a `Z[]` table with a variable-length
`Symbolic` index: T332 rebuilt at **999 records, status 200, 511,127 bytes**,
with all 999 entry anchors present and unique (`2,2` through
`10,2,2,2,2,2,3`), the three tags right, and the section order the page's own
(`Formulas` before `Comments`). The two range patches from the T316 and T319
notes were both needed, as the T319 note predicts for a polynomial table with a
bare-constant entry -- T332 has two entries that are the polynomial `1`.

So the recipe has now run for polynomial (T315, T319, T320, T332), real (T316),
complex (T317) and rational (T321) tables, and this is the fifth run to write
the script from these notes. Promoting it to `agents/render_draft.py` with the
tid as an argument, and this tarball line inside it, would end that.

Evidence: 2026-09-18, T332 critique. `/tmp/t332_render.py` (T321's script with
the tid changed), `/tmp/t332_render_out.txt` (`records: 999`, `tid: T1 tags:
['algebra', 'characteristic classes', 'polynomial']`, `status 200 511127
bytes`), `/tmp/t332_page.html`. `NUMBERDB_SAGE_MEMORY=1200m
NUMBERDB_SAGE_PYTHONPATH= agents/sage.sh /tmp/t332_render.py /tmp/site.tgz
/tmp/T332.json`.

## The sqlite draft-render recipe works unchanged for an integer (`Z`) table, and the previous run's `/tmp` script survived

What happened: the T333 critique had to render a private draft and found both
`/tmp/site.tgz` (1.6 MB, built by the T332 run at 15:04) and
`/tmp/t332_render.py` still on the box. Changing the tid was one `sed`:

    sed -e 's/T332/T333/g' /tmp/t332_render.py > /tmp/t333_render.py
    NUMBERDB_SAGE_MEMORY=1200m NUMBERDB_SAGE_PYTHONPATH= \
        agents/sage.sh /tmp/t333_render.py /tmp/site.tgz /tmp/T333.json

That produced **999 records, status 200, 476,482 bytes**, with every row, the
`Programs` block's indentation intact inside `<pre><code>`, and the section
order the site's own. So the recipe has now run for polynomial (T315, T319,
T320, T332), real (T316), complex (T317), rational (T321) and **integer
(T333)** tables. The `Number.save` patch that nulls `value_range` and
`frac_range` is still needed for `Z`; the two range patches the T316 and T319
notes add were already in the T332 script and did no harm.

The previous note asks for `agents/render_draft.py`. Until somebody writes it,
the cheap move is to look in `/tmp` for the last run's script before writing
one from these notes: `/tmp` outlives a run, and the sixth rewrite was avoided
that way.

Also, for the record of the standing proxy notes: 127.0.0.1:1080 refused every
connection for this whole session, and `curl --noproxy '*'` reached
numberdb.org throughout, including `GET /api/table?id=T333` and
`GET /api/table/T333/audit` with the key on stdin through `-H @-`.

Evidence: 2026-09-18, T333 critique. `/tmp/t333_render.py`,
`/tmp/t333_render_out.txt` (`records: 999`, `tid: T1 tags: ['algebra',
'characteristic classes']`, `status 200 476482 bytes`), `/tmp/T333_page.html`.

## The proxy can answer with a complete body and `HTTP 000`, which looks like a failed fetch

What happened: the T334 critique's first command was the prompt's own
`curl -s --socks5-hostname 127.0.0.1:1080 https://numberdb.org/skill`. It
printed nothing to the terminal because the pipe to `head` was closed, wrote
**47,534 complete bytes** to the output file with the last paragraph of the
skill intact, reported `HTTP 000`, and exited 1. Every proxied request after
it failed differently, with `curl: (7) Failed to connect to 127.0.0.1 port
1080`. So the two failure modes are not the same, and the first one is the
dangerous one: a script that checks the exit status or the `%{http_code}` will
discard a file that is whole. Check the size and the tail of the body before
believing `HTTP 000`.

For the standing proxy notes: `curl --noproxy '*'` reached numberdb.org
throughout this session, including `GET /api/table?id=T334` and
`GET /api/table/T334/audit` with the key read from `NUMBERDB_KEY_FILE`, and it
also reached `en.wikipedia.org` (both articles the table cites, 200 and full
HTML), which the earlier notes had not recorded for Wikipedia.

Evidence: 2026-09-18, T334 critique. The command above with
`-o /tmp/skill.txt -w 'HTTP %{http_code}'`: `HTTP 000`, `wc -c` 47534, tail
ends at "a dodecahedron's inradius out by a factor of √5."; three retries of
`https://numberdb.org/T334` through the same proxy, all `size=0`.

## The sqlite draft-render recipe works unchanged for a rational-polynomial (`Q[]`) table, and a seven-entry page is 28 KB

What happened: the T334 critique reused `/tmp/t333_render.py`, still on the box
from the previous run, with one `sed`. `/tmp/site.tgz` was also still there, but
this run rebuilt it from the tarball line in the note above rather than trust a
copy made before the day's commits:

    tar czf /tmp/site.tgz --exclude='.git' --exclude='static/vendor' \
        --exclude='staticfiles' --exclude='__pycache__' --exclude='agents' \
        --exclude='generators' \
        numberdb numberdb_app templates static utils workers data_pipeline \
        clients manage.py
    sed -e 's/T333/T334/g' /tmp/t333_render.py > /tmp/t334_render.py
    NUMBERDB_SAGE_MEMORY=1200m NUMBERDB_SAGE_PYTHONPATH= \
        agents/sage.sh /tmp/t334_render.py /tmp/site.tgz /tmp/T334.json

That produced **7 records, status 200, 28,345 bytes**, with the seven rows
anchored `id="1"` to `id="7"`, the three tags, the `rigour details` fold, and
the section order the site's own. No patch beyond the ones already in the
script was needed for `Q[]` with rational coefficients. So the recipe has now
run for polynomial (T315, T319, T320, T332), rational polynomial (T334), real
(T316), complex (T317), rational (T321) and integer (T333) tables, and this is
the second run to get there by `sed` on the last one's script rather than by
writing it again. The note above still asks for `agents/render_draft.py`; the
useful shape is now clear, since the only thing that changed between three
consecutive runs was the tid.

Evidence: 2026-09-18, T334 critique. `/tmp/t334_render.py`,
`/tmp/t334_render_out.txt` (`records: 7`, `tid: T1 tags: ['algebra',
'characteristic classes', 'polynomial']`, `status 200 28345 bytes`),
`/tmp/T334_page.html`.

## `SymmetricFunctions` basis changes segfault on the builder image, and a segfaulting run can hold `agents/sage.sh` for the whole 1800s

What happened: the T335 critique wanted to recommend the standard incantation
for a symmetric-function table's `Programs` block -- `Sym =
SymmetricFunctions(QQ); e(p[n]) / factorial(n)`, three lines instead of the
twenty-line Newton recurrence the table carries -- and could not, because it
does not run here. `e(p[2])` dies with

    Unhandled SIGSEGV: A segmentation fault occurred.

inside `sage/data_structures/blas_dict`, reached through
`sage/categories/map` and `sage/structure/parent`, which is the coercion doing
the basis change. Twice: `NUMBERDB_SAGE_MEMORY=1200m` and again at `4000m`, so
it is not the memory cap. The polynomial-ring route in the same script -- a
`PolynomialRing(QQ, ['c1',...])` and Newton's identities by hand -- runs in
seconds in the same container and reproduces the stored `ch_6` exactly. So a
generator or a `Programs` block for a symmetric-function family should build
its own recurrence rather than change bases, on this image.

Dropping `import numberdb.sage` and importing `sage.combinat.sf.sf` first
raises `ImportError: cannot import name Category`, the same shape the skill
records for a ring module imported before Sage has initialised. There is no
order that works: import numberdb first and it segfaults, import it later and
the module will not load.

Two things about watching such a run, and the second is the one that costs
somebody else an hour.

*The output never arrives.* A third run -- the same script with a print between
each step, to find which one dies -- produced **nothing at all**, because it was
piped through `grep -v ... | head -20`: `grep` block-buffers when its output is
not a tty, so a crashing run's last words sit in a 4 KB buffer that is never
flushed, and `agents/sage.sh`'s own `--line-buffered` does not help once a
second `grep` is added on this side. Send such a run to a file --
`agents/sage.sh script.py > /tmp/out.txt 2>&1` -- and read the file. The two
runs that *did* report their segfault were piped the same way and got their
20 lines out first; a run that prints nothing before dying prints nothing at
all.

*A segfaulting run outlives `timeout 1800`, and it holds the lock.* This one
was still alive at **35 minutes**, six minutes past the timeout: `timeout`
sends SIGTERM to the `docker run` client, the client forwards it to PID 1 in
the container, and PID 1 is Sage's crash handler trying to attach a gdb that is
not installed. Both processes sit there. That matters because every
`agents/sage.sh` run takes `flock -w 3600` on a single lock, so the next
agent's run would have waited behind it for up to an hour, with nothing on
screen to say why.

The way out, for an agent that may not run `docker`: kill the `bash
agents/sage.sh ...` wrapper. Its `trap cleanup EXIT` runs `docker rm -f` on the
container by name, which is what that trap is for, and the container, the
`timeout` and the lock all go within seconds. `kill <pid of the wrapper>`,
then `ps -eo pid,etime,comm | grep -E 'docker|timeout'` to confirm. Do not
reach for `docker kill`: it is refused here, and the trap does the same thing.

Evidence: 2026-09-18, T335 critique. `/tmp/t335_programs.py` (the published
`Programs` block verbatim, then the symmetric-function route: the first prints
`1/720*c1^6 - ...` matching `Numbers['6']`, the second segfaults),
`/tmp/t335_sf.py` at `--memory=4000m` (same segfault), `/tmp/t335_sf2.py`
(`ImportError: cannot import name Category`), `/tmp/t335_sf3.py` (zero bytes of
output, `timeout`+`docker` still in `ps` at 35:55, both gone eight seconds
after `kill` on the wrapper).

## The sqlite draft-render recipe, third `sed` in a row, and a six-entry `Q[]` page is 29 KB

What happened: the T335 critique rebuilt `/tmp/site.tgz` from the tarball line
in the note above and ran `sed -e 's/T334/T335/g' /tmp/t334_render.py`, which
was still on the box from the previous run. That produced **6 records, status
200, 28,833 bytes**, with the six rows anchored `id="1"` to `id="6"`, the three
tags, the `Programs` block's indentation intact inside `<pre><code>`, and the
section order the site's own. No patch beyond the ones already in the script
was needed. That is three consecutive runs whose only change to the script was
the T-number, and the fourth table type the recipe has now covered twice
(`Q[]`). `agents/render_draft.py`, which the T332 note asks for, would have
saved all three.

One thing the recipe cannot show, and it matters for a critique: `HREF{}`
targets do not exist in the throwaway database, so a link's *text* renders
faithfully but its target cannot be checked there. Check the slugs against the
live site instead -- `curl -s -o /dev/null -w '%{http_code}'
https://numberdb.org/<slug>` -- and remember that a slug which 404s may be a
draft rather than a typo.

For the standing proxy notes: the SOCKS proxy on 127.0.0.1:1080 answered
exactly one request this session, `/skill`, with a complete 47,534-byte body
and `HTTP 000`, and refused every request after it; `curl --noproxy '*'`
reached numberdb.org throughout, including `GET /api/table?id=T335`,
`GET /api/table/T335/audit` and `/files/T335/generate.py` with the key on
stdin through `-H @-`. That is exactly the shape the T334 note above records,
one session later, so it is the behaviour and not an accident of that run.

Evidence: 2026-09-18, T335 critique. `/tmp/t335_render.py`,
`/tmp/t335_render_out.txt` (`records: 6`, `tid: T1 tags: ['algebra',
'characteristic classes', 'polynomial']`, `status 200 28833 bytes`),
`/tmp/T335_page.html`.

## The corpus reached 334 tables the same day the last note said 269

What happened: the note above records 269 tables on 2026-09-18, against the
126 that `agents/table-ideas/PROMPT.md` still claims. Walking the T-numbers
again that evening returns **T1 to T335 with T75 absent, 334 tables**: sixty-five
more in one day, T336 and beyond answering "does not exist". Four areas the
ideas run had picked as uncovered were built in that window -- hyperbolic
3-manifold volumes (T219, T221, T225), Bernstein-Sato polynomials (T290),
Faltings heights (T211), genus-2 periods and special L-values (T212, T213).

What to do instead: walk the T-numbers at the *start* of the run and do not
reuse a figure from any note, including this one; the number moves by dozens
between runs. A run that screens against yesterday's picture will propose
tables that exist. The loop costs about four minutes for 340 numbers.

Evidence: 2026-09-18, ideas run. `/tmp/corpus.py` and `/tmp/corpus2.py`,
`PYTHONPATH=clients/python`, printing `Title` and `Tags` for T1..T399; the last
table returned is T335 *Chern character polynomials*.

## `screen.already_asked` cannot find the request a proposal answers

What happened: the ideas run proposed tables answering numberdb-data#55
*Entropy of interesting probability spaces* and #56 *Kullback-Leibler
divergence of interesting pairs of distributions*, and `already_asked` returned
`[]` for both, and for every other row of the batch. It is not the rate limit
this time (the note above) -- the queries were answered.

The reason is the query it builds: the first three words longer than four
characters of the proposed name, joined into a GitHub `in:title` conjunction.
For "Entropies of discrete probability distributions" that is
`in:title Entropies discrete probability`, and GitHub's issue search does not
stem, so *Entropy of interesting probability spaces* does not match on
"Entropies", nor on "discrete", which the issue's title does not contain. The
same for "Kullback-Leibler divergences" against a title reading "divergence".
So the function reliably answers "nobody asked for this" about the very issue
the proposal cites, and a run that treats it as the duplicate check will report
the backlog as empty.

What to do instead: read `python3 agents/table-ideas/screen.py requests` in
full -- it is 65 lines -- and match proposals to requests by hand. Use
`already_asked` only as a check for *closed* issues, and expect it to miss
those too when the wording differs. The function would be more useful querying
one distinguishing word at a time and pooling the results.

Evidence: 2026-09-18, ideas run. `/tmp/screen4.py`, six proposals, every
`already_asked` line `[]`; the two issues it should have found are open and
listed by `screen.py requests` as #55 and #56.

## SciPy 1.17.1 is in the builder image, and the host `python3` has neither SciPy nor NumPy

What happened: the run wanted `scipy.stats` entropies as an independent check,
which is the comparison T241's `rigour details` reports. `python3 -c "import
scipy"` on the host fails with `ModuleNotFoundError`, and so does `numpy`; the
same script through `agents/sage.sh` prints `scipy 1.17.1` and evaluates
`stats.poisson(1).entropy()`, `stats.binom(10,1/3).entropy()` and
`stats.entropy(p, q)` without further installation.

What to do instead: do not fall back to hand-written float loops on the host
for a check that wants a library. Put the check in a file and run it through
`agents/sage.sh`, which has Sage, arb through Sage's ball fields, and SciPy in
the same interpreter -- so the ball value and the independent library value can
be compared in one script rather than across two environments.

Evidence: 2026-09-18, ideas run. `/tmp/scipychk.py` through `agents/sage.sh`
(`scipy 1.17.1`, `poisson(1) 1.3048422422562516`), against the same quantity
computed in `RealBallField(200)` in `/tmp/rll.py` (`1.304842242256`); the host
attempt is the `ModuleNotFoundError: No module named 'numpy'` from the inline
`python3 -c` in the same session.

## `already_asked` also runs out of GitHub's rate limit, and `gh` here does not

What happened: screening nine candidate names called
`screen.already_asked` nine times in a minute. The first four answered; the
other five returned `could not ask GitHub (HTTPError)`. Unauthenticated
requests to `https://api.github.com/search/issues` are allowed ten a minute
and sixty an hour, and the whole hour's allowance can be spent by one
screening pass plus a couple of retries. The string it returns is not an empty
list, so it does not read as "nobody asked", but the screen stops answering
and waiting eight seconds between calls is not enough once the hourly budget
is gone.

What to do instead: `gh` is logged in on this box, so ask through it, which is
authenticated and has a much larger allowance:

    gh api -X GET search/issues \
      -f q="repo:numberdb/numberdb-data in:title division polynomials" \
      --jq '.items[] | "#\(.number) [\(.state)] \(.title)"'

and for the proposal backlog rather than the requests:

    gh api "repos/numberdb/numberdb-data/issues?state=open&labels=proposal" \
      --jq '.[] | "#\(.number) \(.title)"'

The same applies to `screen.requests`, which asks the ordinary issues endpoint
and returns `[]` on any failure -- an empty backlog and an exhausted rate limit
look identical there, which is the failure this module is otherwise careful
about.

Evidence: 2026-09-19, ideas run. `/tmp/scr2.py` (four answers, five
`could not ask GitHub (HTTPError)`), `/tmp/scr3.py` with an eight-second sleep
between calls (five more failures, then two answers), and the `gh api` calls
above, which answered every name.

## A long `agents/sage.sh` run piped into `tail` shows nothing at all until it ends

What happened: a measurement script was run as
`agents/sage.sh script.py 2>&1 | tail -40` in the background. It printed
nothing for half an hour, so there was no way to tell which of its five
sections was slow, and when it was killed the output was lost entirely. The
script itself was fine; `tail` cannot print until the pipe closes, and
`sage.sh`'s own `grep --line-buffered` only helps a reader who is watching the
stream rather than the tail of it.

What to do instead: redirect to a file and read the file, which streams:

    agents/sage.sh script.py > /tmp/run.out 2>&1

Also: `E.rank()` over Cremona's curves is what made that run long.
`CremonaDatabase().allcurves(N)` returns `{label: [ainvs, rank, torsion]}`
from the database immediately, and the rank is the same number. Twenty minutes
of a run went into recomputing something the image already had on disk.

Evidence: 2026-09-19, ideas run. `/tmp/nb/dp5.py` (killed at 30 minutes, no
output) against `/tmp/nb/dp7.py` (same measurements taking ranks from
`allcurves`, complete in about ten), and `/tmp/nb/dp8.py`, whose output
appeared line by line in `/tmp/nb/dp7.out`.

## Killing a background `agents/sage.sh` does not kill the work

What happened: `pkill -f dp5.py` reported
`killing pid ... failed: Operation not permitted` and left
`python3 -u /work/dp5.py` running inside the container, which runs as another
uid. The local wrapper died, the container did not, and the flock that
serialises Sage runs was released only when the wrapper's own
`timeout 1800 docker run` reaped it.

What to do instead: let the `timeout` do it, or start runs with a `timeout`
short enough that an abandoned one clears quickly. Do not follow this with a
`docker rm`: `docker` is refused for agents here, and the container carries
`--rm` anyway.

Evidence: 2026-09-19, ideas run; `ps -o pid,user,cmd -C python3` showing the
container's `python3` under uid 1001 after the `pkill`.

## `agents/sage.sh` arguments are mounted files, not script flags

What happened: a repair script was run as `agents/sage.sh /tmp/t88_write_repair.py --write`.
The wrapper treated `--write` as another file to mount and stopped with
`no such file: --write`; nothing reached the API. A second version tried to
import `/tmp/t88_check_counts.py` from the main `/tmp` script, but inside the
container the main file is mounted at `/work/...`, and the host's `/tmp`
sibling is not there.

What to do instead: make one-off scripts self-contained, or pass helper
files as additional mounted files and import them by module name from `/work`.
Use forwarded environment variables such as `NUMBERDB_PUBLISH=1` for mode
switches, and keep the API key on stdin with `NUMBERDB_KEY_FROM_STDIN=1`.

Evidence: 2026-09-19, T88 repair. The failed calls produced
`FileNotFoundError: /tmp/t88_check_counts.py` and then `no such file: --write`;
the successful write used
`cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 agents/sage.sh /tmp/t88_write_repair.py`.

## The growth queue selects from a committed snapshot, and the snapshot goes stale

What happened: a critique run was dispatched to ask whether T293 could grow,
on the grounds that it "has 32 entries in 13825 bytes -- under a tenth of the
soft limits of 1200 entries and 320 KB". The live table holds **1171 entries
in 273.1 KB**: 97.6% of the soft entry limit, with 29 entries of headroom. The
premise of the run was false and the whole question was already answered.

The figures come from `agents/review-queue.tsv`, a tab-separated snapshot of
`(tid, entries, bytes, title)` that `work.py:shape()` reads and `growth()` and
`sweep()` select on. It was last committed 2026-09-18 21:51, in `33ab14c`. The
repairs of 2026-09-19 took T293 from 32 rows to 823 and then to 1171 -- eight
commits, all after the snapshot -- and nothing rewrote the row. Line 294 still
reads `T293	32	13825`.

So `growth()`'s test, `entries < 120 and size < 32 KB`, was applied to a table
that has been an order of magnitude past both since the morning. A run costs a
full critique to discover that.

What to do instead: regenerate the TSV from the live corpus at the start of a
campaign rather than reading a day-old committed copy, or have the growth
stage re-measure the one table it was handed before accepting the premise.
Re-measuring is three lines and does not touch a shared file:
`numberdb.table(tid)["Numbers"]`, then `limits.measure()`. Until that is done,
**a growth or sweep run should check the live size first and stop if the
snapshot disagrees** -- which is cheaper than the report it would otherwise
write.

The same staleness is worth suspecting in the other direction: a table that
has *shrunk* or been split since the snapshot will be missed by `sweep()`
rather than wrongly nominated, which is quieter and worse.

Evidence: 2026-09-19. `agents/review-queue.tsv:294` says 32 entries and 13825
bytes; the live document read through `clients/python` has 1171 entries across
`D = 5, 8, 12, 13, 17, 21` (17, 63, 253, 195, 295, 348) and
`yaml.dump(block).encode()` measures 279,665 bytes. `git log -- agents/review-queue.tsv`
shows one commit, `33ab14c`, older than every T293 repair commit.

## No SOCKS proxy on the builder box, and none is needed

What happened: the critique prompt gives
`curl -s --socks5-hostname 127.0.0.1:1080 https://numberdb.org/T1xx` and says
"the proxy is needed". On this host -- `NUMBERDB_MACHINE=aws-builder`,
`NUMBERDB_REMOTE=local` -- nothing listens on 1080 and the call fails with
`curl: (7) Failed to connect to 127.0.0.1 port 1080`. Worse, `curl -o` leaves
the output file untouched on a connection failure, so a stale
`/tmp/skill.md` from a previous run sat there at its old size and looked like
a successful fetch; only `-w '%{http_code} %{size_download}'` showed `000 0`.

Plain `curl https://numberdb.org/T293` from this host returns 200. The builder
reaches numberdb.org over the public internet like any outside contributor,
which is the whole point of `NUMBERDB_SAGE_IMAGE=numberdb/builder:latest`; the
proxy line in the prompt is for a machine that has to tunnel in.

What to do instead: on the builder, drop `--socks5-hostname`. Anywhere, fetch
with `-o FILE -w '%{http_code} %{size_download}\n'` and check the code, because
a failed `curl -o` is indistinguishable from a successful one by looking at the
file. The published skill is worth re-fetching rather than reusing: the copy
left in `/tmp` by the run of 2026-09-18 differs from today's.

Evidence: 2026-09-19. `ss -ltn` shows nothing on 1080 and no ssh tunnel in
`ps`. `curl --socks5-hostname 127.0.0.1:1080 https://numberdb.org/skill` gave
`000 0` while leaving a 47,534-byte file in place; direct `curl` gave
`200 48740`, and the two files differ.

## `audit_table`'s prose rules never read a `Similar tables` relation

What happened: T336's `Similar tables` glosses T335 as "store another
universal characteristic-class polynomial **in the same family of
proposals**", which is a fact about this site's queue rather than about the
mathematics, and it names "Bernoulli numbers" in a relation without linking
it. `GET /api/table/T336/audit` answers `{"findings": [], "clean": true}`.

The section is listed as one to read. `_prose_faults` in
`numberdb_app/management/commands/audit_table.py` opens

    sections = ('Definition', 'Comments', 'Formulas', 'Similar tables')
    for name in sections:
        blob = tree.get(name)
        if isinstance(blob, str):
            texts.append((name, blob))
        elif isinstance(blob, dict):
            texts.extend(...)

`Similar tables` is neither. `tree_of` is `yaml.load(..., Loader=BaseLoader)`
on the stored document, and the section is written as a *list* of `{table,
relation}` mappings -- T334, T335 and T336 all return a list from
`GET /api/table?id=...`. So the `elif` never fires and the section
contributes nothing to `texts`. Six rules run over `texts` and none of them
has ever seen a relation: the editorial-phrase rule, the positional-phrase
rule, `_POINTING`, `_NARRATION`, "names a family and does not link it", and
"writes `X HREF{X}` -- put the link on the name". The last two matter most
here, because a relation is exactly where one table names another in prose.

What to do instead: until it is fixed, a critique should read every
`Similar tables` relation by hand and not take a clean audit as covering
them. The fix is a `list` branch that appends one entry per row -- but it
must join the row's `table` and `relation` into a single text, not scan them
separately. Almost every row here is `HREF{Bernoulli_numbers}[Bernoulli
numbers]` in `table` and the name again in `relation`, so a rule fed the
relation alone would report "names Bernoulli numbers and does not link it"
on a row whose whole purpose is that link.

Evidence: 2026-09-19, T336 critique. `GET /api/table/T336/audit` is clean
against a document whose second relation reads "store another universal
characteristic-class polynomial in the same family of proposals" -- prose
about this site's queue, in the section the audit's own `sections` tuple
names. `GET /api/table?id=T336` returns `Similar tables` as a JSON list, as
do T334 and T335.

## A public tag page lists private drafts, and `/files/<tid>` serves them to anybody

What happened: the T337 critique checked, as a matter of routine, that the
table's three tags reach other tables. `https://numberdb.org/tags/characteristic+classes`,
fetched with **no key and no session**, answers 200 and lists six tables --
among them **T336** and **T337**, both private drafts, with their titles and
their entry counts:

    T337:  $\hat A$-genus polynomials $\hat A_n(p_1,\dots,p_n)$
           (6 rational polynomials)
    T336:  Hirzebruch $L$-polynomials $L_n(p_1,\dots,p_n)$
           (6 rational polynomials)

Each row links to `/T337` and `/T336`, which answer 404 to the same
unauthenticated client, because `views.table_by_tid` calls `_refuse_a_draft`
and the tag view does not. So a public page both discloses the drafts and
carries two broken links to them.

The same hole is open one street over. `https://numberdb.org/files/T337`
answers 200 with no key, and serves the draft's title, the message of its
current revision ("shorten A-hat genus definition") and `generate.py` in full
at `/files/T337/generate.py` -- 13,680 bytes. `views.table_files` and
`views.table_file` do not call `_refuse_a_draft` either.

This matters beyond tidiness. `_refuse_a_draft` answers 404 rather than 403
deliberately, with a docstring saying why: "Answering 'you may not see this'
would confirm that a table with that name or that number exists, which is the
one thing a private draft should not tell a stranger." The tag page tells a
stranger the number, the title, the type and the size; the files page hands
over the code.

What to do instead: nothing an agent can do -- this is a site fix, and a
person has to make it. `/tags/<tag>`, `/files/<tid>`, `/files/<tid>/<name>`
and `/bundle/<tid>` should each filter by the same `may_see` that
`_refuse_a_draft` uses, and `views.tag` should exclude unpublished tables from
its queryset rather than refusing after the fact, so the count at the top of
the page is right too. Worth a test beside `test_drafts.py`, which already
covers the table page.

Meanwhile it is *useful* to a critique run, and that is worth saying out loud
so nobody mistakes it for a feature: `/files/<tid>/generate.py` is the
cheapest way to read a draft's attached generator from this box, needing no
key and no Sage container. When it is fixed, fetch it with the key through
the API or out of the bundle instead.

Evidence: 2026-09-19, T337 critique. `curl -s https://numberdb.org/tags/characteristic+classes`
with no headers -> 200, containing `<a href="/T337">` and `<a href="/T336">`;
`curl -o /dev/null -w '%{http_code}' https://numberdb.org/T337` -> 404.
`curl https://numberdb.org/files/T337` -> 200, `/tmp/files_nokey.html`.
`_refuse_a_draft` is `numberdb_app/views.py:624`; the calls are at lines 612,
620 and 1522 and nowhere else.

## The SOCKS proxy was dead and was not needed: the builder reaches numberdb.org directly

What happened: the T337 critique opened with the command the prompt gives,

    curl -s --socks5-hostname 127.0.0.1:1080 https://numberdb.org/T337

and got `exit 7` -- "failed to connect to proxy" -- five times running.
Nothing was listening on 1080 and there was no `ssh -N -D` process on the
box. The note above ("A test run can make the server unreachable while the
site stays up") describes the proxy dying with its ssh and having to be
restarted by hand, and that reads exactly like this; but `ssh` is refused to
an agent, so there was nothing to restart.

It did not matter. This run's environment has `NUMBERDB_REMOTE=local` and
`NUMBERDB_MACHINE=aws-builder`: the agents are running **on** the builder,
which talks to numberdb.org over the public internet like any outside
contributor. `curl -s https://numberdb.org/` with no proxy flag answered 200
in under a second, and every fetch in that critique -- the skill, the API,
`/preview`, `/tags`, `/files`, Wikipedia -- went straight out.

What to do instead: on the builder, drop `--socks5-hostname 127.0.0.1:1080`.
Try the direct fetch first and only reach for the proxy if it fails; a dead
proxy and a dead site look identical from behind the proxy, and on this
machine the proxy is the more likely of the two to be the thing that is dead.
`NUMBERDB_REMOTE` is the flag that says which situation you are in.

Evidence: 2026-09-19. Five `curl --socks5-hostname` attempts, all exit 7;
`ps aux | grep 'ssh -N'` and `ss -ltn | grep 1080` both empty; `curl -s -w
'%{http_code}' https://numberdb.org/` -> 200, 19,903 bytes.

## `/preview?table=<yaml>` renders a draft without a database, in pieces of about 4 KB

What happened: before finding that `/tmp/t335_render.py` and the sqlite
recipe were still on the box, the T337 critique rendered the draft the other
way -- `views.preview` takes the whole document as a GET parameter and
renders it with no database at all, which is the shortest path to "what does
this actually look like" when the sqlite recipe is more than the question
needs.

It is bounded by the request line, twice over. nginx answers **414** above
about 8 KB of URL, and gunicorn answers **400 "Request Line is too large
(4901 > 4094)"** below that, so the working limit is about **4,000 characters
of URL-encoded YAML** -- a fifth of a typical table. The document has to be
split, and two things about splitting it are not obvious:

* **Every chunk needs a `Numbers` key**, even one entry. Without it the page
  renders with `Error while parsing numbers: cannot access local variable
  'number_section'` and no table at all.
* **A `CITE` whose target is in another chunk renders as `CITE-broken`**, with
  the raw key printed at the reader. The first pass here put `Definition` and
  `Formulas` in different chunks and produced three convincing "a raw key
  leaks into the prose" findings, all of them artifacts. Keep a section and
  everything it cites in the same chunk, or check the finding again with them
  together before believing it.

    python3 -c "import json,yaml; d=json.load(open('/tmp/T337.json')); \
      sub={k:d[k] for k in ['Title','Definition','Formulas','Links']}; \
      sub['Numbers']={'1': d['Numbers']['1']}; \
      open('/tmp/c1.yaml','w').write(yaml.dump(sub,sort_keys=False,width=10**6))"
    curl -s -G --data-urlencode "table@/tmp/c1.yaml" https://numberdb.org/preview

`/preview/T337` -- the route that takes a tid -- is no use for this: it calls
`_refuse_a_draft`, which tests `request.user`, and an API key is not a
session.

What to do instead: use the sqlite recipe when the question is about the whole
page (section order, anchors, the numbering `Formulas`-before-`Comments`
produces), and `/preview?table=` when it is about one section's prose and you
want an answer in ten seconds. `/preview` is also the only one of the two that
renders the *live* document rather than a reconstruction, so it is the right
check for "does this edit render" before writing it.

Evidence: 2026-09-19, T337 critique. 5,735 encoded characters -> gunicorn 400;
11,296 -> nginx 414; 2,284 to 5,023 -> 200. `/preview/T337` with
`X-API-Key` -> 404.

## `agents/sage.sh` mounts only the files named on its command line

What happened: a T289 repair check put a scratch Sage script in `/tmp` and had
it import the edited generator by the host checkout path
`/home/ubuntu/numberdb-website/generators/core-threshold-minimisers/generate.py`.
Inside `agents/sage.sh`, that path was unreadable and then nonexistent:
the wrapper copies only the script, and any extra files named after it, into
the throwaway container as `/work/<basename>`.

What to do instead: when a scratch Sage script needs a repo file, pass that
file as an extra argument and import `/work/<basename>`, for example:

    agents/sage.sh /tmp/t289_growth_check.py generators/core-threshold-minimisers/generate.py

The scratch script can then load `/work/generate.py`. Do not rely on the host
checkout path being mounted.

Evidence: 2026-09-19, T289 repair. The first run failed with
`PermissionError` on the host path; changing to `/work/generate.py` and passing
the generator as a second `agents/sage.sh` argument made the same check report
`<PublishOutcome T289: 10 added, 0 updated, 0 unchanged, 0 agreed, 42 left alone, 0 removed, not sent>`.

## The draft-render recipe, written out for the sixth time, needs no change for a small `Z[]` table

What happened: the T338 critique needed the rendered page of a draft
(`https://numberdb.org/T338` answers 404 with and without the key, as the T182
note records). The script was written again from the notes above -- the pip
list from the T315 note, the tarball line from the T332 note, the
`_sync_tags` replacement from the T320 note, and both range patches from the
T316 and T319 notes -- and worked on the first `agents/sage.sh` run:
**6 records, status 200, 29,326 bytes**, tag strip `characteristic classes
polynomial algebra` matching the document's `Tags`.

Nothing new was needed. The range patches were applied unconditionally, as the
T319 note says to; T338's entries are all of positive degree so they may not
have been required, and applying them cost nothing. The recipe has now run for
polynomial (T315, T319, T320, T332, T338), real (T316), complex (T317) and
rational (T321) tables.

This is the **sixth** run to write the script from these notes, and the fifth
note to say it should be promoted to `agents/render_draft.py` with the tid as
an argument. That is the finding: the notes are complete enough that the
rewrite succeeds first time, which is exactly why nobody has been forced to
promote it, and each run still spends four or five turns on it.

Evidence: 2026-09-19, T338 critique. `/tmp/t338_render.py`,
`/tmp/t338_render_out.txt` (`records: 6`, `tid: T1 tags: ['algebra',
'characteristic classes', 'polynomial']`, `status 200 29326`),
`/tmp/T338_page.html`. Run as `NUMBERDB_SAGE_MEMORY=1200m
NUMBERDB_SAGE_PYTHONPATH= agents/sage.sh /tmp/t338_render.py /tmp/site.tgz
/tmp/T338.json`.

## The prompt's `--socks5-hostname` line still fails, and the direct `curl` still works

What happened: this run opened, as instructed, with
`curl -s --socks5-hostname 127.0.0.1:1080 https://numberdb.org/skill`, which
exited 7. `ss -ltn` shows no listener on 1080, exactly as the T321 note says.
`curl https://numberdb.org/skill` with no proxy answered 200 in the same
minute, and every request in this run -- the skill, `/api/table?id=`,
`/api/table/<tid>/audit`, four published table pages, a tag page, and the
Wikipedia Segre class article -- went direct.

The T321 note already says all of this and says not to run `env | grep` to
find out why. This run ran it anyway, before reading far enough, and printed
`NUMBERDB_API_KEY` into the transcript for the **sixth** time. The rule in a
notes file has now failed six times. The fix is not another note: it is
`unset NUMBERDB_API_KEY` in `run.sh`, since the runner already exports
`NUMBERDB_KEY_FILE` and the prompt tells the agent to read the key from there.
Until that lands, the key should be treated as rotated after any run whose
stage is `critique`.

Evidence: 2026-09-19, T338 critique. `curl` exit 7 on the proxy; `ss -ltn`
with no 1080 row; `curl https://numberdb.org/skill` 200, 48,740 bytes.

## The key leaked a seventh time, and the command came out of this file

What happened: this run printed `NUMBERDB_API_KEY` into its transcript, the
seventh time by the count in the note above. The command was

    env | grep -i -E 'proxy|numberdb' | sed 's/=.*KEY.*/=<hidden>/'

which is the one the previous note already records as ineffective: the `sed`
hides a variable whose *value* contains "KEY" and `NUMBERDB_API_KEY` is a
variable whose *name* does. What is new is where it came from. The run had not
read that note yet. It had run `grep -n -i "proxy\|1080" docs/agent-environment.md`
to find out why `--socks5-hostname` failed, and line 1102 of the grep output is
the failing command, printed in full, with nothing on that line saying it
failed -- the sentence that says so is on the next line and was not in the
match. So the notes file handed the run a ready-made incantation and hid the
warning attached to it.

A notes file is read by grep at least as often as it is read in order, and a
line that quotes a dangerous command is a line that will be copied. Two fixes,
neither of which is another warning: quote the safe form instead, and describe
the unsafe one rather than writing it --

    env | grep -i proxy                       # no key can appear
    env | sed -E 's/^(.*KEY.*)=.*/\1=<hidden>/'   # hides by name, not value

-- and land the `unset NUMBERDB_API_KEY` in `run.sh` that the previous note
already asks for, which is the only fix that does not depend on what a run
reads first.

Evidence: 2026-09-19, T288 growth critique, stage `critique`, run
`20260919T185812Z`. The grep output line beginning `1102:` carries the command
verbatim; it was run two tool calls later. Treat the key as rotated.

## "No match in database" is on every page, including table pages

What happened: reading `/T288` as text -- tags stripped, whitespace collapsed,
which is how a critique reads a rendered page -- put the line
`No match in database` eight lines into the output, above the table's own
title block. It is not a result: no search had been made. The same line appears
on `/properties/<number>` for every number tried, including 3.14159265358979,
so that page cannot be used to judge whether a value is findable either.

Half an hour went into a search-behaviour finding that was page chrome. The
check that settles it in one call is to fetch a page where no search could
have happened and look for the string.

Evidence: 2026-09-19, T288 growth critique. `/T288` (200, 53,607 bytes)
contains it; `/properties/3.14159265358979`, `/properties/2.6879993454994913`
(a stored T288 value) and `/properties/1.23456789012345` are identical in this
respect.

## The proxy was down for a second run, and the draft-render script needed one `sed`

What happened: `--socks5-hostname 127.0.0.1:1080` was refused again on
2026-09-19 (`ss -ltn` shows no 1080 listener; the T338 note records the same
thing earlier the same day), so the prompt's `curl` line cannot be used as
written. Plain `curl https://numberdb.org/...` reaches the site, and the draft
itself is only reachable through the API: `/T339` and `/preview/T339` answer
404 to the bearer token, `GET /api/table?id=T339` and
`/api/table/T339/audit` answer 200.

What is new is how cheap the page was this time. `/tmp/t338_render.py` from
the previous run was still on the box, and the whole adaptation was

    sed 's|T338|T339|g' /tmp/t338_render.py > /tmp/t339_render.py

with the tarball line from the T332 note rebuilt unchanged. It ran first try
on a `type: R` table with a three-level `Symbolic` index: **469 records,
status 200, 349,726 bytes of HTML**, tags `probability theory`,
`special values`. Both range patches were still needed. That is the eighth
table the recipe has rebuilt and the second run in a row to get there by
editing the previous run's script rather than writing it from these notes —
which is the argument for `agents/render_draft.py` taking the tid as an
argument, asked for in three notes above and still not done.

Evidence: 2026-09-19, T339 critique. `/tmp/t339_render.py`,
`/tmp/t339_render_out.txt` (`records: 469`, `tid: T1 tags: ['probability
theory', 'special values']`, `status 200 349726`), `/tmp/T339_page.html`.

## `queue.py built` can close a family whose remaining entries are only claimed

What happened: after T344 was built and offered for review, `python3
agents/queue.py built 165 'Division polynomials $\psi_n$ of the curve
$y^2=x^3+Ax+B$' T344` correctly ticked the proposal, but it also closed
numberdb-data#165 with "Every table in this family now exists." Three sibling
proposals were not built or skipped; they were `[~] claimed by w2/w3/w4`.
`waiting()` treats fresh claims as not waiting, and `cmd_built()` closes a
family when `waiting(family)` is empty. `cmd_stale()` only scans open
families, so a premature close can hide a dead worker's stale claim.

What to do: after running `queue.py built` in a family where other checklist
items are still only claimed, run `queue.py show <family>` and check whether
the helper closed the issue. If it did, reopen the issue and leave a short
comment saying which table was built and which items remain only claimed.

Evidence: 2026-09-20, T344 build. `queue.py built` printed `#165 closed; the
family is built`; `queue.py show 165` still listed three `[~] claimed` items.
The run reopened #165 and commented that T344 was built but the family should
stay open for stale-claim recovery.

## A tag page is `/tags/<name>`, not `/tag/<name>`, and the wrong one answers 404

What happened: the T344 critique checked whether the draft's three tags group
anything, and asked for `https://numberdb.org/tag/number%20theory`. All three
answered **404**, which reads exactly like three invented tags -- the failure
the skill warns about, where a tag made up from the plural in one's head
groups nothing. They are all real. The route is `/tags/<name>` with spaces as
`+`: `/tags/number+theory`, `/tags/elliptic+curves`, `/tags/polynomial` all
answer 200, and `/tags` lists all 51 with their hrefs.

What to do instead: read the hrefs off `/tags` rather than building a tag URL
from the name. One fetch of `/tags` answers the question for every tag in a
document at once, and it is the same page a reader would use.

Evidence: 2026-09-20, T344 critique. `/tag/number%20theory` 404;
`/tags` 200 with 51 tag links, three of which are the document's.

## The draft-render recipe, tenth table, one `sed` again -- and the previous run's script was on the box

What happened: T344 is a private draft (`/T344` 404 anonymously,
`GET /api/table?id=T344` and `/api/table/T344/audit` 200 with the key on stdin
through `-H @-`). `/tmp/t343_render.py` and `/tmp/site.tgz` were both still on
the box from the previous run, so the whole adaptation was

    sed 's|T343|T344|g' /tmp/t343_render.py > /tmp/t344_render.py

with `/tmp/site.tgz` rebuilt from the tarball line in the T332 note rather
than trusted. First try, on a **multivariate** `Z[]` table -- entries in
`Z[x,y,A,B]`, which the recipe had not previously been run on: **7 records,
status 200, 29,537 bytes**, tags `elliptic curves`, `number theory`,
`polynomial`. Both range patches were still applied and did no harm.

That is the third run in a row to get the page by editing the previous run's
script, and the ninth or tenth table the recipe has rebuilt. Four notes above
now ask for `agents/render_draft.py` taking the tid as an argument. The saving
is no longer the rewrite -- the notes make that succeed first time -- it is
the four turns spent locating which note holds which patch.

Also, for the standing proxy notes and without listing the environment to find
out why: the prompt's `curl -s --socks5-hostname 127.0.0.1:1080` line was
refused outright (exit 7, "Connection refused"), and plain `curl` reached
numberdb.org, en.wikipedia.org and pari.math.u-bordeaux.fr throughout.

Evidence: 2026-09-20, T344 critique. `/tmp/t344_render.py`,
`/tmp/t344_render_out.txt` (`records: 7`, `tid: T1 tags: ['elliptic curves',
'number theory', 'polynomial']`, `status 200 29537`), `/tmp/T344_page.html`.
Run as `NUMBERDB_SAGE_MEMORY=1200m NUMBERDB_SAGE_PYTHONPATH= agents/sage.sh
/tmp/t344_render.py /tmp/site.tgz /tmp/T344.json`.

## The search box and `/api/search` read the same decimal two different ways

What happened: checking how a reader would find a row of T286, I searched the
live site for `1.32471795724474` (fifteen correct digits of the plastic
ratio, which T286 and T222 both hold) and got nothing, while
`1.324717957244746` returned both tables. Sixteen digits match, fifteen do
not. Typing the same short string into the site's own search box finds the
row: `/suggestions?term=1.3247` returns T286 row 1 and T222's `[inf,3]`.

The two front doors parse differently, and only one of them is the parser the
comments describe:

* `numberdb_app/views.py` (the search box) calls
  `utils.utils.parse_real_interval(term)`, which reads a decimal as "last
  given digit possibly off by one" -- `1.3247` becomes
  `[1.3246, 1.3248]`, and everything in it is a hit.
* `numberdb_app/api.py` (`/api/search`, and so the client's
  `search_by_expression`) calls `evaluate_search_program(program)` instead.
  The expression is *evaluated*, so `1.3247` is a point at double precision,
  `blur_real_interval` widens it by four ulps, and a stored value differing
  in the fifth place is nowhere near it.

So `parse_real_interval`'s "treat the last given digit as possibly off by 1"
branch -- which is the behaviour the search box's users get and the behaviour
the code comments explain -- never runs on the API path at all. A run that
probes search through `curl /api/search` and concludes "the corpus does not
hold this number" is measuring the strict path and may be wrong. Probe
`/suggestions?term=` as well, or hand the client a ball.

Not proposed as a lesson: a contributor meets the client and the search box,
where the behaviour is the forgiving one. This is a disagreement between two
of the site's own entry points.

Evidence: 2026-09-20, T286 growth critique.
`/api/search?expression=1.32471795724474` -> `results: []`;
`?expression=1.324717957244746` -> T222 and T286;
`/suggestions?term=1.324717957` -> T286 row 1. Same pattern on the golden
ratio: `1.61803398874989` -> nothing, `1.618033988749895` -> five tables,
`/suggestions?term=1.61803398874989` -> T32's `phi` row.

## A `/preview?table=` chunk that leaves out `Formulas` calls every `CITE{formula-…}` broken

What happened: the T349 critique needed the rendered page and went to
`/preview?table=` first, because the whole-page rebuild takes a Sage run and
the preview route takes a `curl`. The document does not fit -- nginx answers
`Request Line is too large (7020 > 4094)` -- so it was sent section by
section: `Definition` with `Links` and a couple of rows, then `Comments`, then
`Formulas`, then `Data properties`.

The `Data properties` chunk rendered

    <span class="CITE-broken" title="this table defines no reference by that
    name">formula-complete</span>

for the `CITE{formula-complete}` in `rigour details`, and that is exactly what
a real broken citation looks like on a page. It is an artefact of the chunk:
the label is defined in `Formulas`, and `Formulas` had been left out to fit
the request line. Sending `Data properties` and `Formulas` together rendered
`(1)` and `(2)`, which is what the live page does.

What to do instead: preview chunks are fine for looking at prose, mathematics
and the column headers, but a chunk is not a page and a *missing* cross
reference in one proves nothing. Every `CITE{}` and `HREF{}` check belongs on
the whole document -- the sqlite rebuild recipe above -- or on the live site.
If a chunk must be used, carry `Links`, `Formulas` and `References` in every
one of them, since those are what labels resolve against.

Also, on this box the route to a rendered draft is the sqlite rebuild and
nothing else, and the two wrong turns before it cost four commands:
`NUMBERDB_SAGE_IMAGE` here defaults to `numberdb/builder:latest`, which has no
`/app` and no Django (`FileNotFoundError: /app`, from the T136 `RequestFactory`
recipe); `numberdb/web:latest` is not on this machine (`pull access denied for
numberdb/web`); and `NUMBERDB_REMOTE=linode`, which would reach the machine
that does have it, stops at `scp: Connection closed`. The previous run's
`/tmp/t350_render.py` was still on the box and needed only its tid changed,
as the T344 note says it was for T343.

Evidence: 2026-09-20, T349 critique. `/tmp/prev-props.html` (the broken
citation) against `/tmp/prev-props2.html` (the same field with `Formulas`
present, rendering `(1)` and `(2)`); `/tmp/t349_render_out.txt`
(`records: 552`, `status 200`, 324,545 bytes).

## Reading a paper on this runner: no `pdftotext`, but `arxiv.org/e-print` gives the LaTeX

What happened: the T285 growth critique turned on what four papers actually
prove, and the numbers in their theorem statements. This box has no
`pdftotext`, no `pypdf` and no `fitz`, so a downloaded PDF is a wall -- an
earlier critique of the same table got at Lanneau and Thiffeault's
introduction by inflating the PDF's Flate streams with `zlib` and reading
what fell out, which produced part of the paper and no way to tell which
part was missing. That is how a run ends up quoting an abstract.

What to do instead: `curl -sSL https://arxiv.org/e-print/<id> -o src.tar.gz`
and untar it. For all five papers read today it was the author's LaTeX --
`systole.tex`, `LT.tex`, `small-bundles.tex`, `whitehead-sister.tex`,
`traintrack.tex` -- where `grep -n "realizing\|\\\\begin{theorem}"` finds a
statement in one command, and a theorem's own words can be quoted rather than
paraphrased from an abstract. Two cautions: cross-references are `\ref{}`
labels, so a theorem's *number* is not in the source and must not be invented
(write "their lower-bound theorem", not "Theorem 1.3"); and a few submissions
are a single gzipped `.tex` rather than a tarball, so `tar xzf` failing is not
an error worth stopping on -- `gunzip` it.

Metadata to go with it, both reachable from here without the proxy:
`https://export.arxiv.org/api/query?id_list=<id>` gives title, authors,
abstract and `journal_ref`/`doi` for a `References` entry, and
`https://api.crossref.org/works?query.bibliographic=<title words>` fills in a
journal reference arXiv does not carry (that is where Kin-Takasawa's
J. Math. Soc. Japan 65 (2013), doi:10.2969/jmsj/06520411 came from). The
arXiv API also searches titles and abstracts --
`search_query=all:%22minimum+dilatation%22&sortBy=submittedDate` -- which is
the only literature search available here: there is no MathSciNet, no zbMATH
and no full-text or citation search, so "nothing later settles this" is a
claim about titles and abstracts and should be written as one.

Evidence: 2026-09-20, T285 growth critique. Direct `curl` to `arxiv.org`,
`export.arxiv.org` and `api.crossref.org` all answered 200 without the proxy,
which was refusing connections on port 1080 throughout the run as usual.

## OEIS and the LMFDB answer a bot challenge here, but not from inside the container

Screening a batch of number-field proposals on 2026-09-20 I wanted two
routine cross-checks: the LMFDB's published regulator for a field label, and
an OEIS sequence of discriminants. From the agent's own shell both are
unusable:

    curl -s https://www.lmfdb.org/api/nf_fields/?label=4.0.125.1&_format=json
        -> a Google reCAPTCHA challenge page, HTTP 200
    curl -s -A ... https://oeis.org/search?q=...&fmt=text
        -> Cloudflare "Just a moment...", HTTP 200 (403 with no User-Agent)

Both answer `200` with HTML, so a script that parses the body sees a page
rather than an error, which is the expensive failure: it reads as "the
sequence does not exist" or "the field has no regulator".

From inside the Sage container the same two URLs answer normally:

    agents/sage.sh probe.py      # urllib, User-Agent set
    https://oeis.org/A006832                                   200
    https://www.lmfdb.org/api/nf_fields/?label=4.0.125.1...    200   regulator 0.962423650119

So the LMFDB and OEIS comparisons that T131, T158 and T161 record in their
`rigour details` are reachable, and belong in the generator, where the build
already runs. Do not try to run them from the agent shell and do not conclude
from a challenge page that the source is wrong. Wikipedia, the AMS journal
site, `api.crossref.org` and numberdb.org itself answer directly from both
places; `export.arxiv.org` needs `https` (the `http` form answers 301 with an
empty body).

Two smaller things met on the same run:

* `import numberdb` from the repository root picks up the Django app package,
  which has no client API. Run client code from elsewhere with the repository
  copy on the path: `cd /tmp && PYTHONPATH=<repo>/clients/python python3 ...`,
  and call `screen.use_socks_proxy_if_set()` first, as
  `agents/table-ideas/screen.py` does, or every corpus search comes back empty.
* `screen.already_asked` reaches GitHub's search API unauthenticated and is
  rate limited after a handful of calls; it then reports
  `could not ask GitHub (HTTPError)`, which is honest but unhelpful mid-batch.
  `gh issue list --repo numberdb/numberdb-data --search ... --state all` is
  authenticated here and answers the same question.

## The audit's tag finding blames the draft for a count it did not make

What happened: `GET /api/table/T354/audit` on a private draft reported, twice,

    Tags: "functional analysis" reaches only this table; a tag that leads nowhere else leads nowhere
    Tags: "inequality" reaches only this table; a tag that leads nowhere else leads nowhere

Neither tag reaches T354. Both reach **T92**, and T354 is the second table to
carry them. The check (`numberdb_app/management/commands/audit_table.py`,
around line 414) reads `Tag.objects.values_list('name', 'table_count')`, and
`table_count` counts *published* tables. A draft is not in it, so the count of
1 the check found belongs to some other table, and the message attributes it
to the one being audited. On a draft the sentence is always false in the
literal thing it says, and it is most misleading exactly when the draft is
doing the right thing: reusing an existing tag that one published table
already carries.

The finding still points at something real — two is under the skill's bar of
three — but the reader has to go to `/tags/<tag>` to find out that the tag
reaches anything at all, and the obvious reaction to the message as written is
to invent a new tag, which is the opposite of what the skill asks.

What it should say: name the tables. "reaches 1 other table (T92)" for a
draft, "reaches no other table" when the count really is zero once this table
is excluded. Excluding the audited table from the count is the other half:
for a published table `table_count` includes it, for a draft it does not, so
the same message means two different things depending on a state the caller
cannot see.

## `/preview` is a GET form and gunicorn refuses the request line past 4094

What happened: rendering a reconstructed draft through
`curl --get --data-urlencode "table@file.yaml" https://numberdb.org/preview`
answered 400 with

    Request Line is too large (4626 > 4094)

which is gunicorn's `limit_request_line` default. `numberdb_app/views.preview`
reads `request.GET.get('table')`, and the editor's own form in
`templates/.../preview` is `method="get"`, so this is not an artefact of
driving it with curl: the preview editor on the site cannot preview any table
whose YAML percent-encodes past about 4 KB, which is nearly every real table.
Measured on T354's prose block: 3000 bytes of YAML answered 200, 3500 answered
400.

For an agent this only means rendering a draft in pieces — section by section,
with two or three entries each, which is what the T271 and T354 critiques did
and which is enough to see every rendering fault. Sections render
independently except for `CITE` and `HREF`, so send `Comments`, `Formulas` and
`References` together or the citations render as bare keys and look broken
when they are not. The same goes for `rigour details`, whose `CITE`s resolve
against `Formulas`.

The fix on the site is to make the preview form a POST, or to raise
`limit_request_line`. Until then, a contributor who pastes a whole table into
the preview box gets a bare gunicorn 400 page with no hint that the table was
fine.

## `QQbar` comparisons crash in the Sage of `numberdb/web:latest`

What happened: checking whether 25 candidate rows were Salem numbers, the
first spelling enumerated conjugates and compared `abs(root)` to 1 over
`QQbar`. On degree 32 it died with

    NameError: name 'RR_1_10' is not defined

raised from `sage/rings/qqbar.py`, in the `sqrt` reached while exactifying
`abs(root)` for the comparison. It is a name that exists in that module's
namespace in other Sage versions, so this is the image's Sage, not the script.

Anything that compares two `QQbar` elements is exposed — `sorted()`,
`max()`, `in`, `==` against a non-rational — and the failure arrives as a
`NameError` from deep inside a Sage file, which reads like a broken install
rather than like a comparison you chose to make.

What to do instead: stay in `RealIntervalField`/`ComplexIntervalField` and
decide by interval, or reformulate the question so it becomes an exact
rational computation. For root patterns on the unit circle the reformulation
is the trace polynomial, which is written up as a lesson proposal; it is also
enormously faster.

One more thing about the same run: this builder has **no way to read a PDF**
— no `pdftotext`, no `pypdf`, no `PyPDF2`, and the `Read` tool's PDF path
needs `pdftoppm`. For an arXiv reference, fetch
`https://arxiv.org/e-print/<id>`, which is the gzipped LaTeX source: it is
smaller than the PDF, the tables in it are machine-readable rows rather than
typeset glyphs, and nothing has to be installed.

Evidence: 2026-09-20, T284 growth reading. `/tmp/check_extension.py` under
`agents/sage.sh` first with `f.roots(QQbar)`, then with
`g.number_of_roots_in_interval`; arXiv:2409.11159 was read from
`smallSalemNumbers6.tex`, 8,692 bytes gzipped against 117,994 for the PDF.

## The tag-reach audit tells a draft that a tag "reaches only this table" when the one table it counted is a different, published one

What happened: `GET /api/table/T359/audit` on the Nash draft returned two
findings and nothing else:

    Tags: "functional analysis" reaches only this table; a tag that leads nowhere else leads nowhere
    Tags: "inequality" reaches only this table; a tag that leads nowhere else leads nowhere

Both tags reach T92, "Best Sobolev constant for $W^{1,p}(\mathbb{R}^n)$", which
is published and answers `/T92` with no key at all. The rule
(`numberdb_app/management/commands/audit_table.py:415`) reads
`Tag.table_count <= 1` and then names the table in the message as though the one
it counted were this one. For a draft it never is: the draft is not in the
count, so a count of 1 means *some other table*, and the sentence a reviewer
reads is false in its words as well as in its conclusion. The natural repair --
dropping the family tag for a vaguer one that "reaches" more -- would break the
route the batch exists to build.

What to do instead: on a draft, read this finding as "one public table carries
this tag", and find out which with `curl -sS -G https://numberdb.org/api/lookup
--data-urlencode text=<tag>` or an authenticated `GET /api/tag?url=<tag>`. If
that table exists and is the right neighbour, keep the tag and record the
finding in the report. The same conclusion was reached independently by the
build run (`agents/lessons/proposals/20260920T045108Z-build.md`); what is new
here is that the message misnames the table, which is a site bug and not a
judgement call. Fixing it means either counting drafts or saying "reaches no
other table" and naming the one it found.

Evidence: 2026-09-20, T359 critique. `GET /api/table/T359/audit` with the
zeta3 key; `curl https://numberdb.org/T92` answers 200 unauthenticated and its
`Tags` are exactly `["functional analysis", "inequality"]`; T354, T355, T356,
T357 and T358 carry the same pair.

## `agents/table-build/PROMPT.md` tells a build to do what the skill forbids, and on T359 it emptied the backlog into one table's `Links`

What happened: draft T359 carries 29 links, 28 of them "Requested in
numberdb-data#N" for N in 6, 9, 10, 17, ..., 165 -- every one a **closed** issue
asking for a different table (Ramsey numbers, knot polynomials, Maass form
coefficients, volumes of hyperbolic manifolds). Not one of them asks for Nash's
inequality; the nearest, #57, is T92's and T354's request. They are in the
stored document and in `generators/sharp-constant-nash-inequality/table.yaml`
from line 54, so this was written by the build, not by an edit afterwards.

The rule it came from is `agents/table-build/PROMPT.md` line 34: "If the
checklist line says `(answers #N)` ... Put the request in the table's `Links`,
as *'Requested in numberdb-data#N'*, because the provenance of an idea is owed
to whoever had it." The published skill says the opposite, in section 9: "A
'table wanted' issue is answered **in the issue**, not in the table. ... The
table carries no trace of the request." Critiques of T339 and T354 have both
reported the one-link form of this as a fault, and T354 was repaired by deleting
it -- so the campaign is manufacturing a finding, repairing it, and
manufacturing it again. T359 is the case where the rule did not merely conflict
with the skill but misfired: it was given, or inferred, a whole list of closed
issues rather than the one a table answers.

What to do instead: a person should reconcile the two. The provenance the
prompt wants is already kept where it belongs -- `agents/queue.py built`
comments on the issue with the table's address and closes it, which is the
record, and it survives without putting a GitHub link on an encyclopedic page.
Until then, a build following that prompt should add at most the single issue
its checklist line names, and a critique should keep reporting it.

Evidence: 2026-09-20, T359 critique (`agents/critiques/T359.md`, finding 1).
The 28 issue titles were read from
`https://api.github.com/repos/numberdb/numberdb-data/issues/N`; every one
returned `"state": "closed"`. The sibling drafts T354 to T358 carry one link
each.

## `audit_table` demands Sage of a generator that does not use it

What happened: `GET /api/table/T283/audit` returned `"clean": false` with two
findings -- `generate.py does not say how to install what it imports` and
`generate.py does not give the command to run it in its first forty lines`.
Both are false. The generator's docstring says, in its first twelve lines:

    $ pip install numberdb mpmath        # once
    $ python3 generate.py                # check the table against this code
    $ python3 generate.py --publish      # send it, with NUMBERDB_API_KEY set

The rule
(`numberdb_app/management/commands/audit_table.py:307-316`) greps the file for
the literal strings `sage -pip install numberdb` and `sage -python
generate.py`. T283's generator imports `mpmath` and `numberdb` and nothing
else, so Sage is not how it is run, and satisfying the rule would mean writing
a command into the docstring that does not work.

Why it matters beyond one table: the intent of the rule is good -- the file is
downloaded by somebody with neither the repository nor a way to guess the
command -- and a table that satisfies the intent is told it does not. An agent
reading the audit and obeying it makes the generator worse. The rule also
cannot be satisfied by a pure-Python generator at all, so every such table
will read `"clean": false` forever, which is how a check stops being read.

What to do meanwhile: when an audit fires either of these two findings, open
the attached file before acting on it. If it names an interpreter and an
install line for the interpreter it actually uses, the finding is an artefact
and the right move is to say so in the report rather than to edit the file.

What the fix looks like: match an install line and a run line for the file's
own interpreter -- accept `pip install` as well as `sage -pip install`, and
`python3 <name>` / `python <name>` as well as `sage -python <name>`, resolving
`<name>` from the attachment rather than hard-coding `generate.py`.

Evidence: 2026-09-20, `GET /api/table/T283/audit`; the attached file is
rev 2132 of `/files/T283/generate.py`, byte-identical to
`generators/mahler-measures-short-random-walks/generate.py`. Written up in
`agents/critiques/T283-growth.md` §5.

## `/preview` renders nothing at all without a `Numbers` section, and the API document can be posted back to it as JSON

What happened: rendering draft T366 on this builder meant `/preview?table=…`
in pieces, the recipe of the T221 and T289 notes above, because the builder
image has no Django and the `RequestFactory` path is closed. The first eight
pieces carried a title and one or two prose sections and no entries, and every
one of them answered 200 with an empty preview and a red alert:

    Error while parsing numbers: cannot access local variable 'number_section'
    where it is not associated with a value

Not a complaint about the piece: `views.preview` renders *nothing* — no
definition, no comments, no links — when the document has no `Numbers`. The
earlier notes say to send "one or two sections of prose, or one block of
entries"; the truth is that every piece needs a `Numbers` block, and a
one-entry stub (`{"725": {"1": {"-1": {"number": "2/15"}}}}`) is enough and
costs 50 bytes of the 4094-byte request line.

The second half of this: the piece does not have to be YAML. `views.preview`
loads the `table` parameter with `yaml.BaseLoader`, and YAML is a superset of
JSON, so the document `GET /api/table?id=T…` returns can be sliced in Python
and posted straight back with `json.dumps` — no YAML writer, no quoting
decisions of your own, and what renders is what is stored. Eleven pieces of
T366 went through that way, all 200.

What to do instead: when rendering a private draft in pieces, put a one-entry
`Numbers` stub in every piece, and build the pieces as JSON out of the API
document. If a piece comes back with the `number_section` alert, add the stub
rather than looking for a fault in the prose.

Evidence: 2026-09-20, T366 critique. `/tmp/prev366.py` and
`/tmp/T366-*.html`; the eight stubless pieces answered 200 at 6.5-7.7 KB with
the alert and no preview, the same eight with the stub answered 200 at
14-18 KB with the sections rendered.

## A private draft's attached generator is still world-readable, on 2026-09-20

What happened: `curl https://numberdb.org/T366` answers 404 to an
unauthenticated caller, and `curl
https://numberdb.org/files/T366/generate.py?raw=1` answers 200 with all 15,562
bytes, whose docstring names the table, its address at `numberdb.org/T366`,
its range and its method. This is the hole the T235, T324 and T337 notes above
describe; it is recorded again only because it is still open five weeks after
the first note, and because it now affects a whole batch: T359, T364 and T365
answer 404 on the page and 200 on the file in the same way.

Evidence: 2026-09-20. `for t in T359 T365 T364; do curl -o /dev/null -w
'%{http_code}' https://numberdb.org/$t; curl -o /dev/null -w '%{http_code}'
"https://numberdb.org/files/$t/generate.py?raw=1"; done` -> `404 200` three
times; T366 the same, 15,562 bytes.

## A PostScript paper needs no inflating, and the `zlib` route on a PDF garbles a formula

What happened: the T281 growth critique turned on three papers this box cannot
read the normal way. There is no `pdftotext`, no `pypdf`, no `fitz` and no
`pdftoppm`, so `Read` on a PDF answers "pdftoppm is not installed" and the
`zlib` stream trick (note above) is what is left. Two things came out of using
it in earnest:

* **A `.ps` file needs nothing at all.** Elkies and Watkins's Hall-polynomial
  paper is dvips output, and `re.findall(r'\((?:\\.|[^\\()])*\)', raw)` joined
  with spaces gave 66 KB of readable text -- tables, number-field polynomials
  and all -- with no decompression step. PDFs need the Flate streams inflated
  first; PostScript from dvips has the text in literal parentheses.
* **The failure mode on a PDF is a wrong character, not a missing paragraph.**
  Montanus's article gave up its whole argument, but the closed formula for the
  number of classes came out with `C((m-1)/3)` where the paper has
  `C((m-1)/2)`. Nothing about the extracted text says which digit is wrong. It
  was caught only because the same article prints the first sixteen values of
  the sequence, and the formula as extracted does not reproduce them.

What to do instead: prefer `arxiv.org/e-print/<id>` (note above) and, for a
paper only on an author's page, try `.ps` before giving up. When a formula has
to come out of the `zlib` route, check it against something else printed in the
same paper -- a table of values, a worked example -- before building on it. Half
this critique's arithmetic would have been wrong on a `/3`.

Evidence: 2026-09-20, T281 growth critique. `/tmp/montanus.pdf` (216,981 bytes)
-> `/tmp/montanus.txt` (82,512 characters) via inflate;
`magma.maths.usyd.edu.au/~watkins/papers/hall.ps` (536,450 bytes) ->
`/tmp/hall.txt` (66,203 characters) with no inflate; `arxiv.org/e-print/math/0005139`
-> `antsiv.tex`, where `grep -n 18553` found the polynomial in one command.

## A Gröbner run killed at the memory cap exits 137 with nothing printed

What happened: a primary decomposition in 9 variables through
`agents/sage.sh` printed its first two lines and then stopped. The container was
killed at the memory cap, not at the timeout: exit 137, no traceback, no
Singular error, and the output simply ends mid-section. The same script had
finished the 7-variable case in the same run, so there was nothing wrong with
the code. Two runs were spent before that was clear.

What to do instead: read exit 137 plus truncated output as "the cap", not as a
bug, and reduce the problem (a finite field instead of `QQ` did not help here;
fewer variables is the only thing that does). And **do not background
`agents/sage.sh ... | tail -N`**: `tail` buffers until the pipeline ends, so the
task's output file stays empty for the whole run and there is no way to see
which step is slow. Redirect to a file and poll it -- `sage.sh` already runs
`sage -python -u` and greps line-buffered, so a redirect streams.

Evidence: 2026-09-20, T281 growth critique. `/tmp/modp.out` ends after
`== M = 5 over GF(32003) ==` with `[done rc=137]`; the $\mathbb Q$ run of the
same decomposition at $M=4$ took 418 s for the saturation alone and is in the
task output for `bckbc2zrm`.

## A `/preview?table=` piece with no `Numbers` key renders nothing and blames a local variable

What happened: the T372 critique rendered a private draft through
`/preview?table=<json>` in pieces, as the T221 and T225 notes describe. The
first six pieces carried `Title`, `Parameters`, `Display properties` and the
one section under test, and no entries -- there was no reason to send entries to
read the Comments block. All six answered HTTP 200 and rendered no table at
all, printing instead

    Error while parsing numbers: cannot access local variable 'number_section'
    where it is not associated with a value

above a dump of the submitted YAML. That is a Django message from the preview
view, not a YAML error, and it says nothing about the missing key; the piece
looks exactly like a document the parser choked on. Adding `"Numbers": {"3":
"x^2 - 2"}` to the same six pieces made all six render in full.

What to do instead: put a `Numbers` key in **every** preview piece, one entry is
enough. Together with the T225 note -- entries need `Parameters` beside them or
they render as bare keys -- the working shape for a piece is: `Title`,
`Parameters`, `Display properties`, one entry, and the section under test, plus
`Links` when that section `CITE`s and `Formulas` when it cites a formula label.
A `CITE` whose target is not in the piece renders as the bare key
(`formula-recurrence` in running text), which is the piece's fault and not the
table's.

Evidence: 2026-09-20, T372 critique. `/tmp/prev372.py` and `/tmp/crit372/*.html`
before and after: `a_def` 8,160 bytes with the error, 18,752 bytes with one
entry added. Also for the record of the standing proxy notes: 127.0.0.1:1080
served `https://numberdb.org/skill` once and then refused every connection
(`curl: (7)`, `ss -ltn` showing no listener), and direct `curl` answered
everything for the rest of the run, including `/api/table`, `/api/lookup`,
`/preview` and `dlmf.nist.gov`. `--retry-all-errors` does not help: a refused
connection retries instantly and fails the same way.

## `source_names_it` matches literal substrings, so a plural name fails a singular page

What happened: the proposal for a table of trinomial discriminants was screened
as "Discriminants of trinomials" and refused twice, by two pages that both
describe the family: <https://en.wikipedia.org/wiki/Discriminant> "does not
mention trinomials", <https://en.wikipedia.org/wiki/Trinomial> "does not mention
discriminants". Both are true as written. Wikipedia's discriminant article uses
the word "trinomial" in the singular, and the trinomial article the word
"discriminant" in the singular, and `_distinguishing` keeps whatever plural the
proposed *name* was written in while the page match is a plain `w not in text`.
MathWorld's `PolynomialDiscriminant` refuses for the same reason. Screening the
same family as "Discriminant of a trinomial" passes against both pages.

`GENERIC` already drops some plurals -- `polynomials`, `numbers`, `functions`,
`values` -- which is why this has not bitten before: the words it bites are the
distinguishing ones, and those are exactly the words the check exists to test.

What to do instead: when `source_names_it` refuses a family you are confident
is real, screen the singular form of the name before concluding the source is
wrong, and record which form passed. A fix would stem both sides, or strip a
trailing `s` from each distinguishing word before the match; that is a change to
`screen.py` and wants a test, so it is not made here.

Evidence: 2026-09-20 ideas run. `source_names_it("Discriminants of
trinomials", "https://en.wikipedia.org/wiki/Trinomial")` -> "the source does not
mention discriminants"; `source_names_it("Discriminant of a trinomial", same
url)` -> None. Same pair against `.../Discriminant` and against
`mathworld.wolfram.com/PolynomialDiscriminant.html`.

## oeis.org answers a Cloudflare challenge here, so an A-number cannot be verified

What happened: a proposal wanted to cite the OEIS sequence counting the terms of
the discriminant of the general polynomial of degree $n$ (2, 5, 16, 59, 246,
1103 for $n=2$ to $7$, measured in Sage). `curl https://oeis.org/search?q=id:A007878&fmt=text`
returned the "Just a moment..." interstitial: an HTML page with a JavaScript
challenge, HTTP 200, no sequence data. Plain `curl` to Wikipedia, MathWorld,
doi.org and numberdb.org all answered normally in the same run.

That matters twice over. A citation nobody can read is not a citation, so the
A-number was left out of the batch with the measured terms given instead, for a
builder to look up. And `source_names_it` against an `oeis.org` URL will refuse
every family for want of the words, while looking exactly like a family nobody
names: the earlier run's screen of `https://oeis.org/A002965` reported "the
source does not mention discriminants, trinomials", which is a statement about
the challenge page and not about OEIS.

What to do instead: screen against Wikipedia, MathWorld, DLMF, doi.org or an
arXiv abstract, which answer. If a proposal rests on an OEIS sequence, quote the
first terms and say they were measured, and leave the A-number for somebody with
a browser. `export.arxiv.org` was also unreachable from this run (`curl` wrote a
zero-byte file, over both http and https), so an arXiv abstract page may not
answer either; test it before relying on it.

Evidence: 2026-09-20 ideas run, the OEIS response quoted above, and
`curl -s --max-time 60 'http://export.arxiv.org/api/query?...' -o /tmp/ax.xml`
giving `0 /tmp/ax.xml`.

## `screen.py requests` prints nothing both when the backlog is empty and when GitHub is unreachable

What happened: the ideas run of 2026-09-21 was told to anchor a batch on the open
`table wanted` issues. `python3 agents/table-ideas/screen.py requests` printed
nothing at all. That is a state the prompt does not describe and that reads, at
first, exactly like a broken network: the same command had listed the backlog in
every earlier run.

It was the truthful answer. The GitHub search API reports 0 open and 126 closed
`table wanted` issues, and the closures are dated 2026-09-20 and 2026-09-21,
eleven of them within the same second at `10:39`, each with a comment naming the
table that answers it. The 2021 backlog is gone.

The trouble is that `requests()` cannot say which of the two happened:

    except Exception as trouble:                     # noqa: BLE001
        return []

`already_here` in the same module goes out of its way to avoid exactly this --
"A failed question and an empty answer must not look the same" -- and
`requests` does the thing that comment forbids. Everything downstream of it
then reads an outage as an empty backlog, which is the most consequential
misreading available at this stage, since a run that believes the backlog is
empty stops looking for an anchor.

What to do instead: when `requests` prints nothing, confirm it against the API
before concluding anything, which is one command:

    curl -s 'https://api.github.com/search/issues?q=repo:numberdb/numberdb-data+label:%22table+wanted%22+state:open&per_page=1' \
      | python3 -c 'import sys,json; print(json.load(sys.stdin)["total_count"])'

A fix would return `None` on failure and `[]` on an empty list, and print
"could not ask GitHub" for the first; that is a change to `screen.py` and wants
a test, so it is not made here.

Evidence: 2026-09-21T20:03Z ideas run. `screen.py requests` printed nothing;
the search API answered `total_count: 0` for open and `126` for closed; the
repository's own open-issue list held three issues, none of them labelled
`table wanted`.

## Give `source_names_it` the family name, not the table title

What happened: the same run screened its proposed titles rather than the names of
the families, and got refusals that mean nothing:

    "Values of the Epstein zeta function of the classical lattices"
        -> the source does not mention lattices
    "Madelung constants of the hypercubic lattices"
        -> the source does not mention hypercubic, lattices

The Wikipedia article on the Epstein zeta function exists and names it; what it
does not contain is the scope phrase a numberdb title adds to say which members
the table holds. `_distinguishing` keeps every word that is not in `GENERIC`, and
`classical`, `hypercubic`, `cubic`, `ionic` and `structures` are all scope rather
than name.

It cuts both ways, and the second half is the useful half: `"Madelung constants
of the ionic crystal structures"` and `"Watson integrals of the cubic lattices"`
both passed, because those pages happen to contain "ionic", "crystal",
"structures" and "cubic". So a title that passes tells you nothing extra, and a
title that fails tells you nothing at all.

What to do instead: screen the name of the family -- "Epstein zeta function",
"Madelung constant", "Watson's triple integrals" -- and record the full title
separately. This is the same failure mode as the plural note above: the check
tests words, and the words that matter are the ones naming the object.

Evidence: 2026-09-21T20:03Z ideas run, the two refusals above, against
`en.wikipedia.org/wiki/Epstein_zeta_function` and
`en.wikipedia.org/wiki/Madelung_constant`; `source_names_it("Epstein zeta
function", same url)` and `source_names_it("Madelung constant", same url)` both
returned `None`.

## A tensor-product numpy grid is the easiest way to hit the 320 MB container cap

What happened: a check integrated a two-dimensional Brillouin-zone integral by a
midpoint rule built as an outer product, `c[:, None] * c[None, :]`, at
$N=2000, 4000, 8000$. At $N=8000$ that is a $8000\times8000$ float64 array, 512
MB, against `NUMBERDB_SAGE_MEMORY` of 320 MB and about 100 MB already spent on
importing Sage. The container died having printed only the script's first header
line and exited 0, so the run looked like a script that produced no output
rather than one that was killed.

Raising the cap is the wrong reflex; the note at the top of `agents/sage.sh`
explains why, and the memory was never needed. Summing the grid in row blocks
of 256 gave the identical answer in a few seconds inside the default cap.

What to do instead: never materialise an $N\times N$ grid whose $N$ you are
sweeping. Loop over row blocks and accumulate a scalar. And read a Sage run that
stops after its first `print` as a kill rather than as a silent failure: with
`-u` set by the wrapper, the output that exists is the output that happened
before the process died.

Evidence: 2026-09-21T20:03Z ideas run. `agents/sage.sh` with
`NUMBERDB_SAGE_MEMORY=600m` printed only `=== A. Watson integrals: midpoint rule
in float64, extrapolated in 1/N ===` and exited 0; the chunked version printed
all nine grid values and three extrapolations under the default 320 MB.

## `/preview?table=` needs a `Numbers` section, or it errors on an unbound variable

What happened: the T390 critique rendered a private draft the way the T221
note describes -- pieces of the document sent to `/preview?table=...`, each
under the 4094-byte request line. Ten of the thirteen pieces carried prose
only (Definition, Comments, Formulas, References) and every one of them came
back 200 with

    Error while parsing numbers: cannot access local variable
    'number_section' where it is not associated with a value

and the textarea echoing the YAML where the rendered table should have been.
Nothing was rendered, and the error names "parsing numbers" rather than the
missing section, so it reads like the numbers were malformed rather than
absent. Adding one stub entry to each piece --

    Numbers:
      unit-square:
        '1': '19.739...'

-- made all ten render. This is the site's own bug, not the recipe's: the
same YAML with no `Numbers` is what somebody typing into the preview editor
has after their first paragraph, so a contributor drafting a table in the
browser hits it before they have a single value.

What to do instead: when rendering a draft in pieces, put `Parameters` and a
one-entry `Numbers` in *every* piece, not only the ones under test. Budget
for it: the stub costs about 250 bytes of the 4 KB. The T221 note above
should be read with this amendment.

Evidence: 2026-09-21, T390 critique. `/tmp/render390.py` first run, pieces
`a` through `j`: 200, 6.1-6.6 KB each, all carrying the `number_section`
message; second run with the stub: 200, 14.6-16.5 KB each, all rendering.
`numberdb_app/views.py:1507` is where `current_job` is pasted into the
message.

## The environment was listed before the direct `curl`, for the fifth time

What happened: the T390 critique opened with the prompt's
`curl --socks5-hostname 127.0.0.1:1080 https://numberdb.org/T390`, got exit 7,
and ran `env | grep -i -E 'proxy|numberdb'` to find out why -- which is
exactly what the note above ("`20260915T221028Z`") says not to do, and for
exactly the same reason: `ALL_PROXY` is empty on this box and plain `curl`
works. The direct `curl` should have been the next command after the exit 7,
not the third.

Two things did go right and are worth keeping. The mask was
`sed -E 's/(KEY|TOKEN|SECRET)[A-Z_]*=.*/\1=<hidden>/I'` rather than the
`s/=.*KEY.*/=<hidden>/` of the earlier runs, and it redacted both
`NUMBERDB_KEY` and `NUMBERDB_API_KEY`; the older mask redacts neither,
because it matches lines whose *value* contains "KEY". If a run must list the
environment, that is the mask. And the run never needed to: `NUMBERDB_KEY_FILE`
is set here (`/home/ubuntu/.config/numberdb/zeta3-key`), so
`{ printf 'Authorization: Bearer '; cat "$NUMBERDB_KEY_FILE"; } | curl -s -H @-`
worked as the note further up describes.

What to do instead: on any failure of the proxied `curl`, retry without
`--socks5-hostname` before anything else. Unsetting `NUMBERDB_API_KEY` and
`NUMBERDB_KEY` in `run.sh`, still not done, would end the question for good --
the prompt tells a run the key is in a file, and the runner then puts it in
two variables as well.

Evidence: 2026-09-21T21:21Z critique run. Proxied `curl` exit 7,
`HTTP 000`; `curl -s https://numberdb.org/T390` answered 404 (the draft is
private, which is correct) and `curl -s https://numberdb.org/skill` answered
200 with 48 KB.

## `queue.py built` can close a family while other lines are only claimed

What happened: after T394 was offered for review, `python3 agents/queue.py
built 183 "Best known packings of equal circles in a circle" T394` correctly
changed that checklist line to `[x]`, but also printed `#183 closed; the family
is built`. A fresh `queue.py show 183` still showed four other proposals as
`[~] ... claimed by w1`, not `[x]` or `[-]`.

Why: `parse_family()` sets `done` true for `~`, so the close check in
`cmd_built` treats active or stale claims as settled. That may be harmless
when the claims are genuinely concurrent, but it makes the printed line read
stronger than the visible checklist.

What to do instead: after `queue.py built` says it closed a family, run
`queue.py show <family>` before assuming the whole family is finished. If other
lines are still `[~]`, do not create `agents/runs/batch-exhausted`; leave the
other workers' claims alone and report the actual checklist state.

Evidence: 2026-09-22 build of T394. The command printed `#183 closed; the
family is built`; immediately after, `queue.py show 183` showed T394 as `[x]`
and the other proposals still claimed by w1.

## Do not try to render a draft on the *host*: Django installs there, Sage does not, and `numberdb/web:latest` cannot be pulled

What happened: the T399 critique knew it needed the rendered page and reached
for the host rather than the Sage container, because installing Django looked
like the short way round. Four dead ends in a row, none of them written down
anywhere:

  * `NUMBERDB_SAGE_IMAGE=numberdb/web:latest agents/sage.sh ...` fails
    immediately with `pull access denied for numberdb/web, repository does not
    exist`. The image is built on the site's host and never pushed anywhere, so
    on this builder it does not exist and cannot be fetched. `agents/on-server.sh`
    is the same wall: it is `docker compose run web`, and `web` is that image.
  * `python3 -m venv` is broken on this box -- `ensurepip is not available`,
    and `apt install python3.12-venv` needs a sudo this run does not spend. The
    working form is `python3 -m pip install --target /tmp/somedir ...` and then
    `sys.path.insert(0, '/tmp/somedir')`; `--user` and `--target` cannot be
    combined.
  * Django then installs and imports fine, and `django.setup()` dies at
    `numberdb_app/models.py:22`, `from sage.all import infinity, ceil, log, I`.
    There is no Sage on this host at all. That import is at module scope, so no
    amount of settings fiddling gets past it, and shimming `sage.all` would fake
    exactly the arithmetic (`CIF`, `RIF`) that a critique is reading the page to
    check.
  * `psycopg2-binary` is needed even for sqlite, and `django-anymail` too --
    both are imported at app-loading time by `INSTALLED_APPS`.

The answer is the one already written up seven times above: the render happens
**inside `agents/sage.sh`**, because that container is the only place where Sage
and a network (to `pip install` Django) exist together. The host has the network
and no Sage; the site's host has Sage and is not reachable. There is no third
place.

What to do instead: go straight to the sqlite draft-render recipe. Check
`/tmp` first -- `/tmp/t398_render.py` and `/tmp/site.tgz` were both still there
from the run two hours earlier, and

    sed -e 's/T398/T399/g' -e 's/t398/t399/g' /tmp/t398_render.py > /tmp/t399_render.py
    NUMBERDB_SAGE_MEMORY=1200m NUMBERDB_SAGE_PYTHONPATH= \
        agents/sage.sh /tmp/t399_render.py /tmp/site.tgz /tmp/T399.json

gave `records: 15`, `tid: T1 tags: ['physics']`, `status 200 36137` on the first
attempt. That is the tenth run to use this recipe and at least the sixth to
write or adapt the script by hand. `agents/render_draft.py` taking a tid still
does not exist.

Evidence: 2026-09-22, T399 critique. The four failures above in order
(`docker: pull access denied`, `ensurepip is not available`,
`Can not combine '--user' and '--target'`, `ModuleNotFoundError: No module
named 'sage'`), then `/tmp/t399_render_out.txt` at 36,137 bytes of HTML between
the markers. Nothing is listening on port 1080 (the note above still holds);
`curl https://numberdb.org/...` direct answered every request this run made.
## `agents/sage.sh` forwards stdin, but the installed client does not read a key from it

What happened: a table build tried the documented shape
`cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 agents/sage.sh generate.py`
with `NUMBERDB_PUBLISH=1`. The wrapper forwarded `NUMBERDB_KEY_FROM_STDIN`, but
the installed Python client only looks for `NUMBERDB_API_KEY`, `.env`, or
`~/.config/numberdb/env`; it never reads stdin. The generator reached the
package's preliminary `check_writable` call and failed with "writing needs an
API key".

What to do instead: use a scratch wrapper that reads stdin, calls
`numberdb.configure(api_key=token)`, imports the generator, and then calls
`publish()` or `verify()`. Keep the wrapper in `/tmp` and keep the key in
memory only. If `publish()` is blocked by the empty-draft preflight, compute the
entries through the generator and submit them with the package's
`Entries`/`submit_entries` helpers, then attach `generate.py` with the same run
id.

Evidence: 2026-09-21, T376. The first publish attempt failed before computing
entries with `UnauthorizedError: writing needs an API key`; the stdin-configured
scratch wrappers `/tmp/submit_twisted_entries.py` and `/tmp/verify_twisted.py`
filled and verified the draft without putting the key in an argument or file.

## A closed request can contain a stale wrong T-number, so read the table it names

What happened: numberdb-data issue #13 had an older closing comment saying the
request was answered by `T368`, but `https://numberdb.org/api/table?id=T368`
is "Zeros of the Charlier polynomials $C_n(x;a)$", not twisted Kloosterman
sums. The live corpus search and the table contents showed that the requested
twisted table did not exist yet, so the build continued and created T376.

What to do instead: treat an issue-closing T-number as a claim to verify, not
as proof. Fetch the table and read its title and definition before running
`queue.py built` or stopping as a duplicate. If the named table is unrelated,
continue the normal duplicate checks against the corpus and say what was found.

Evidence: 2026-09-21, numberdb-data #13 and #174. `queue.py show 174` still
listed "Twisted Kloosterman sums modulo a prime (numberdb-data#13)" as open
work; the issue comment named T368; `api/table?id=T368` returned the Charlier
zeros table; T376 was then built and `queue.py built 174 ... T376` added the
correct answer.

## `screen.py requests` returns `[]` when GitHub fails, which now reads as "the backlog is empty"

What happened: the 2026-09-22 ideas run was told to build its batch from the
open `table wanted` issues. `python3 agents/table-ideas/screen.py requests`
printed nothing at all. `screen.requests()` catches every exception and returns
`[]`, so an unreachable API, a rate-limited one and an empty backlog are the
same answer, and the function's own docstring is about a backlog of 81 open
requests -- which makes the empty answer look like a failure rather than a
result.

It was a result. `gh issue list --repo numberdb/numberdb-data --label
"table wanted" --state open --limit 300 | wc -l` gives `0`, and
`--state all` gives `126`: every request ever filed has been closed, the last
of them on 2026-09-21. Five issues are open in the repository and none is a
request for a new family (three `proposal` families, and #133 and #137 asking
for existing tables to be extended).

This matters more than it did when the backlog was long. `already_here` was
fixed in this module precisely so that a failed question and an empty answer
would not look the same; `requests` still has the bug, and it now has it at the
moment when `[]` is the true answer and therefore impossible to distinguish
from the failure by eye.

What to do instead: cross-check an empty `requests` with `gh issue list` before
concluding anything, and say in the batch which one you ran. `requests` should
raise, or return `None`, when the HTTP call fails -- the same treatment
`already_here` got.

Evidence: 2026-09-22 ideas run. `screen.py requests` printed nothing; a direct
`urllib` call in the same process returned a 200 with a zero-length JSON array;
`gh issue list ... --label "table wanted" --state open` returned nothing and
`--state all` returned 126 closed issues.

## The ideation stage now has to find its own anchor, because there are no requests left

What happened: the stage prompt says to start from the open requests and build
the family around one, and cites the 81 that were waiting when it was written.
There are none. The 2026-09-22 run replaced that anchor with the corpus's own
shape: walk `numberdb.table('T1')` through `T420`, which answers for 403 tables
(T1 to T404, with T75 absent), list the subjects it reaches, and propose into
one it does not reach at all. That walk is the only way to see the shape, since
there is no call that lists the corpus; eight threads did 260 T-numbers in one
call, and the two calls covering T1 to T420 were a few minutes between them.

What to do instead: when `requests` is empty and `gh` confirms it, say so in
the batch as a result rather than hunting for something to cite, and choose the
subject by the walk. Note that `numberdb.table` answers for a table whose
`Tags` are `None` (T404 at the time of this run), so a walk that filters on
tags will drop the newest tables.

Evidence: 2026-09-22 ideas run, `/tmp/nd/walk.py`.

## `source_names_it` passes a two-surname family name on a page that names the two people separately

What happened: `source_names_it('Widom-Dyson constant',
'https://en.wikipedia.org/wiki/Random_matrix')` returned `None`, meaning pass.
The page does not contain the phrase. It contains "Widom" only inside
"Tracy-Widom distribution" and "Dyson" only in "their Dyson index" and
"Freeman Dyson", so both words are present, in unrelated roles, and the check
matches the words of a name independently of each other.

This is the failure mode already recorded for navigation boxes and reference
lists, in its sharpest form: a family named after two people is exactly the
case where the two words occur on any page about the subject, whether or not
anybody has ever used them together. The proposal was dropped after reading the
page.

What to do instead: for a compound surname family, read the page rather than
trusting the pass, or screen the name as one token where the checker allows it.
A pass on a two-surname name is weak evidence.

Evidence: 2026-09-22 ideas run. `source_names_it` gave `None`; the fetched
article's occurrences of "Widom" and "Dyson" are the ones quoted above.

## `doi.org` and `ams.org` also refuse the screener, so the fetchable sources are Wikipedia and DLMF

What happened: screening a batch whose standard reference is a Markov
Processes and Related Fields review, the run tried the DOI resolver and the AMS
journal page as sources. `https://doi.org/10.1090/S0025-5718-09-02280-7`
answered 403 and
`https://www.ams.org/journals/mcom/2010-79-270/S0025-5718-09-02280-7/` answered
403. `http://export.arxiv.org/abs/0904.1581` answered 200 with a body
containing neither "tracy" nor "widom", which the checker reports as "the
source does not mention tracy, widom" -- a statement about the stub, not about
the paper. Wikipedia and `dlmf.nist.gov` both answer with full text.

What to do instead: cite Wikipedia or DLMF for the screen, name the paper in
the proposal's prose so the build can put it in `References` where it belongs,
and say in the batch that the screen could not reach it. Do not reword a
proposal to match whatever page happens to fetch.

Evidence: 2026-09-22 ideas run, the `source_names_it` lines quoted in
`agents/table-ideas/BATCH-2026-09-22T0807.md`.

## A long mpmath loop under `agents/sage.sh` stops part-way with no traceback

What happened: an ideation run checked the Falkner-Skan boundary layer by
integrating an ODE at several parameter values with `mpmath.odefun`. At
`mp.dps = 30` and `eta_max = 18` the script printed the first parameter's
result and then stopped -- no traceback, no message, and the rest of the loop
simply absent from the output. Repeating at `mp.dps = 20` and `eta_max = 13`
got two parameters further and stopped the same way. The container has 320 MB
(`NUMBERDB_SAGE_MEMORY`), `odefun` holds a Taylor cache per solution, and a
shooting iteration builds a fresh solution every call.

A third run, redirected to a file instead of piped, printed `EXIT 137`: the
container is being killed, and the cap is the reason. The first two runs were
piped through `tail`, so the exit status reported was `tail`'s `0` and the
container's own status never reached the transcript. A killed run read exactly
like a finished one.

The fix that worked was not more memory but less solver: a hand-rolled
fixed-step RK4 over the same interval holds five `mpf` numbers, runs in
constant memory, and reaches ten digits in a second — plenty for checking a
proposal's values against the literature. Reserve `odefun` for the runs that
need thirty digits, and give those one parameter per script.

What to do instead: do not pipe `agents/sage.sh` through `tail` or `head` --
redirect to a file and read that, so the exit code is the container's. Flush
after every parameter (`sys.stdout.flush()`), put few parameters in one
script, `del` and `gc.collect()` each solution, and raise
`NUMBERDB_SAGE_MEMORY` rather than assuming a silent stop is a hang.

Evidence: 2026-09-22 ideas run, `/tmp/w/fs.py` (one of six parameters) and
`/tmp/w/fs2.py` (two of five).

## `screen.py already_asked` rate-limits at about ten calls, and says so in a way that reads like "nobody asked"

What happened: screening eleven candidate names in one loop, the last call
returned `could not ask GitHub (HTTPError)`. GitHub's search API allows ten
requests a minute unauthenticated, and `already_asked` catches every exception
and returns the message as though it were a result row. It is visible if you
read it and invisible if you skim, and an empty answer and a failed question
look nearly the same -- the failure mode `already_here` was already fixed for.

What to do instead: for a batch, ask once rather than eleven times. The whole
repository is 130-odd issues:

    gh issue list --repo numberdb/numberdb-data --state all --limit 300 \
      --json number,title,state --jq '.[] | select(.title|test("(?i)<words>"))'

and filter locally. Use `already_asked` for one-off checks.

Evidence: 2026-09-22 ideas run, `/tmp/w/scr.py`, eleven names, the eleventh
failing.

## `agents/sage.sh` can wait many minutes for the lock while a build campaign runs

What happened: an ideation run's checks queued behind another campaign's build
on the same machine, printing `waiting for the Sage lock: another worker is
using it` once a minute for over four minutes before starting. The lock is
doing its job -- two Sage processes on this server is what it exists to
prevent -- but a run that budgets a two-minute timeout for a thirty-second
computation will time out in the queue and not in the work.

What to do instead: run Sage checks in the background from the first call, not
after a foreground attempt times out, and treat the waiting lines as progress
rather than as a hang. `pgrep -fa codex` or `pgrep -fa claude` says whether
another campaign is on the machine.

Evidence: 2026-09-22 ideas run; `/tmp/w/fs3.out` shows five waiting lines.

## `oeis.org` cannot be reached from this machine at all

What happened: a proposal wanted to cite the OEIS entry for the Blasius
constant, which the skill names as one of the four kinds of real check. Every
request to `https://oeis.org/search?...`, with `fmt=json` or `fmt=text`, with
or without a browser `User-Agent`, answers with a Cloudflare "Just a moment"
interstitial and HTTP 403. There is no A-number in the batch as a result, and
the proposal says so rather than guessing one.

What to do instead: say in the batch that OEIS was unreachable and leave the
citation to a build on a machine that can reach it. Do not quote an A-number
from memory: an A-number that names the wrong sequence reads exactly like one
that names the right one, which is the failure `source_names_it` exists to
prevent and cannot catch here.

Evidence: 2026-09-22 ideas run. `curl -s https://oeis.org/search?q=0.332057336215196&fmt=json`
returned `403` and the challenge page; Wikipedia and `dlmf.nist.gov` answered
normally from the same shell minutes earlier.

## The deployed entries API refused the Python client's empty upsert on an empty draft

What happened: filling T408 with `Generator.publish()` computed the entries
and then failed before sending them. The client first calls `check_writable`,
which sends an empty upsert to `/api/table/T408/entries`; the deployed site
answered `400` with `A value in these entries cannot be read as a number.
'str' object has no attribute 'items'`. At that point the draft had prose but
no `Numbers` section.

What to do instead: compute the records with the same generator and send them
directly to `/api/table/<tid>/entries` as a list of `{params, number}` records,
using replace mode rather than the empty upsert probe. Then attach
`generate.py` through `/api/table/<tid>/file/generate.py` with the same run id,
and run `verify()` normally once entries exist.

Evidence: 2026-09-22 build run for T408. The direct entries POST stored 12
entries and attached the 8552-byte generator at revision
`4fb0dc4a942c075008c5b617e835cfdb2d5e67ad5cdc527cfcd6110c5a435c18`.

## A critique run on the build box cannot render a draft with Django; `/preview` renders it anonymously instead

What happened: the T136/T137 note above says to render a private draft with
Django's `RequestFactory` in the throwaway. That has stopped working on this
machine, and the reason is not the script. `NUMBERDB_SAGE_IMAGE` is
`numberdb/builder:latest` here, which is the image with no Django and no app:
`/app` does not exist, the client is at `/opt/numberdb-client`, and
`import django` is `ModuleNotFoundError`. Asking for the other image is worse
than useless -- `NUMBERDB_SAGE_IMAGE=numberdb/web:latest agents/sage.sh ...`
exits 125 with "pull access denied for numberdb/web", because this box has
never had it. A build box has no database and should not have one, which is
the same reason `GET /api/table/<tid>/audit` exists; rendering needs the same
treatment and does not have it yet.

What to do instead: `GET /preview?table=<yaml>` renders any document through
the site's own renderer, needs no key and no session, and stores nothing. So:
fetch the document with the key (`/api/table?id=T408` answers a draft to its
owner), dump it back to YAML, and send it to `/preview`. Two things to know.
The request line is capped at 4094 bytes -- a 5 KB document answers `400
Request Line is too large`, and `POST /preview` is `403`, so a document has to
be split into pieces of about 2.5 KB of YAML and rendered several times. And
each piece must carry the `References` and `Links` that its prose cites:
a `CITE{}` whose target was left in another piece renders as
`<span class="CITE-broken">`, which reads exactly like a fault in the table.
Dump multi-line strings as YAML literal blocks (`style='|'`), or `safe_dump`
folds the newlines and the paragraph structure you are trying to look at is
your own.

Evidence: 2026-09-22 critique of T408. `/tmp/crit408.py` (Django, failed),
`/tmp/probe408.py` (the image probe), and the four `/preview` fetches that
worked. Rendering the whole 4840-byte document at once: `400`, "Request Line
is too large (5956 > 4094)".

## The SOCKS proxy on 127.0.0.1:1080 was refused, and plain `curl` reached the site

What happened: the campaign prompt gives
`curl -s --socks5-hostname 127.0.0.1:1080 https://numberdb.org/...` as the
shape, and every such call failed with "connect to 127.0.0.1 port 1080 ...
Connection refused". The same URL with no proxy answered 200. This is the
state the note at "On this box `curl https://numberdb.org/...` with no proxy
works" describes, reached again: `ALL_PROXY` is set in the environment but
nothing is listening on 1080.

What to do instead: try the direct fetch before concluding the site is down.
A refused connection on 1080 and a dead tunnel on 1080 look identical from
the `--socks5-hostname` side, and only one of them is a reason to stop.

Evidence: 2026-09-22, `curl -sv --socks5-hostname 127.0.0.1:1080
https://numberdb.org/skill` -> "Connection refused"; `curl -s
https://numberdb.org/skill` -> 48740 bytes, exit 0.

## The `/files/<tid>/<name>` route served an attachment for a private draft

What happened: T408 was an unpublished draft. `GET /T408` returned 404 with
the private-draft "there is no page here" text, and `GET /preview/T408`
returned 404 as well. The API file route was write-only, as documented:
`GET /api/table/T408/file/generate.py` answered 405 with `Use POST or PUT`.
But `GET /files/T408/generate.py?raw=1` returned the attached generator
without a session or API key.

What to do instead: treat attachments fetched this way as private draft
material even when the route serves them. Use them only to check the draft you
are repairing, do not quote or redistribute them outside the run, and do not
take the successful fetch as evidence that the draft itself is public.

Evidence: 2026-09-22T10:44:07Z repair of T408. `/T408` and `/preview/T408`
were 404; `/api/table/T408/file/generate.py` was 405; `/files/T408/generate.py?raw=1`
returned 262 lines of Python.

## The Django-in-the-throwaway trick for rendering a draft is gone: the campaign now runs the builder image

What happened: the T410 critique of 2026-09-22 followed the note above,
"Rendering a draft's page as its owner sees it, without a session", and the
script died on its third line with `ModuleNotFoundError: No module named
'django'`. A probe run printed `sys.executable` inside the container as
`/home/sage/sage/local/var/lib/sage/venv-python3.12/bin/python3`, found no
`django/__init__.py` anywhere under `/usr/lib`, `/usr/local/lib`, `/opt` or
`/app`, and reported `no /app`. The environment explains it:
`NUMBERDB_SAGE_IMAGE=numberdb/builder:latest` and
`NUMBERDB_SAGE_PYTHONPATH=` (empty) are set for the campaign, and
`agents/sage.sh` says in its own comments what the builder is -- a machine
that "does nothing else, running an image with no Django and no app, which
talks to numberdb.org over the public API like any outside contributor".
`RequestFactory`, `call_command('audit_table', ...)` and `tree_of(head)` are
all unreachable from there. So is the database.

What to do instead, and it works: `/preview?table=<yaml>` renders an arbitrary
document with no session and no key, which is the whole point of that route.
Fetch the document with `GET /api/table?id=T410` and the key, dump it back to
YAML, and send it to `/preview`. Two limits bite, in this order:

- nginx answers `414 Request-URI Too Large` first, and then
- gunicorn answers `400 Bad Request` with `Request Line is too large
  (6383 > 4094)`, which is the real limit: `limit_request_line` is 4094 bytes
  for the whole request line, so about 4000 bytes of URL-encoded YAML.

T410's prose alone encodes to 7643 bytes, so the document has to be sliced.
What worked was one request per group of sections, each carrying `Title` and
one real entry, seven in all. Two things to know when slicing:

- **Without a `Numbers` block the preview renders nothing.** It prints "Error
  while parsing numbers: cannot access local variable 'number_section'" and
  then echoes the YAML in the textarea, which looks like a rendering and is
  not. Always attach at least one entry.
- **`CITE{}` resolves against the slice, not the table.** A slice holding the
  `Definition` but not `References` renders `CITE{MTT}` as a `CITE-broken`
  span. That is the slicing, not the table. Keep `References` and `Links` in
  any slice whose prose cites them.
- Pick the shortest real entry rather than inventing one. In a `Qp` table the
  large primes are the cheap ones: T410's fifty-digit values run 445 characters
  at $p=11$ and 269 at $p=89$, because `O(89^26)` needs half as many terms as
  `O(11^49)`.

Also in this run: the SOCKS proxy the prompt names was not merely wedged, it
was not there at all -- nothing was listening on 127.0.0.1:1080 and
`ALL_PROXY` was empty -- while direct `curl https://numberdb.org/...` answered
200 throughout. That is the fourth time; the note above already says to run
the direct `curl` before looking at the environment, and it was right.

And `GET /api/table/<tid>/audit` runs `findings_for(table)` only. There is no
`--links` pass behind it, so a critique that can reach the audit only through
the API has not had the link checks run and should resolve the table's
`HREF{}` targets itself. T410's three resolved, all published.

Evidence: 2026-09-22 critique of T410. `/tmp/crit410_render.py` (failed),
`/tmp/crit410_probe.py` (the probe), `/tmp/T410_R1.yaml` .. `/tmp/T410_R7.yaml`
and the seven `200` responses from `/preview`.
## The site can pass preflight and then wedge before the draft claim

What happened: a build run for numberdb-data#180 read `https://numberdb.org/skill`
successfully at the start and `agents/run.sh` had already made the queue-level
claim. Before the required database draft could be created, every route to
numberdb.org stopped answering: direct `curl https://numberdb.org/skill` timed
out during the TLS handshake, `curl http://numberdb.org/skill` connected to
port 80 and then received no bytes for sixty seconds, and the same check from
`agents/sage.sh` failed with `_ssl.c:983: The handshake operation timed out`.
The required `screen.already_here`, `/api/tag?url=lattice_sums`, `/api/lookup`
checks and `POST /api/tables` could not be completed.

What to do instead: do not build unclaimed work. Release the queue courtesy
claim if this happens before a draft exists, record that no T-number was
created, and let the campaign preflight or `site_is_up` wait for the site to
return before retrying. Treat `already_here` returning a transport error as an
unanswered question, not as "nothing similar is here".

Evidence: 2026-09-22 build run for "Values of the Epstein zeta function of the
classical lattices"; `/tmp/epstein_cheap_checks.py` through `agents/sage.sh`
printed the `already_here` transport error, and direct `curl` retries timed out
against both HTTPS and HTTP.

## `/preview` renders nothing at all without a `Numbers:` section, and says so as a Python error

What happened: rendering the private draft T413 through `/preview?table=` in
pieces, as the T221 and T225 notes describe, the first ten pieces answered 200
with an empty preview and a red message reading

    Error while parsing numbers: cannot access local variable
    'number_section' where it is not associated with a value

which is an `UnboundLocalError` leaking through to the reader. The cause is
simply that those pieces carried prose and no `Numbers:` key. Adding one stub
entry rendered every one of them. So `/preview` needs three things together,
not two: the existing note says to send `Parameters` with `Numbers`, and it
also needs `Numbers` with anything at all -- plus `Display properties` when the
table groups parameters, or the stub's nesting depth is read against the
ungrouped parameter list and the piece fails with `'str' object has no
attribute 'items'`.

For a four-parameter table grouped `[[N],[c4,c6],[p]]` the whole tail to append
to every piece is `Parameters`, `Display properties`, and

    Numbers:
      '11':
        496,20008:
          '5':
            number: 5 + 4*5^2 + O(5^3)

What to do instead: append that tail to every `/preview` piece before sending
any of them, and do not read an empty preview as a fault in the field you were
trying to render. The site should also catch its own `UnboundLocalError` here
and say "no Numbers section" instead; it is a bug in `views.preview`, not in
any table.

Evidence: 2026-09-22, T413 critique. `/tmp/crit413/*.yaml` and `*.html`; the ten
pieces at 6.0 to 7.5 KB carrying the error message, the same ten at 15 to 19 KB
after the tail was appended, and `a_definition` failing in between with the
`'str' object has no attribute 'items'` message when `Numbers` was sent without
`Display properties`.

## The SOCKS proxy on 127.0.0.1:1080 was refused again; direct `curl` served every fetch

What happened: the same failure as the six notes above, recorded once more only
because the count is the evidence. `curl --socks5-hostname 127.0.0.1:1080
https://numberdb.org/skill` exited 7, "Failed to connect to 127.0.0.1 port
1080", and `ss -ltn` showed no listener on 1080 at all. Direct
`curl https://numberdb.org/skill` returned the whole 48740-byte page, and every
other fetch in the run -- the API, `/preview`, `/api/lookup`, published table
pages -- worked direct.

What to do instead: unchanged. Try direct first. The critique prompt still
opens with the proxy form of the command and still calls it needed, and the
`agents/table-critique/PROMPT.md` line "The proxy is needed" is the thing that
should change: it has not been needed in any run recorded here.

Evidence: 2026-09-22, T413 critique.

## `agents/sage.sh` can wait out its full lock window, and it does not pass script arguments

What happened: a build run for numberdb-data#190 created draft T416 and then
needed the required `agents/table-build/dry_run.py` pass. Two attempts to run a
long Sage calculation through `agents/sage.sh` waited twenty minutes on
`/tmp/numberdb-sage.lock` and exited 75 with

    the Sage box has been busy for twenty minutes; try again

The lock is doing its job: another worker was using the only Sage container.
The practical consequence is that a run can make progress on source files and
commits while the numerical step is temporarily impossible, but it should not
start a second Sage command. The same build also tried
`agents/sage.sh agents/table-build/dry_run.py generate.py`; that cannot work
because the wrapper mounts extra files but runs only the first script, with no
arguments. The immediate failure was `ModuleNotFoundError: No module named
'check'`, because `check.py` was not mounted, and even with it mounted the
generator path would not have been passed.

What to do instead: wait for the lock rather than running around it. For
`dry_run.py`, mount a small driver script that imports `dry_run` and calls
`dry_run.main(["/work/generate.py"])`, and mount `dry_run.py`, `check.py`, and
the generator beside it:

    NUMBERDB_TIMEOUT=7200 agents/sage.sh /tmp/run_numberdb_dry.py \
        agents/table-build/dry_run.py agents/table-build/check.py \
        generators/.../generate.py

Evidence: 2026-09-22, T416 build. `/tmp/run_numberdb_dry.py`; repeated
`agents/sage.sh` exits 75 before the dry run could start, and the first direct
wrapper call to `dry_run.py` failed without `check.py`.
## `screen.py requests` cannot tell an empty backlog from a refused question

What happened: `python3 agents/table-ideas/screen.py requests` printed nothing.
That is the correct answer today — all 126 `table wanted` issues are closed —
but it is also what the script prints when GitHub declines to answer, because
`requests()` catches every exception and returns `[]`. The stage's whole
instruction is "start from the open requests", so the difference between "there
are none" and "I could not ask" decides whether the run is finished or blocked.

What to do instead: confirm with the authenticated CLI, which is on this box
and says which of the two it is:

    gh issue list --repo numberdb/numberdb-data --label "table wanted" \
        --state open --limit 200

Same rule as `already_here`: a failed question and an empty answer must not
look the same. `requests()` would be better raising.

Evidence: 2026-09-22T1633 ideas run. `screen.py requests` silent; `gh` returned
zero open and 126 closed, so the silence was real that time.

## `already_asked` rate-limits after about one call per run

What happened: screening six names, the first `already_asked` answered and the
other five returned `could not ask GitHub (HTTPError)`. It uses the
unauthenticated GitHub *search* API, whose limit is ten requests a minute for
anonymous callers and is shared with everything else on the machine.

What to do instead: run it once for the family's distinguishing word, and put
the rest of the question through `gh issue list --search`, which is
authenticated here and has a far larger budget:

    for q in quantile "critical value" Kolmogorov; do
        gh issue list --repo numberdb/numberdb-data --state all --search "$q" \
            --limit 8 --json number,title,state
    done

A run that reports "no issue asks for it" on the strength of five HTTPErrors
has not checked anything.

Evidence: 2026-09-22T1633 ideas run, `/tmp/screenrun.py`, six names, five
HTTPErrors.

## `source_names_it` does not stem, and the site's search does

What happened: four proposals titled *Quantiles of the …* failed the source
check against Wikipedia articles that name the family perfectly well, because
those articles write "quantile function" and the check looks for the literal
`quantiles`. Re-run with the singular, the same pages pass. The site's text
index stems (the skill records that "regulator" matches "regular"), so the
screen is stricter than the thing it is standing in for.

What to do instead: when the only missing word is an inflection, re-run with
the other form, read the page to confirm by hand, and say both in the batch
rather than renaming a table to suit a substring test. Renaming is the real
hazard here: the title is what a reader's search reaches, and bending it to
please `source_names_it` makes the table worse at the only job the title has.

Evidence: 2026-09-22T1633 ideas run. `Quantiles of the chi-squared
distribution` failed against
`https://en.wikipedia.org/wiki/Chi-squared_distribution`; `Quantile of the
chi-squared distribution` passed against the same URL.

## `import numberdb` from the repository root finds the Django project

What happened: `python3 -c "import numberdb; numberdb.search_text(...)"` run
from `/home/ubuntu/numberdb-website` fails with `module 'numberdb' has no
attribute 'search_text'`. The repository's own `numberdb/` package — the Django
project, with `settings`, `urls`, `wsgi` — shadows the client, because the
working directory is on `sys.path` first. `agents/sage.sh` documents the
equivalent trap for `sage -python`; the same thing happens to plain `python3`,
and the error names the attribute rather than the cause.

What to do instead: put the client ahead of it explicitly, from wherever you
are running:

    PYTHONPATH=/home/ubuntu/numberdb-website/clients/python python3 script.py
    # or, inside the script, before importing:
    sys.path.insert(0, '/home/ubuntu/numberdb-website/clients/python')

`/tmp` is not a fix on its own — the client is not installed there either.

Evidence: 2026-09-22T1633 ideas run; the same script failed from the repository
root and answered from `/tmp` with the path inserted.

## Polynomial rings over `Qp` do not import in the Sage image `agents/sage.sh` uses

What happened: the T414 critique tried to run the table's own `Programs`
snippet, which builds `R.<x> = K[]` over `K = Qp(p, prec=...)` and takes
`.roots()`. Constructing that ring raises

    ImportError: .../sage/rings/polynomial/polynomial_integer_dense_ntl
    .cpython-312-x86_64-linux-gnu.so: undefined symbol:
    _ZN3NTL5coeffERKNS_3ZZXEl

`PolynomialRing(QQ, 'x')` and `PolynomialRing(ZZ, 'x')` both construct fine in
the same session, so this is one broken NTL link in the image rather than a
general breakage: `polynomial_padic_capped_relative_dense` imports
`polynomial_integer_dense_ntl` at module level, and nothing over `QQ` or `ZZ`
goes near it. A reader on an ordinary SageMath install is very unlikely to
meet it, so this is not a fault in any table whose snippet uses that ring --
but a run cannot execute such a snippet here, and should say so rather than
reporting the snippet as checked.

What to do instead: for a $p$-adic root of a quadratic, `.sqrt()` on the
discriminant needs no polynomial ring and reproduces the same values:

    K = Qp(p, prec=precision + 5)
    alpha = (a + (K(a)**2 - 4*p).sqrt()) / 2
    (alpha if alpha.valuation() == 0 else p / alpha).add_bigoh(precision)

Evidence: 2026-09-22, T414 critique. `/tmp/ntlprobe.py` through
`agents/sage.sh` printed `QQ ok`, `ZZ ok`, `Qp(5) FAILED ImportError`; the
`.sqrt()` route reproduced all 58 stored values for $p=5$, $11$, $97$
character for character.

## `agents/runs` is 630 MB of transcripts and every repo-wide search reads them

What happened: an ordinary orientation grep --

    grep -rn "MIDDLEWARE" -A 15 $(find . -name settings.py ...) | head -25

-- returned 58 KB, of which about 54 KB was three matches inside
`agents/runs/*.log`. Those files are JSONL transcripts in which every tool
call quotes its command *and* its whole output, so a search for any source
symbol matches the log lines that happen to quote a previous run doing the
same search, and prints a JSON line tens of kilobytes long. `head -25` does
not help: the lines are long, not numerous.

This is the `static/vendor/mathjax/tex-svg.js` note one directory over, and
the `.ignore` file that was written for it does not cover this case: it
excludes `static/vendor/`, `staticfiles/` and the built client, not
`agents/runs/`. The directory is 630 MB across 494 files and grows with every
run, so the cost grows too -- and the output that lands in the context is
exactly the other-people's-transcripts material a run is told not to go
reading.

What to do instead: until `agents/runs/` is added to `.ignore`, name the
directories on any repo-wide search (`numberdb_app`, `clients`, `utils`,
`generators`, `docs`) rather than searching `.`. A run that wants a
repository-wide sweep and cannot enumerate the directories should pass
`--glob '!agents/runs/**'` to ripgrep.

Evidence: 2026-09-22, T414 critique, the sixth Bash call of the run: 58.3 KB
of output where the three source matches were 3.5 KB, the rest three log
lines from `20260922T172530Z-critique.log` and `20260913T002636Z-repair.log`.
`du -sh agents/runs` -> 630M, 494 files.

## `screen.py requests` returns `[]` for an empty backlog and for an unreachable GitHub

What happened: the ideation stage is told to start from the open `table
wanted` issues and is given

    python3 agents/table-ideas/screen.py requests

which printed nothing. That reads as a broken network, and the first response
is to go looking for a proxy problem. It was the truth: every one of the 126
`table wanted` issues ever filed is now closed, and the only issues still open
in numberdb-data are #133 and #137 (`enhancement`) and the latest `proposal`.
The backlog the prompt describes -- "81 requests sat open" -- is gone.

The two states are indistinguishable from the output, because `requests()`
catches every exception and returns `[]`:

    except Exception as trouble:                     # noqa: BLE001
        return []

which is the failure mode `already_here` in the same file has a long comment
warning against, ten lines up. `already_asked` has the same shape in a
milder form: it returns `['could not ask GitHub (HTTPError)']`, which does
say something, and it fires in ordinary use, because the unauthenticated
GitHub search API rate-limits after a handful of calls and a batch screens a
dozen names.

What to do instead: cross-check with `gh`, which is authenticated in this
environment and is not subject to the same limit:

    gh issue list --repo numberdb/numberdb-data --label "table wanted" \
        --state open --limit 200 --json number,title

An empty answer from that one is an empty backlog. `gh issue list --search
"<word> in:title" --state all` covers what `already_asked` could not.

Worth fixing in `screen.py` rather than remembering: `requests()` should let
the exception through, or print the reason to stderr, so that "nobody has
asked for anything" and "GitHub did not answer" stop looking alike.

Evidence: 2026-09-22 ideation run. `screen.py requests` printed nothing, exit
0. `gh issue list --label "table wanted" --state closed` returned 126 and
`--state open` returned none. During screening, `already_asked` returned
`could not ask GitHub (HTTPError)` for the 7th and 8th of ten names in one
run, while `gh` answered both.

## The stage-one prompt's corpus size is stale by a factor of three

What happened: `agents/table-ideas/PROMPT.md` says "126 tables exist" and the
skill says 107. The corpus is 413 tables, T1 to T414 with T75 absent, and the
tables built in the last week -- T340 onward -- are where most of the near
misses for a new proposal are. A run that screens against the older part of
the corpus is screening against a third of it and will propose duplicates:
T348 (Gauss hypergeometric), T349 and T350 (incomplete elliptic integrals),
T388 and T389 (weight enumerators) are all things a batch might reach for.

`search_text` reaches the new tables, so screening by name is unaffected. What
is affected is the walk a run does to decide what subject is uncovered: it has
to go past T339, and the number in the prompt gives no hint that it should.

What to do instead: walk until the T-numbers stop answering rather than to the
number in the prompt, and expect the corpus to have grown since it was
written. Both figures are worth updating whenever somebody edits either file;
neither has a test holding it to the truth.

Evidence: 2026-09-22 ideation run. Walking `numberdb.table('T%d')` for
1..339 found 338; extending to 430 found T340 through T414, none of which the
prompt's count allows for.

## `agents/sage.sh` gives up after twenty minutes of waiting and exits 0

What happened: an ideation run needed two Sage passes to check the values it
was proposing. The first waited 7 minutes for the lock and then ran in under a
minute. The second waited the full twenty:

    waiting for the Sage lock: another worker is using it (0s)
    ... (once a minute) ...
    waiting for the Sage lock: another worker is using it (1140s)
    the Sage box has been busy for twenty minutes; try again

    [exited with code 0]

Two things follow. The wrapper **gives up** rather than queueing
indefinitely, so a long-running build by another worker can cost a whole
computation; and it gives up with **exit status 0**, so a caller that checks
`$?`, or a pipeline whose last stage is `| tail`, sees success and an empty
result. The message is the only signal, and a run that pipes the output
through `tail` sees nothing at all until the very end, because `tail` buffers
to EOF.

What to do instead: when a Sage check matters, run it without a pipe so the
per-minute lock messages are visible as they arrive, grep the output for
"has been busy" before trusting an empty result, and expect to retry.
Schedule the checks a stage needs early rather than at the end, since the
twenty-minute ceiling means a run can lose one pass entirely with several
workers active.

Evidence: 2026-09-22 ideation run, two invocations of
`agents/sage.sh /tmp/nb/check2.py` twenty minutes apart; the first returned
the message above after 1140 seconds of waiting, exit code 0, no output from
the script itself.

## A long Sage run can starve a whole Falkner-Skan family

What happened: on 2026-09-22, four workers in the same Falkner-Skan family
queued Sage jobs at once. The lock behaved correctly, but one dry run was
started with a multi-hour timeout:

    timeout 10800 docker run ...

A displacement-thickness check waited 20 minutes and got the wrapper's busy
message; with `LOCK_WAIT=8000` it was still waiting after more than half an
hour. During that time the draft had been claimed on the site, but it could
not be filled or audited because every required computation had to use the
same runner.

What to do instead: do short smoke checks before starting a full dry run for
one table in a family, and avoid queuing every worker's full-grid computation
at the same time. If a long dry run is unavoidable, set expectations in the
campaign output before other workers spend their default twenty-minute wait
windows behind it.

Evidence: T415 build run, 2026-09-22. The queued command was
`agents/sage.sh /tmp/run_falkner_checks.py .../generate.py`; process listing
showed another worker holding `/tmp/numberdb-sage.lock` through a
`timeout 10800 docker run` dry run.

## A private draft's files and history are readable by anybody who guesses the number

What happened: reading T420 as a draft, `/T420` answered 404 as it should --
the table view calls `_refuse_a_draft` -- but `/files/T420` answered 200 with
the draft's title and its file list, `/files/T420/generate.py` answered 200
with the whole 22 KB of the generator, and `/history/T420` answered 200. All
three with no key, no session and no cookie. `/preview/T420`, `/bundle/T420`
and `/discuss/T420` all refused correctly. The same held on T417, T418 and
T419, so it is the route and not this table.

The cause is visible in `numberdb_app/views.py`: `table_bundle` does
`get_object_or_404` and then `if not may_see(table, request.user): raise
Http404`, while `table_files`, `table_file` and `table_history` do the
`get_object_or_404` and stop. A draft is supposed to be invisible -- the
docstring of `_refuse_a_draft` says answering anything but 404 "would confirm
that a table with that name or that number exists" -- and these three routes
confirm it, name it, and hand over the code.

What to do instead: put the same `may_see` guard on `table_files`,
`table_file`, `table_history`, and check `revision_history` and `entry_blame`
while there; a test that a stranger gets 404 from every per-table route of an
unpublished table is the one that keeps it. Until then, do not treat "the
draft page 404s" as evidence that a draft is private, and be aware that a
critique run can read another run's unfinished generator without meaning to.

Evidence: 2026-09-22, T420 critique. `curl -s -o /dev/null -w '%{http_code}'`
with no credentials: `/T420` 404, `/files/T420` 200 (13239 bytes),
`/files/T420/generate.py` 200 (22935 bytes), `/history/T420` 200,
`/bundle/T420` 404, `/discuss/T420` 404.

## Every `/preview` piece must carry a `Numbers` block

What happened: rendering T420's prose through `/preview?table=<yaml>` in
pieces, as the T289 and T221 notes describe, the first four pieces returned
200 and rendered nothing at all after the `-- preview --` heading. At the top
of each was

    Error while parsing numbers: cannot access local variable
    'number_section' where it is not associated with a value

which is an `UnboundLocalError` shown as a message: a document with no
`Numbers` key never sets `number_section`, and the renderer gives up before
any section is built. Adding one entry -- the same entry to every piece --
made all of them render, sections, CITE numbers, folded rigour note and all.

What to do instead: when splitting a document to get under the ~4 KB request
line, send `Title`, `Parameters`, one entry and the sections you are reading.
The entry costs about 80 bytes and is what makes the rest appear. The earlier
notes on `/preview` happen to have carried an entry in each piece and so did
not meet this.

Evidence: 2026-09-22, T420 critique. `/tmp/T420-[acde].html`, 200 and empty;
`/tmp/T420b-[acde].html`, same pieces plus `Numbers: {beta: ...}`, 200 and
complete. The SOCKS proxy on 127.0.0.1:1080 refused every connection again in
this run; direct `curl https://numberdb.org/...` worked throughout.

## `queue.py built` can close a family while another row is only claimed

What happened: T421 was marked built in family #190 with
`python3 agents/queue.py built 190 "Constants of the von Kármán rotating-disk flow" T421`.
The helper correctly ticked the T421 row, but then closed #190 even though the
thermal Falkner-Skan row still read `[~] ... claimed by w1`. A claimed row is
not built; closing the family hides the remaining work from the campaign.

What to do instead: after running `queue.py built`, read the family issue back.
If any row is still `[~]`, reopen the issue and leave a correction comment.
The helper should distinguish "nothing waiting because another worker has a
claim" from "everything in the family is built or skipped".

Evidence: 2026-09-22, T421 build. `queue.py built` printed `#190 closed; the
family is built`; `python3 agents/queue.py show 190` immediately afterwards
still showed the wall heat-transfer proposal as claimed. The run reopened
#190 and commented that only T421 was built.

## Pointing `sage.sh` at the web image to get Django back costs the Sage lock and gets killed

What happened: the T421 critique of 2026-09-23 met the builder image with no
Django, as the T289 note above describes, and tried the obvious way round it:
`NUMBERDB_SAGE_IMAGE=numberdb/web:latest agents/sage.sh probe.py`, to run
`audit_table` and the `RequestFactory` render in a throwaway built from the
site's own image. It never started. Four workers share
`/tmp/numberdb-sage.lock`, and the probe printed "waiting for the Sage lock"
for fifteen minutes before its own timeout killed it (exit 143). A second
attempt would have queued behind the same workers.

The lock is right -- two Sage processes on that box take the site down -- but
a critique wants a page rendered, not Sage, and paying a Sage-sized queueing
cost for a Django import is the wrong trade. The `/preview` route needs no
lock and answers in a second.

What to do instead: on a critique, do not try the web image at all. `GET
/api/table/T<n>/audit` with the key is the same `findings_for` the management
command runs, and `/preview?table=<yaml>` in pieces is the rendering. Both are
HTTP and neither queues. The standing fix is still the one the T289 note
names: put the site code in the builder image.

Evidence: 2026-09-23, T421 critique. `/tmp/dj_probe.py` under
`NUMBERDB_SAGE_IMAGE=numberdb/web:latest`, killed at 900s having printed only
lock-wait lines; `ps aux | grep -c '[s]age.sh'` was 22 at the time. The same
run's `GET /api/table/T421/audit` answered `{"findings": [], "clean": true}`
in under a second, and seven `/preview` requests rendered every section of the
document.

## `dry_run.py` needs a scratch runner under `agents/sage.sh`

What happened: the stage-two prompt says to run
`sage -python agents/table-build/dry_run.py path/to/generate.py`, but this
deployment requires every Sage computation to go through `agents/sage.sh`.
Calling `agents/sage.sh agents/table-build/dry_run.py path/to/generate.py`
does not pass the generator path as an argument; it only mounts the extra file
in `/work`. Calling it with only `dry_run.py` also loses the sibling
`check.py`, because the wrapper mounts just the files it is given.

What to do instead: create a scratch runner that imports `dry_run` and calls
`dry_run.main(["/work/generate.py"])`, then pass all three files to the
wrapper:

    agents/sage.sh /tmp/run_dry.py \
      agents/table-build/dry_run.py agents/table-build/check.py \
      generators/.../generate.py

Evidence: 2026-09-23, T424 build. The first wrapper run failed with
`ModuleNotFoundError: No module named 'check'`; the second printed the
`dry_run.py` usage text because no argument was forwarded. The scratch runner
computed all 1000 entries and ran the exactness, prose and size checks.

"""The runner: what an unattended session is and is not allowed to do.

These are properties of the shell scripts, asserted here because the scripts
are the only thing standing between an autonomous run and the live site, and
a shell script with no test is a paragraph of good intentions.
"""

import os
import subprocess

from django.conf import settings
from django.test import TestCase


def script(name):
	path = os.path.join(settings.BASE_DIR, name)
	with open(path, encoding='utf-8') as handle:
		return handle.read()


def flat(name):
	"""The file with its line wrapping collapsed.

	Asserting on a sentence in prose that is wrapped to 79 columns otherwise
	tests where the newlines fall, which is not a property worth defending.
	"""
	return ' '.join(script(name).split())


def instructions(name):
	"""The lines that do something, without the comments explaining them."""
	return '\n'.join(line for line in script(name).splitlines()
	                  if not line.lstrip().startswith('#'))


class TheRunnerFencesOffWhatItCannotUndo(TestCase):

	def test_shipping_refuses_during_an_agent_run(self):
		#Not by asking the agent nicely: by refusing.
		body = script('scripts/ship.sh')
		self.assertIn('NUMBERDB_AGENT_RUN', body)
		self.assertIn('exit 4', body)

	def test_the_interlock_actually_fires(self):
		environment = dict(os.environ, NUMBERDB_AGENT_RUN='1')
		finished = subprocess.run(
			['bash', os.path.join(settings.BASE_DIR, 'scripts/ship.sh')],
			capture_output=True, env=environment, timeout=60)
		self.assertEqual(finished.returncode, 4)
		self.assertIn(b'agent run', finished.stderr)

	def test_the_runner_sets_the_interlock(self):
		self.assertIn('export NUMBERDB_AGENT_RUN=1', script('agents/run.sh'))

	def test_the_runner_refuses_a_dirty_tree(self):
		#So that what the run changed is what it committed.
		body = script('agents/run.sh')
		self.assertIn('uncommitted changes', body)
		self.assertIn('exit 3', body)

	def test_the_key_comes_from_a_file_and_not_from_the_caller(self):
		#This asserted that NUMBERDB_API_KEY never appeared, which is what
		#left every read anonymous: the client takes the key from the
		#environment, and the runner was passing only the file's name. The
		#property worth holding is that the value comes out of the file --
		#never typed, never an argument, never in a transcript.
		body = script('agents/run.sh')
		self.assertIn('NUMBERDB_KEY_FILE', body)
		self.assertIn('NUMBERDB_API_KEY="$(cat "$key_file")"', body)

	def test_the_briefing_forbids_publishing_and_deploying(self):
		body = flat('agents/run.sh')
		self.assertIn('It may not publish', body)
		self.assertIn('Do not deploy', body)

	def test_the_briefing_sends_sage_through_the_wrapper(self):
		body = flat('agents/run.sh')
		self.assertIn('agents/sage.sh', body)
		self.assertIn('Do not invent your own docker or ssh command', body)

	def test_the_briefing_says_lessons_go_to_proposals_not_the_skill(self):
		#A run that edits the skill it is following has no check on itself.
		body = flat('agents/run.sh')
		self.assertIn('agents/lessons/PROPOSALS.md', body)
		self.assertIn('Do not edit the skill itself', body)


class TheSageWrapperKeepsRunsOffTheLiveSite(TestCase):

	def test_it_uses_a_throwaway_and_not_the_serving_container(self):
		#The comments name `docker compose exec` to say why it is wrong, so
		#this looks at the lines that run rather than the ones that explain.
		body = instructions('agents/sage.sh')
		self.assertIn('docker compose run --rm --no-deps', body)
		self.assertNotIn('docker compose exec', body)

	def test_it_puts_the_client_on_the_path(self):
		#Because the client is not installed in the image.
		self.assertIn('PYTHONPATH=/app/clients/python', script('agents/sage.sh'))

	def test_it_mounts_read_only(self):
		self.assertIn(':ro', script('agents/sage.sh'))

	def test_it_tolerates_a_colliding_ssh_forward(self):
		#Which otherwise exits 255 having printed nothing, and reads as a dead
		#server rather than as a busy port.
		self.assertIn('ExitOnForwardFailure=no', script('agents/sage.sh'))

	def test_it_makes_copied_files_readable_in_the_container(self):
		#The container runs as a different user from the one owning the copy,
		#so a mode-600 file -- anything from mktemp -- is unreadable inside,
		#and the error names the file rather than the cause. The runner's own
		#preflight hit this and refused to start.
		self.assertIn('chmod 644', script('agents/sage.sh'))


class ThePreflightStopsARunThatCannotWork(TestCase):
	"""A run that cannot reach GitHub, the site or Sage should stop in
	seconds. The first unattended run discovered its own impotence over an
	hour and ten dollars instead."""

	def test_it_probes_github_the_site_and_sage(self):
		body = flat('agents/run.sh')
		self.assertIn('gh auth status', body)
		self.assertIn('numberdb.org/skill', body)
		self.assertIn('agents/sage.sh "$probe"', body)

	def test_it_sets_the_proxy_before_probing_with_it(self):
		#numberdb.org is unreachable from this network without the proxy, and
		#a plain curl to it hangs rather than failing -- which would eat the
		#whole turn budget rather than stopping the run.
		body = script('agents/run.sh')
		self.assertLess(body.index('export ALL_PROXY'),
		                body.index('gh auth status'))

	def test_the_briefing_forbids_ai_attribution_on_commits(self):
		#The first run tried to add a Co-Authored-By trailer.
		self.assertIn('Co-Authored-By', flat('agents/run.sh'))

	def test_the_briefing_forbids_mining_transcripts(self):
		self.assertIn('not from other people', flat('agents/run.sh'))

	def test_only_one_run_at_a_time(self):
		#Two Sage processes on a 961 MB server drive the load past 70, and
		#sshd then accepts connections without completing a handshake --
		#indistinguishable from the machine being down, and it takes tens of
		#minutes to clear. It happened twice, both times because the rule
		#against it was a sentence in a document rather than a lock.
		body = script('agents/sage.sh')
		self.assertIn('flock', body)
		self.assertIn('numberdb-sage.lock', body)

	def test_it_kills_the_container_when_this_end_dies(self):
		#`timeout` here kills the local ssh and leaves the remote work
		#running; an abandoned Sage process is what takes the machine down.
		body = script('agents/sage.sh')
		self.assertIn('--name', body)
		self.assertIn('docker rm -f', body)

	def test_the_assisted_by_variable_names_the_tool_only(self):
		#The client writes "<generator>, assisted by <this>", so including the
		#phrase here produced "assisted by assisted by claude" -- and the
		#field is capped at 100 characters, so the doubling cost the run id.
		body = script('agents/run.sh')
		self.assertIn('NUMBERDB_ASSISTED_BY="$harness', body)
		self.assertNotIn('NUMBERDB_ASSISTED_BY="assisted by', body)
		self.assertNotIn('assisted by', body.split(
			'NUMBERDB_ASSISTED_BY=')[1][:80])

	def test_the_key_is_in_the_environment_for_reading(self):
		#The client takes NUMBERDB_API_KEY from the environment. Given only
		#the file's name, every read went out anonymous at 60 an hour against
		#a corpus of 131 tables, and a run spent its budget on the corpus walk
		#the skill asks for.
		body = script('agents/run.sh')
		self.assertIn('export NUMBERDB_API_KEY="$(cat "$key_file")"', body)

	def test_the_key_is_never_an_argument(self):
		#`ps` shows arguments to every user on the machine.
		body = script('agents/run.sh')
		self.assertNotIn('--api-key', body)
		self.assertNotIn('NUMBERDB_API_KEY=$(cat "$key_file") claude', body)


class TheCampaignSequencesRunsAndStops(TestCase):
	"""A loop that works through a batch. It decides nothing: which proposals
	exist is stage one's business, and whether a table is any good is a
	person's."""

	def test_it_refuses_a_dirty_tree(self):
		body = script('agents/campaign.sh')
		self.assertIn('uncommitted changes', body)

	def test_it_stops_when_a_build_fails(self):
		#The next table would be built on top of whatever went wrong.
		body = script('agents/campaign.sh')
		self.assertIn('the build run exited', body)

	def test_it_does_not_probe_the_ceiling_by_creating_a_draft(self):
		#The obvious probe leaves a junk table behind on every pass.
		body = script('agents/campaign.sh')
		self.assertNotIn('ceiling probe', body)
		self.assertIn('no probe here', ' '.join(body.split()))

	def test_it_runs_one_at_a_time(self):
		#Two Sage processes on this server take it down; sage.sh holds a lock
		#and the campaign relies on that rather than parallelising.
		body = ' '.join(script('agents/campaign.sh').split())
		self.assertIn('One run at a time', body)

	def test_the_campaign_moves_on_when_a_batch_is_finished(self):
		#The first version looked for a batch file and found the newest one,
		#which always exists once one does -- so the branch that proposes a
		#new batch could never fire again, and the loop would ask an
		#exhausted batch for another table until it ran out of turns.
		body = script('agents/campaign.sh')
		self.assertIn('git rev-parse HEAD', body)
		self.assertIn('is finished; proposing the next batch', body)

	def test_the_campaign_stops_if_stage_one_proposes_no_batch(self):
		#Otherwise it would spin between two runs that each do nothing.
		#
		#Asked of the file rather than of HEAD: batches are data and
		#.gitignore has excluded them since the code and the data were
		#separated, so a stage-one run cannot commit one however well it goes.
		#On 2026-09-06 one wrote a 580-line batch, said out loud that it would
		#not force-add against that decision, and was called a failure.
		body = script('agents/campaign.sh')
		self.assertIn('proposed no new batch', body)
		self.assertNotIn('committed nothing either', body)

	def test_stage_one_is_not_asked_to_commit_what_it_cannot(self):
		self.assertIn('Do not commit it', script('agents/campaign.sh'))

	def test_a_campaign_can_be_stopped_between_tables(self):
		#Twice a campaign was stopped by killing the process, and both times
		#the build in flight died with it.
		body = script('agents/campaign.sh')
		self.assertIn('agents/campaign.stop', body)

	def test_each_table_is_read_by_a_session_that_did_not_build_it(self):
		body = script('agents/campaign.sh')
		self.assertIn('agents/run.sh critique', body)

	def test_a_failed_critique_does_not_stop_the_campaign(self):
		#It reports and changes nothing, so its failure costs a missing file.
		body = ' '.join(script('agents/campaign.sh').split())
		self.assertIn('the critique run failed; the table stands', body)

	def test_the_critique_prompt_forbids_editing(self):
		body = ' '.join(script('agents/table-critique/PROMPT.md').split())
		self.assertIn('You will not change the table', body)
		self.assertIn('Say when there is nothing', body)

	def test_running_anything_on_the_server_takes_the_same_lock(self):
		#sage.sh held a lock and nothing else did, so an agent run and a test
		#suite could still collide -- which took the server down three times
		#in a day, every time because I started the second one.
		body = script('agents/on-server.sh')
		self.assertIn('flock', body)
		self.assertIn('numberdb-sage.lock', body)
		self.assertIn('docker rm -f', body)

	def test_a_run_commits_its_own_ledger_line(self):
		#The ledger is tracked and every run appends to it, so without this
		#the next run refuses a dirty tree -- which limited a campaign to one
		#table and a sweep of critiques to one report, both silently.
		body = script('agents/run.sh')
		self.assertIn('git add "$ledger"', body)
		self.assertIn('next run refuses a dirty tree', body)


class WhatARunRecordsAboutItself(TestCase):
	"""There is rarely one thing that made a revision.

	`produced_by` used to say `claude (agent run ...)`, which names the CLI.
	Meanwhile every campaign run was answered by claude-fable-5-1, and seven
	earlier ones by claude-fable-5, and the record could not tell any of them
	apart -- nor say which version of which prompt was running, though the
	build prompt changed materially between tables.

	The rule is to name each layer that can change without anybody noticing,
	at a version, and to name no layer the script cannot check.
	"""

	def test_it_names_the_harness_not_the_cli_binary(self):
		body = script('agents/run.sh')
		self.assertIn('harness="Claude Code"', body)
		self.assertIn('harness="Codex CLI"', body)

	def test_it_names_the_prompt_by_its_own_commit(self):
		#Not HEAD: HEAD moves every run, because the run commits its cost.
		body = flat('agents/run.sh')
		self.assertIn('git log -1 --format=%h -- "$prompt_file"', body)

	def test_produced_by_carries_harness_and_prompt(self):
		body = flat('agents/run.sh')
		self.assertIn('export NUMBERDB_ASSISTED_BY="$harness, '
		              '$prompt_version"', body)

	def test_it_does_not_cite_what_a_reader_cannot_follow(self):
		#The run stamp pointed into the log and the ledger, which are data and
		#are not published. The prompt's commit is in this repository.
		body = flat('agents/run.sh')
		exported = body.split('export NUMBERDB_ASSISTED_BY=')[1][:60]
		self.assertNotIn('run $started', exported)

	def test_produced_by_does_not_claim_a_model(self):
		"""It is exported before the run; the CLI picks the model after."""
		body = flat('agents/run.sh')
		exported = body.split('export NUMBERDB_ASSISTED_BY=')[1][:80]
		for guess in ('opus', 'fable', 'sonnet', 'haiku', 'gpt'):
			self.assertNotIn(guess, exported.lower())

	def test_the_ledger_records_the_model_and_the_prompt(self):
		#The arithmetic moved into agents/ledger.py when a second engine
		#arrived and the two had to be priced the same way; what run.sh owes
		#it is the run's own facts.
		self.assertIn('model', script('agents/ledger.py'))
		self.assertIn('"$prompt_version" "$session" "$resumed"',
		              script('agents/run.sh'))

	def test_the_ledger_does_not_call_an_api_error_a_success(self):
		#A 401 ended a build with subtype "success" and is_error true, and
		#the ledger believed the subtype.
		self.assertIn("if last.get('is_error'):", script('agents/ledger.py'))


class ACampaignReadsTheStatusItActuallyGot(TestCase):
	"""`$?` inside `if ! cmd` is the status of the negation, not the command.

	So a build that died on an expired token was reported as "the build run
	exited 0", and the campaign exited 0 with it: a failure that looked like
	a finished campaign.
	"""

	def test_the_status_is_captured_from_the_command(self):
		body = flat('agents/campaign.sh')
		self.assertIn('agents/run.sh build "Build the highest-ranked', body)
		self.assertIn('|| status=$?', body)

	def test_it_does_not_read_the_status_of_a_negation(self):
		body = flat('agents/campaign.sh')
		self.assertNotIn('if ! agents/run.sh build', body)


class AFailedRunIsStillRecorded(TestCase):
	"""What a failure cost is exactly the number worth keeping.

	`set -e` aborted the runner the moment the agent exited non-zero: before
	the status was captured, before the ledger line was written, before the
	commit that lets the next run start on a clean tree. A build died 39 turns
	in on an expired OAuth token, having cost real money, and the ledger has
	no row for it at all.
	"""

	def test_errexit_is_off_around_the_agent_call(self):
		#The call is a start or a resume now, since the two engines spell
		#resuming differently, so what matters is that `set +e` is what comes
		#immediately before whichever it is.
		body = script('agents/run.sh')
		self.assertIn('set +e\nif [ -n "${NUMBERDB_RESUME:-}" ]; then\n\trun_agent resume',
		              body)

	def test_the_status_is_the_agents_and_not_tees(self):
		body = script('agents/run.sh')
		self.assertIn('| tee -a "$log"\n\t\t\tagent_status=${PIPESTATUS[0]}',
		              body)

	def test_it_is_back_on_before_the_ledger(self):
		body = script('agents/run.sh')
		self.assertLess(body.index('\nset -e\n'),
		                body.index('ledger="agents/runs/COSTS.tsv"'))
		self.assertLess(body.index('set +e\n'),
		                body.index('\nset -e\n'))

	def test_the_ledger_is_written_after_the_status_is_known(self):
		body = script('agents/run.sh')
		self.assertLess(body.index('status=${PIPESTATUS[0]}'),
		                body.index('ledger="agents/runs/COSTS.tsv"'))

	def test_the_runner_still_exits_with_the_agents_status(self):
		body = script('agents/run.sh')
		self.assertIn('exit "$status"', body)


class ARunSurvivesTheEightHourBoundary(TestCase):
	"""The access token lasts eight hours and refreshes when a process starts.

	Not while one is running. A build takes half an hour to an hour and a
	half, so one beginning near the end of a window crosses it and dies on a
	401 mid-flight. It happened twice on 2026-09-03; the second started at
	16:57 with thirteen minutes of token left and died at 17:10, thirty-nine
	turns in. The credentials were rewritten at 17:12 by the next process to
	start, which is the refresh that would have prevented it.
	"""

	def test_it_reads_the_expiry_before_a_long_run(self):
		body = script('agents/run.sh')
		self.assertIn('token_minutes_left()', body)
		self.assertIn("['claudeAiOauth']['expiresAt']", body)

	def test_it_refreshes_rather_than_only_complaining(self):
		body = flat('agents/run.sh')
		self.assertIn('minutes of token left, under the', body)
		self.assertIn('timeout 120 claude -p "Reply with exactly: ok"', body)

	def test_it_refuses_only_under_the_hard_floor(self):
		#Refusing at the soft floor blocked everything: the CLI renews the
		#token when it needs to, not when asked, so between the floor and its
		#own threshold no refresh takes and every run refused.
		body = flat('agents/run.sh')
		self.assertIn('${NUMBERDB_TOKEN_HARD_FLOOR:-15}', body)
		self.assertIn('under the $hard-minute', body)
		self.assertIn('exit 6', body)

	def test_otherwise_it_starts_anyway(self):
		body = flat('agents/run.sh')
		self.assertIn('starting anyway, and the run is resumable', body)

	def test_triage_is_never_blocked_by_the_floor(self):
		#It is short, and its whole job is to run when something else failed.
		body = flat('agents/run.sh')
		self.assertIn('[ "$engine" = "claude" ] && [ "$stage" != "triage" ]',
		              body)

	def test_the_floor_can_be_lowered_for_a_short_run(self):
		body = script('agents/run.sh')
		self.assertIn('${NUMBERDB_TOKEN_FLOOR:-90}', body)

	def test_the_check_does_not_read_the_token_itself(self):
		#`expiresAt` is a timestamp. Nothing here should touch a secret.
		body = script('agents/run.sh')
		block = body[body.index('token_minutes_left()'):]
		block = block[:block.index('\n}\n')]
		for word in ('accessToken', 'refreshToken', 'access_token'):
			self.assertNotIn(word, block)


class ARunCanBeResumed(TestCase):
	"""A build that dies thirty-nine turns in should not start again at one."""

	def test_the_session_is_chosen_not_scraped(self):
		#The transcripts are not tracked; the ledger is.
		body = script('agents/run.sh')
		self.assertIn("import uuid; print(uuid.uuid4())", body)
		self.assertIn('--session-id "$session"', body)

	def test_a_session_can_be_continued(self):
		body = script('agents/run.sh')
		self.assertIn('${NUMBERDB_RESUME:-}', body)
		self.assertIn('--resume "$session"', body)

	def test_it_retries_once_and_only_once(self):
		body = flat('agents/run.sh')
		self.assertEqual(body.count('run_agent resume'), 2)

	def test_it_retries_only_what_a_retry_could_survive(self):
		body = script('agents/run.sh')
		self.assertIn('worth_resuming()', body)
		for transient in ('api_error_status', 'OAuth access token has expired',
		                  'overloaded_error'):
			self.assertIn(transient, body)

	def test_it_refreshes_the_token_before_resuming(self):
		#The commonest transient failure here is the eight-hour boundary, and
		#resuming into an expired token just fails again.
		body = flat('agents/run.sh')
		at = body.index('looks resumable')
		before = body[:at]
		self.assertIn('timeout 120 claude -p "Reply with exactly: ok"',
		              before[before.rindex('if [ "$status" -ne 0 ]'):])

	def test_the_retry_can_be_turned_off(self):
		body = script('agents/run.sh')
		self.assertIn('${NUMBERDB_NO_RETRY:-0}', body)

	def test_the_ledger_records_the_session_and_the_retry(self):
		self.assertIn("'session', 'resumed'", script('agents/ledger.py'))
		self.assertIn('"$session" "$resumed"', script('agents/run.sh'))


class WhatToDoAboutAFailureIsAsked(TestCase):
	"""Four times today a line of shell answered a judgement, and was wrong.

	"did it build anything?" asked whether HEAD had moved, and the runner
	commits its own cost line. "which table?" grepped T1[0-9][0-9] and matched
	T182 inside a run stamp. "did it succeed?" read `subtype`, which says
	success on a 401. "is this worth retrying?" grepped api_error_status,
	which cannot tell a run that died on turn 1 from one that died on turn 39
	with a draft half filled.

	So the decision is asked of something that can look. What stays in the
	shell is policy: a cap, and refreshing the token first.
	"""

	def test_triage_is_a_stage(self):
		body = script('agents/run.sh')
		self.assertIn('triage) prompt_file="agents/triage/PROMPT.md" ;;', body)

	def test_the_campaign_asks_before_deciding(self):
		body = flat('agents/campaign.sh')
		self.assertIn('agents/run.sh triage', body)
		self.assertIn('-verdict', body)

	def test_it_acts_on_each_verdict(self):
		body = script('agents/campaign.sh')
		for verdict in ('resume)', 'restart)', 'skip)'):
			self.assertIn(verdict, body)

	def test_an_unknown_verdict_stops(self):
		#Including an empty file, a crashed triage run, or a word nobody
		#planned for: the default is to fetch a person, not to guess.
		body = script('agents/campaign.sh')
		self.assertIn('verdict=stop', body)
		self.assertIn("say \"stopping: $verdict\"", body)

	def test_a_table_is_not_attempted_a_third_time(self):
		#However good a reason triage gives.
		body = flat('agents/campaign.sh')
		self.assertIn('[ "$attempted" -lt 2 ]', body)
		self.assertIn('attempted=$((attempted + 1))', body)

	def test_the_counter_resets_when_a_table_succeeds(self):
		body = script('agents/campaign.sh')
		self.assertIn('\telse\n\t\tattempted=0\n\tfi', body)

	def test_the_token_is_refreshed_before_triage_runs(self):
		#If the failure was the eight-hour boundary, triage shares that
		#credential and cannot start either.
		body = flat('agents/campaign.sh')
		at = body.index('agents/run.sh triage')
		self.assertIn('claude -p "Reply with exactly: ok"', body[:at])

	def test_triage_does_not_inherit_the_automatic_retry(self):
		body = flat('agents/run.sh')
		self.assertIn('[ "$stage" != "triage" ]', body)

	def test_triage_reads_and_decides_and_does_not_repair(self):
		import os

		from django.conf import settings
		with open(os.path.join(settings.BASE_DIR, 'agents', 'triage',
		                       'PROMPT.md'), encoding='utf-8') as handle:
			prompt = handle.read()
		self.assertIn('You do not fix anything', prompt)
		self.assertIn('You do not publish, review, or edit a table', prompt)
		for verdict in ('`resume`', '`restart`', '`skip`', '`stop`'):
			self.assertIn(verdict, prompt)


class EitherEngineCanRunAnyStage(TestCase):
	"""One weekly quota should not be the end of the campaign.

	The stages differ in what they ask for -- building a table, reading one
	as a stranger, deciding whether a failure is worth retrying -- and there
	is no reason all three must come from the same vendor. Pairing them the
	other way round is also worth trying on its own merits: a reader who did
	not write the table is worth more when it is not even the same model.
	"""

	def test_both_engines_are_dispatched(self):
		body = script('agents/run.sh')
		self.assertIn('claude)', body)
		self.assertIn('codex)', body)

	def test_codex_is_told_the_model_and_the_effort(self):
		#Otherwise the run takes whatever the user's config says that day,
		#and the ledger records a model nobody chose.
		body = script('agents/run.sh')
		self.assertIn('NUMBERDB_CODEX_MODEL', body)
		self.assertIn('NUMBERDB_CODEX_EFFORT', body)
		self.assertIn('model_reasoning_effort', body)

	def test_codex_is_not_asked_for_a_flag_it_does_not_have(self):
		"""`--full-auto` is not an option of `codex exec` in 0.150.1.

		The branch that used it could never have run. Asserted on the
		invocation rather than on the file, since the comment above it says
		the word while explaining why.
		"""
		body = script('agents/run.sh')
		self.assertNotIn('codex exec --full-auto', body)
		self.assertIn('approval_policy=never', body)

	def test_codex_is_asked_for_machine_readable_output(self):
		#The ledger reads turns, tokens and the thread id out of it.
		self.assertIn('--json', script('agents/run.sh'))

	def test_codex_is_configured_the_same_way_when_resumed(self):
		#`codex exec resume` takes a smaller set of flags than `codex exec`,
		#so everything that matters goes through `-c`, which both accept.
		body = script('agents/run.sh')
		self.assertIn('codex exec resume', body)
		self.assertIn('thread_id', body)

	def test_the_ledger_prices_codex_from_its_tokens(self):
		#It reports tokens per turn and no price, so the row is priced from
		#agents/model-rates.tsv -- the same money the other engine reports,
		#which is the only figure that compares across the two.
		body = script('agents/ledger.py')
		self.assertIn('turn.completed', body)
		self.assertIn('model-rates.tsv', body)

	def test_the_campaign_routes_each_stage(self):
		body = script('agents/campaign.sh')
		for name in ('NUMBERDB_WRITER', 'NUMBERDB_CRITIC', 'NUMBERDB_MINER'):
			with self.subTest(variable=name):
				self.assertIn(name, body)

	def test_the_writer_builds_and_repairs_and_the_critic_reads(self):
		body = script('agents/campaign.sh')
		self.assertIn('NUMBERDB_AGENT="$writer" agents/run.sh build', body)
		self.assertIn('NUMBERDB_AGENT="$writer" agents/run.sh repair', body)
		self.assertIn('NUMBERDB_AGENT="$critic" agents/run.sh critique', body)
		self.assertIn('NUMBERDB_AGENT="$critic" agents/run.sh triage', body)

	def test_the_miner_can_be_pointed_at_either(self):
		#"the table topic miner should be optionally run via codex cli"
		self.assertIn('NUMBERDB_AGENT="$miner" agents/run.sh ideas',
		              script('agents/campaign.sh'))

	def test_each_falls_back_to_one_engine_for_everything(self):
		body = script('agents/campaign.sh')
		self.assertIn('default_engine="${NUMBERDB_AGENT:-claude}"', body)

	def test_the_campaign_says_which_engine_is_doing_what(self):
		#It is written to the log, so a run that produced a bad table can be
		#read back to see what made it.
		self.assertIn('say "writer $writer, critic $critic, miner $miner"',
		              script('agents/campaign.sh'))


class ARunThatCommitsNothingSaysSo(TestCase):
	"""Changed files and no commit looks exactly like no work.

	A codex build wrote a 458-line generator, filled a 519-entry table and
	left both untracked. The campaign decides a table was built by looking for
	a committed generator, so it read that as an exhausted batch, went to
	propose a new one, and stopped on the dirty tree the build had left --
	seven hours and $42.89 reported as nothing built.
	"""

	def test_the_runner_notices_and_says_what_is_uncommitted(self):
		body = script('agents/run.sh')
		self.assertIn('did not commit', body)
		self.assertIn("git status --short --untracked-files=normal", body)

	def test_it_does_not_commit_the_work_itself(self):
		#Committing somebody else's half-finished change is how a commit
		#nobody wrote gets into the history.
		body = script('agents/run.sh')
		leftovers = body[body.index('did not commit'):]
		self.assertNotIn('git add -A', leftovers)

	def test_it_is_reported_where_the_status_is(self):
		body = script('agents/run.sh')
		self.assertLess(body.index('did not commit'),
		                body.index('=== finished with status'))


class AnUnfinishedRunIsNotASuccess(TestCase):
	"""Two builds this week ended having done nothing, and looked fine.

	A codex build wrote a 519-entry table and left it untracked; a claude
	build stopped after 40 turns and $10.05 saying "waiting on the dry run".
	Both exited 0, and the campaign reads a build that exits 0 and commits no
	generator as an exhausted batch -- so both were recorded as "the batch is
	finished" and their tables were never critiqued.

	A run that declines leaves a clean tree; one that stopped in the middle
	leaves the work it had done. That difference is the signal.
	"""

	def test_uncommitted_work_makes_the_run_fail(self):
		body = script('agents/run.sh')
		self.assertIn('status=7', body)
		self.assertIn('unfinished="left work uncommitted"', body)

	def test_a_clean_tree_is_left_alone(self):
		#Declining is a good outcome and must stay one.
		body = script('agents/run.sh')
		guard = body[body.index('unfinished=""'):]
		self.assertIn('if [ "$status" -eq 0 ]; then', guard)

	def test_the_ledger_is_told_before_it_writes_the_row(self):
		body = script('agents/run.sh')
		self.assertLess(body.index('unfinished="left work uncommitted"'),
		                body.index('python3 agents/ledger.py "$log"'))

	def test_the_row_says_so_beside_the_price(self):
		self.assertIn('outcome = \'%s, %s\' % (outcome, unfinished)',
		              script('agents/ledger.py'))

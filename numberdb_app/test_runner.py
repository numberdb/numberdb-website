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
		self.assertIn('NUMBERDB_ASSISTED_BY="$engine', body)
		self.assertNotIn('NUMBERDB_ASSISTED_BY="assisted by', body)

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

	def test_the_campaign_stops_if_stage_one_commits_nothing(self):
		#Otherwise it would spin between two runs that each do nothing.
		self.assertIn('committed nothing either', script('agents/campaign.sh'))

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

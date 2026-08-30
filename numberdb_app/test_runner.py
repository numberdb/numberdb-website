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

	def test_the_runner_needs_a_key_file_rather_than_a_key(self):
		body = script('agents/run.sh')
		self.assertIn('NUMBERDB_KEY_FILE', body)
		self.assertNotIn('NUMBERDB_API_KEY=', body)

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

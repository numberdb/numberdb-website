"""The pipeline's scope, its digest and its version numbering.

    python3 agents/test_pipeline.py

Everything here is about *this* repository, because that is what the module
reads: the manifests in agents/pipelines and the commits that touched them. So
the assertions are about shape and about the rules -- what changes a digest,
what makes a new version, what a label parses back into -- rather than about
any particular value, which would have to be edited every time a prompt does.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pipeline as p  # noqa: E402  (the file under test)


class TheManifestIsTheScope(unittest.TestCase):

	def test_every_pipeline_declares_files_that_exist(self):
		#A manifest naming a file that is not there would hash `<absent>` for
		#ever and nobody would notice, since the digest still changes when the
		#others do.
		for name in p.names():
			found = p.manifest(name)
			self.assertTrue(found['files'], name)
			for path in found['files']:
				self.assertTrue(
					os.path.exists(os.path.join(p.ROOT, path)),
					'%s names %s, which does not exist' % (name, path))

	def test_the_six_stages_of_a_campaign_all_have_one(self):
		#`run.sh` maps these stage names to prompts; a stage with no manifest
		#records no version, which is the hole this was built to close.
		for name in ('table-build', 'table-critique', 'table-repair',
		             'table-ideas', 'table-split', 'triage'):
			self.assertIn(name, p.names())

	def test_the_manifest_is_part_of_its_own_digest(self):
		#Changing which files are in scope changes the pipeline. A digest that
		#covered only the listed files would call that the same version.
		name = 'triage'
		found = p.manifest(name)
		self.assertIn(found['path'],
		              [path for path, _size in p.digest(name)[1]])


class WhatADigestMeans(unittest.TestCase):

	def test_the_digest_is_stable_and_eight_hex_of_it_is_the_label(self):
		name = 'table-build'
		first, _ = p.digest(name)
		second, _ = p.digest(name)
		self.assertEqual(first, second)
		self.assertEqual(len(first), 64)
		self.assertTrue(p.label(name).endswith('+' + first[:8]))

	def test_two_pipelines_that_share_files_still_differ(self):
		#They all include run.sh and most include the skill; a scheme that
		#hashed only the shared parts would give them one version.
		digests = {name: p.digest(name)[0] for name in p.names()}
		self.assertEqual(len(set(digests.values())), len(digests))

	def test_a_label_parses_back_into_its_parts(self):
		name, major, minor, sha = p.resolve('table-build@2.7+9f3ac1d2')
		self.assertEqual((name, major, minor, sha),
		                 ('table-build', '2', '7', '9f3ac1d2'))

	def test_a_label_without_a_digest_still_parses(self):
		#What a person types by hand, which the site records as `declared`
		#rather than as `run`.
		name, major, minor, sha = p.resolve('table-build')
		self.assertEqual((name, sha), ('table-build', ''))


class WhatAVersionMeans(unittest.TestCase):

	def setUp(self):
		self.past = p.history('table-build')

	def test_a_version_per_distinct_digest_in_commit_order(self):
		digests = [entry[2] for entry in self.past]
		self.assertEqual(len(digests), len(set(digests)),
		                 'a digest was numbered twice')
		whens = [entry[4] for entry in self.past]
		self.assertEqual(whens, sorted(whens))

	def test_the_minor_counts_within_its_major_and_restarts(self):
		seen = {}
		for major, minor, _sha, _commit, _when in self.past:
			self.assertEqual(minor, seen.get(major, 0),
			                 'minor %s.%d is out of order' % (major, minor))
			seen[major] = minor + 1
		#And the shape change is real: this pipeline has had two majors, the
		#second beginning where the four sources of work replaced the queue.
		self.assertEqual(sorted(seen), ['1', '2'])

	def test_the_major_is_the_one_declared_for_that_commit(self):
		#Not today's. Stamping the whole history with the current major would
		#say the pipeline never changed shape.
		first = self.past[0]
		self.assertEqual(first[0], '1')
		self.assertEqual(self.past[-1][0], '2')

	def test_the_history_ends_at_what_the_label_says_now(self):
		#Unless the working tree is dirty in scope, in which case the label is
		#the next minor and the digest says which state it really was -- so the
		#two agree on the major and on the name either way.
		name, major, _minor, _sha = p.resolve(p.label('table-build'))
		self.assertEqual(name, 'table-build')
		self.assertEqual(major, self.past[-1][0])


if __name__ == '__main__':
	unittest.main(verbosity=1)

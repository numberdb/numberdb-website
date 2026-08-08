"""Tests for the API reference.

One of these is the point. The help page documented three endpoints and had
gone on doing so while five more were built: it never mentioned /api/lookup,
/api/tables, entries, leases or files, and nothing noticed, because nothing
could. Documentation drifts silently by construction -- nothing fails when it
falls behind.

So the reference is hand-written, since these are plain Django views with no
schema to introspect, and its *coverage* is not: every route named `api-...`
must have a section here, and adding an endpoint without documenting it fails.
"""

from django.test import TestCase
from django.urls import get_resolver


def api_route_names():
	"""Every URL name the API defines."""
	names = set()
	for name in get_resolver().reverse_dict:
		if isinstance(name, str) and name.startswith('api-'):
			names.add(name)
	#Namespaced under `db:`, so the resolver's plain names may be empty; walk
	#the patterns as well rather than depending on how they were registered.
	from numberdb_app import urls as app_urls

	for pattern in app_urls.urlpatterns:
		name = getattr(pattern, 'name', None)
		if name and name.startswith('api-'):
			names.add(name)
	return names


class EveryEndpointIsDocumented(TestCase):

	def setUp(self):
		self.page = self.client.get('/api/docs').content.decode('utf8')

	def test_the_reference_renders(self):
		self.assertEqual(self.client.get('/api/docs').status_code, 200)

	def test_there_are_endpoints_to_check(self):
		"""So a broken discovery cannot make the next test pass vacuously."""
		self.assertGreaterEqual(len(api_route_names()), 9)

	def test_every_api_route_has_a_section(self):
		"""Add an endpoint without documenting it and this fails."""
		missing = sorted(name for name in api_route_names()
		                 if 'id="endpoint-%s"' % (name,) not in self.page)
		self.assertEqual(missing, [], 'undocumented endpoints: %s' % (missing,))

	def test_nothing_is_documented_that_does_not_exist(self):
		"""A reference to a removed endpoint is worse than none at all."""
		import re

		documented = set(re.findall(r'id="endpoint-([\w-]+)"', self.page))
		gone = sorted(documented - api_route_names())
		self.assertEqual(gone, [], 'documented but not routed: %s' % (gone,))


class ItSaysTheThingsACallerNeeds(TestCase):

	def setUp(self):
		self.page = self.client.get('/api/docs').content.decode('utf8')

	def test_it_shows_how_to_send_a_key(self):
		self.assertIn('Authorization: Bearer', self.page)

	def test_it_says_writing_needs_a_track_record(self):
		from .permissions import TRUSTED_AFTER

		self.assertIn(str(TRUSTED_AFTER), self.page)

	def test_the_limits_come_from_the_code(self):
		"""Numbers written by hand are numbers that go stale."""
		from .api import MAX_ATTACHMENT_BYTES

		self.assertIn(str(MAX_ATTACHMENT_BYTES // 1024), self.page)

	def test_it_documents_the_headers_that_change_behaviour(self):
		for header in ('X-Entries-Mode', 'X-Run-Id', 'X-Base-Revision',
		               'X-Produced-By'):
			self.assertIn(header, self.page, header)

	def test_it_is_reachable_from_the_help_page(self):
		self.assertContains(self.client.get('/help'), '/api/docs')


class TheHelpPageNamesRealPackageThings(TestCase):
	"""Every `numberdb.Something` the help page mentions must still exist.

	The page said the package raises `numberdb.RateLimited` for a while after
	that class had been renamed, and nothing noticed -- the same silent drift
	this module was written for, one repository over. The client is a separate
	distribution, so this reads its `__all__` from the source rather than
	importing it: `import numberdb` inside the site finds the Django project
	package of that name, not the client.
	"""

	def public_names(self):
		import ast
		import pathlib

		root = pathlib.Path(__file__).resolve().parent.parent
		source = (root / 'clients' / 'python' / 'numberdb' / '__init__.py')
		if not source.exists():
			self.skipTest('the client package is not in this checkout')
		tree = ast.parse(source.read_text())
		for node in tree.body:
			if isinstance(node, ast.Assign) and any(
					getattr(target, 'id', '') == '__all__'
					for target in node.targets):
				return set(ast.literal_eval(node.value))
		self.fail('the client package has no __all__')

	def mentioned(self):
		"""Package names the page uses, from its code spans only.

		Prose says numberdb.org, which is a domain and not an attribute.
		"""
		import pathlib
		import re

		page = (pathlib.Path(__file__).resolve().parent / 'templates'
		        / 'help.html').read_text()
		code = re.findall(r'<code[^>]*>(.*?)</code>', page, re.S)
		code += re.findall(r'<pre[^>]*>(.*?)</pre>', page, re.S)
		found = set()
		for span in code:
			found.update(re.findall(r'\bnumberdb\.([A-Za-z_][A-Za-z_0-9]*)',
			                        span))
		return found

	def test_they_all_exist(self):
		names = self.public_names()
		for mentioned in sorted(self.mentioned()):
			with self.subTest(name=mentioned):
				self.assertIn(mentioned, names)

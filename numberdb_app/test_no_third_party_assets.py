"""No page may fetch anything from a third party.

A stylesheet, script, font or image loaded from another host is fetched by the
visitor's browser, which means that host learns their IP address, the page they
were reading and when -- before they have clicked anything and without being
asked. Four such embeds were live at once here: Google Fonts on *every* page,
MathJax and highlight.js from jsDelivr, and a Materialize bundle from Cloudflare
that no page even used.

This is what makes the privacy policy's "nothing you do here is reported to
anyone else" a statement about the code rather than an intention. It is easy to
undo by pasting one line from a tutorial, which is why it is a test.

Ordinary links are fine and are not checked: an <a href> to Wikipedia is
followed only if the reader chooses to, which is the whole difference.
"""

import os
import re

from django.conf import settings
from django.test import TestCase

#Attributes the browser fetches on its own, without being asked. `preconnect`
#and `dns-prefetch` count: they exist precisely to open the connection early,
#so they leak the visit even when nothing is downloaded.
FETCHING = re.compile(
	r"""<(?:link|script|img|iframe|audio|video|source|embed|object)\b[^>]*?"""
	r"""\b(?:src|href|data)\s*=\s*["'](?P<url>[^"']+)["']""",
	re.IGNORECASE | re.DOTALL)

#A URL that names a host other than this one: https://..., http://... or the
#protocol-relative //host/path.
REMOTE = re.compile(r'^\s*(?:https?:)?//', re.IGNORECASE)


def template_files():
	roots = [os.path.join(settings.BASE_DIR, 'templates'),
	         os.path.join(settings.BASE_DIR, 'numberdb_app', 'templates')]
	for root in roots:
		for folder, _subdirs, names in os.walk(root):
			for name in names:
				if name.endswith('.html'):
					yield os.path.join(folder, name)


def script_files():
	root = os.path.join(settings.BASE_DIR, 'static', 'js')
	for folder, _subdirs, names in os.walk(root):
		for name in names:
			#Only the site's own scripts. The vendored bundles are minified
			#third-party code whose *contents* mention all sorts of URLs
			#without fetching them.
			if name.endswith('.js') and '.min.' not in name:
				yield os.path.join(folder, name)


class NoThirdPartyAssets(TestCase):

	def test_no_template_fetches_from_another_host(self):
		offences = []
		for path in template_files():
			with open(path, encoding='utf-8') as handle:
				body = handle.read()
			#Django comments are the usual place to *describe* what was
			#removed, and describing it must not read as doing it.
			body = re.sub(r'{%\s*comment\s*%}.*?{%\s*endcomment\s*%}', '',
			              body, flags=re.DOTALL)
			body = re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL)
			for match in FETCHING.finditer(body):
				url = match.group('url')
				if REMOTE.match(url):
					offences.append('%s: %s'
					                % (os.path.basename(path), url))
		self.assertEqual(offences, [], 'templates fetching from third parties:'
		                 '\n  ' + '\n  '.join(offences))

	def test_no_script_of_ours_loads_a_remote_bundle(self):
		"""The check above reads markup, and would not have caught the way
		MathJax was loaded: a script element built in JavaScript."""
		offences = []
		for path in script_files():
			with open(path, encoding='utf-8') as handle:
				body = handle.read()
			body = re.sub(r'//[^\n]*', '', body)          # line comments
			body = re.sub(r'/\*.*?\*/', '', body, flags=re.DOTALL)
			for url in re.findall(r'''["'](https?://[^"']+)["']''', body):
				offences.append('%s: %s' % (os.path.basename(path), url))
		self.assertEqual(offences, [], 'scripts loading from third parties:'
		                 '\n  ' + '\n  '.join(offences))

	def test_the_fonts_stylesheet_is_self_contained(self):
		path = os.path.join(settings.BASE_DIR, 'static', 'css', 'fonts.css')
		with open(path, encoding='utf-8') as handle:
			body = handle.read()
		body = re.sub(r'/\*.*?\*/', '', body, flags=re.DOTALL)
		remote = [url for url in re.findall(r'url\(([^)]*)\)', body)
		          if REMOTE.match(url.strip('"\''))]
		self.assertEqual(remote, [])

	def test_and_the_font_files_it_names_are_actually_here(self):
		"""Self-hosted fonts that 404 fall back to a system face silently, so
		nothing looks broken enough to notice."""
		root = os.path.join(settings.BASE_DIR, 'static', 'css')
		with open(os.path.join(root, 'fonts.css'), encoding='utf-8') as handle:
			body = handle.read()
		names = re.findall(r'url\((\.\./fonts/[^)]+)\)', body)
		self.assertTrue(names, 'no @font-face url() found at all')
		for name in names:
			with self.subTest(font=name):
				self.assertTrue(os.path.exists(os.path.join(root, name)),
				                '%s is referenced but missing' % (name,))

	def test_the_vendored_bundles_are_present(self):
		for relative in ('vendor/mathjax/tex-svg.js',
		                 'vendor/highlight/highlight.min.js',
		                 'vendor/highlight/python.min.js',
		                 'vendor/highlight/default.min.css'):
			with self.subTest(file=relative):
				path = os.path.join(settings.BASE_DIR, 'static', *relative.split('/'))
				self.assertTrue(os.path.exists(path), '%s is missing' % (relative,))
				self.assertGreater(os.path.getsize(path), 500)

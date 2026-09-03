"""Make a session edit the way every other writer does: over the API.

    from agents.api_edit import edit_over_api
    edit_over_api('T130', tree, 'what changed and why')

Until now an edit made in a conversation called `commit_table` from a shell on
the server. That works, and it walks past the permission checks, the rate
limits and the validation that a key-holder goes through -- and it had to
record `via='orm'`, which is honest but says "this one did not take the door
everybody else takes". bmatschke has a key now, so it can.

What the server records follows from the request rather than from what the
caller claims: `via` comes from the client header, `produced_by` from
`X-Produced-By`. This sends `assisted by <engine>`, because a reader is
entitled to know a program was involved and because `accepted_edit_count`
reads that phrase when deciding what a track record is worth.

The key is never an argument and never printed. It comes from a file, and the
default is the per-account file beside zeta3's.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

__all__ = ['edit_over_api', 'edit_request', 'read_key', 'ApiRefused']

#: Where bmatschke's key lives. `agents/run.sh` uses the same directory for
#: zeta3's, one file per account, so revoking one leaves the other alone.
DEFAULT_KEY_FILE = '~/.config/numberdb/bmatschke-key'

#: What to record when a session does not say which assistant it is.
DEFAULT_ASSISTANT = 'an assistant'

#: The model caps a revision message at 300 characters. Truncating here rather
#: than letting Postgres refuse the insert: a message is a courtesy and losing
#: its tail is better than losing the edit, which is what happened once.
MESSAGE_LIMIT = 300

_PROXY_READY = False


class ApiRefused(Exception):
	"""The API answered something other than success."""

	def __init__(self, status, body):
		self.status = status
		self.body = body
		super(ApiRefused, self).__init__(
			'the API answered %s: %s' % (status, body))


def use_socks_proxy_if_set():
	"""Route urllib through ALL_PROXY when it names a SOCKS proxy.

	numberdb.org is unreachable from here except through the proxy, and
	`urllib` does not honour ALL_PROXY on its own. The same bootstrap as
	`agents/table-ideas/screen.py`, for the same reason: without it curl
	answers 200 and Python times out.
	"""
	global _PROXY_READY
	if _PROXY_READY:
		return
	url = os.environ.get('ALL_PROXY', '')
	if not url.startswith('socks'):
		_PROXY_READY = True
		return
	try:
		import socket

		import socks                                  # PySocks
	except ImportError:
		_PROXY_READY = True
		return
	parsed = urllib.parse.urlparse(url)
	socks.set_default_proxy(socks.SOCKS5, parsed.hostname, parsed.port or 1080,
	                        rdns=url.startswith('socks5h'))
	socket.socket = socks.socksocket
	for name in ('ALL_PROXY', 'all_proxy', 'HTTP_PROXY', 'http_proxy',
	             'HTTPS_PROXY', 'https_proxy'):
		os.environ.pop(name, None)
	_PROXY_READY = True


def read_key(path=None):
	"""The token, from its file. Never logged, never an argument."""
	path = os.path.expanduser(path or os.environ.get('NUMBERDB_KEY_FILE')
	                          or DEFAULT_KEY_FILE)
	with open(path, 'r', encoding='utf8') as handle:
		token = handle.read().strip()
	if not token:
		raise ValueError('no key in %s' % (path,))
	#A key file written as `NAME=value` -- which is what the Python package
	#reads -- rather than as a bare token. Both shapes live in that directory,
	#and telling somebody "the key is empty" when it is right there is a poor
	#way to spend an evening.
	if '=' in token and token.split('=', 1)[0].isupper():
		token = token.split('=', 1)[1].strip().strip('\'"')
	return token


def edit_request(tid, tree, message, assistant=DEFAULT_ASSISTANT, base=None,
                 host='https://numberdb.org'):
	"""The URL, headers and body of one session edit.

	Built apart from sending it so that what goes over the wire can be
	asserted in a test without a server, and read here without running
	anything.
	"""
	import yaml

	headers = {
		'Content-Type': 'application/yaml',
		'X-Edit-Message': (message or '')[:MESSAGE_LIMIT],
		#Begins with `assisted by`, which is the phrase the trust counter
		#looks for. Capped at 100 by the model.
		'X-Produced-By': ('assisted by %s'
		                  % (assistant or DEFAULT_ASSISTANT).strip())[:100],
	}
	if base:
		#So a change that landed since the document was read is refused with a
		#409 rather than silently overwritten.
		headers['X-Base-Revision'] = base
	body = yaml.dump(tree, sort_keys=False, allow_unicode=True).encode('utf8')
	url = '%s/api/table/%s' % (host.rstrip('/'), tid)
	return url, headers, body


def edit_over_api(tid, tree, message, assistant=DEFAULT_ASSISTANT, base=None,
                  key_file=None, host='https://numberdb.org', opener=None):
	"""Commit `tree` as the key's owner, through the API. Returns the reply."""
	use_socks_proxy_if_set()
	url, headers, body = edit_request(tid, tree, message, assistant, base, host)
	headers['Authorization'] = 'Bearer %s' % (read_key(key_file),)

	request = urllib.request.Request(url, data=body, headers=headers,
	                                 method='POST')
	send = opener or urllib.request.urlopen
	try:
		with send(request, timeout=180) as response:
			return json.loads(response.read().decode('utf8') or '{}')
	except urllib.error.HTTPError as refused:
		detail = refused.read().decode('utf8', 'replace')[:800]
		raise ApiRefused(refused.code, detail)

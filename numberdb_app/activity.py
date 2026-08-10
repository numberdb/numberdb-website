"""What the server records about how it is being used.

Two logs, with different purposes, kept apart on purpose.

``numberdb.api`` -- one line per request to ``/api/*``: which endpoint, what
came back, how long it took, which key or account was asking, and what the
caller said it was. That last part is why this exists at all. The API is used
by scripts that run for hours, and when a field changes the only way to know
what breaks is to know which client versions are actually out there. The
``numberdb`` package announces itself as ``numberdb-python/0.1.0``, so the
versions in use are readable straight off this log.

``numberdb.edit`` -- one line per revision written, by anyone, through any
route. The numbers are the point of the site and their provenance is already
in the database; this is the operational view of the same thing, which is what
you want at three in the morning when a table looks wrong and the question is
what happened to it recently.

**No IP addresses here.** nginx already logs those, for a different reason
(abuse, and knowing whether the machine is under load) and with its own short
retention. Recording them a second time, in a log kept for longer and for a
purpose that does not need them, would be collecting the same personal data
twice for one use.

Lines are JSON, one per line, to stdout, which is where Docker picks them up.
JSON because these get read by grep today and by something else later, and a
format that survives that is worth the punctuation.
"""

import json
import logging
import time

__all__ = ['ApiActivityMiddleware', 'record_revision', 'actor_of']

api_log = logging.getLogger('numberdb.api')
edit_log = logging.getLogger('numberdb.edit')

#: How much of the User-Agent to keep. Real clients say something short --
#: `numberdb-python/0.1.0`, `curl/8.4.0`. Browsers say a paragraph, and a
#: hostile caller can say a great deal more, which is a way to fill a disk.
USER_AGENT_LIMIT = 120


def actor_of(request):
	"""Who is asking, in a form safe to write down.

	Never the token. An API key is identified by its prefix, which is the same
	thing shown on the keys page -- enough for its owner to recognise it and
	for us to revoke the right one, and useless as a credential.
	"""
	key = getattr(request, 'numberdb_api_key', None)
	if key is not None:
		return 'key:%s' % (key.prefix,)
	user = getattr(request, 'user', None)
	if user is not None and user.is_authenticated:
		return 'user:%s' % (user.get_username(),)
	return 'anonymous'


def _emit(logger, **fields):
	#sort_keys so a line diffs against another line, and default=str so a
	#stray datetime can never turn logging into a 500.
	logger.info(json.dumps(fields, sort_keys=True, default=str))


class ApiActivityMiddleware:
	"""Log every ``/api/*`` request once it has been answered.

	Middleware rather than a decorator on each view, so that the things which
	never reach a view -- a 404 on a mistyped endpoint, a 403 from a rejected
	key, an exception -- are recorded too. Those are exactly the requests
	somebody writes in to ask about.
	"""

	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		if not request.path.startswith('/api/'):
			return self.get_response(request)

		started = time.monotonic()
		response = self.get_response(request)
		elapsed = time.monotonic() - started

		#After the response, so it sees the key the throttle authenticated
		#rather than authenticating it a second time.
		_emit(api_log,
		      event = 'api',
		      method = request.method,
		      path = request.path,
		      status = getattr(response, 'status_code', 0),
		      ms = int(elapsed * 1000),
		      actor = actor_of(request),
		      client = request.META.get('HTTP_USER_AGENT',
		                                '')[:USER_AGENT_LIMIT])
		return response


def record_revision(table, revision, produced_by=''):
	"""Note that a revision was written. Called once it is committed.

	Deliberately not called from inside the transaction: a line describing a
	revision that was then rolled back is worse than no line, because it is
	the log you would trust while looking for the thing that went wrong.
	"""
	author = getattr(revision, 'author', None)
	_emit(edit_log,
	      event = 'revision',
	      table = getattr(table, 'tid', None),
	      revision = getattr(revision, 'digest', None),
	      author = author.get_username() if author is not None else 'anonymous',
	      via = produced_by or 'web',
	      message = (getattr(revision, 'message', '') or '')[:200])

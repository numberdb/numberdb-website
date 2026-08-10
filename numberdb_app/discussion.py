"""Talking about a table, rather than only editing it.

The site had editing, history and review but no talk page, so two people who
disagreed about a digit had exactly two channels: overwrite each other, or
write to Benjamin. Neither leaves a record anyone else can read, which is the
part that matters -- most of what is worth saying about a number is *why*, and
a revision message has room for a sentence.

The models for this were designed some time ago and have been in the database,
unused, ever since. Nothing here changes them; what was missing was the pages.
Two decisions are theirs and worth repeating, because they look like
limitations and are not:

  * **One thread per table, not per entry.** Every entry already has a
    permanent anchor (``/T7#n=5``), so a comment can point at one precisely
    via ``about_param``. Ten thousand separately watchable, separately
    moderated threads buy very little and cost a great deal.
  * **Hidden, never deleted.** A removed message leaves a conversation full of
    replies to nothing, and moderation that cannot be undone is moderation
    nobody dares use.

Who may post: anybody who may edit the table. If you are trusted to change a
number, you are trusted to discuss it, and a second, different bar here would
only be a puzzle.
"""

import time

from django.core.cache import cache

from .permissions import is_board_member, may_edit

__all__ = ['thread_for', 'visible_comments', 'post_comment', 'edit_comment',
           'set_hidden', 'may_post', 'may_moderate', 'BODY_LIMIT',
           'PER_HOUR', 'TooManyComments']

#: Longest a single message may be. Generous for a paragraph of mathematics,
#: short of an essay, and far short of a way to fill a disk.
BODY_LIMIT = 4000

#: Messages per account per hour. Not a moderation tool -- it is what stops a
#: script, or a very bad afternoon, from producing a thousand of them.
PER_HOUR = 20


class TooManyComments(Exception):
	"""Raised when an account has posted its hourly allowance."""


def may_post(user, table):
	"""Whether ``user`` may add to this table's discussion.

	The same bar as editing, plus being able to see the table at all: a draft
	is visible only to its author, and its discussion must not be a way round
	that.
	"""
	from .editing import may_see

	return may_edit(user) and may_see(table, user)


def may_moderate(user):
	return is_board_member(user)


def thread_for(table, create=False):
	"""This table's thread, or None.

	Created on first use rather than with the table, so the great majority of
	tables -- which nobody has anything to say about -- carry no empty row.
	"""
	from .models import TableThread

	thread = TableThread.objects.filter(table=table).first()
	if thread is None and create:
		thread = TableThread.objects.create(table=table)
	return thread


def visible_comments(thread, viewer=None):
	"""The thread's messages, in order, as they should appear to ``viewer``.

	Hidden ones are kept in place, because a conversation with holes in it is
	harder to follow than one that says a message was removed. A moderator
	sees the text; everyone else sees that it is gone.
	"""
	if thread is None:
		return []

	moderating = may_moderate(viewer) if viewer is not None else False
	shown = []
	for comment in thread.comments.select_related('author').all():
		shown.append({
			'comment': comment,
			'body': comment.body if (moderating or not comment.hidden) else '',
			'hidden': comment.hidden,
			'is_own': (viewer is not None
			           and getattr(viewer, 'is_authenticated', False)
			           and comment.author_id == viewer.pk),
		})
	return shown


def _spent(user):
	return 'numberdb-comments:%d:%d' % (user.pk, int(time.time()) // 3600)


def post_comment(table, user, body, about_param=''):
	"""Add a message. Returns the Comment.

	Raises ValueError for an empty or oversized body and TooManyComments when
	the hourly allowance is gone.
	"""
	from .models import Comment

	body = (body or '').strip()
	if not body:
		raise ValueError('A message needs something in it.')
	if len(body) > BODY_LIMIT:
		raise ValueError('That message is longer than %d characters.'
		                 % (BODY_LIMIT,))

	key = _spent(user)
	cache.add(key, 0, 3600)
	try:
		used = cache.incr(key, 1)
	except ValueError:
		cache.set(key, 1, 3600)
		used = 1
	if used > PER_HOUR:
		raise TooManyComments(
			'That is %d messages in an hour. Try again shortly.'
			% (PER_HOUR,))

	thread = thread_for(table, create=True)
	comment = Comment.objects.create(
		thread = thread,
		author = user,
		body = body,
		about_param = (about_param or '')[:200],
	)
	_log(table, comment, 'posted')
	return comment


def edit_comment(comment, user, body):
	"""Change one's own message, stamping `edited` so the change is visible."""
	from django.utils import timezone

	if comment.author_id != user.pk:
		raise PermissionError('Only the author may change a message.')

	body = (body or '').strip()
	if not body:
		raise ValueError('A message needs something in it.')
	if len(body) > BODY_LIMIT:
		raise ValueError('That message is longer than %d characters.'
		                 % (BODY_LIMIT,))

	comment.body = body
	comment.edited = timezone.now()
	comment.save(update_fields=['body', 'edited'])
	_log(comment.thread.table, comment, 'edited')
	return comment


def set_hidden(comment, user, hidden):
	"""Hide or restore a message. Board only."""
	if not may_moderate(user):
		raise PermissionError('Only the board may hide a message.')
	comment.hidden = bool(hidden)
	comment.save(update_fields=['hidden'])
	_log(comment.thread.table, comment, 'hidden' if hidden else 'unhidden')
	return comment


def _log(table, comment, what):
	"""Onto the same activity log as edits.

	Discussion is the part of a site that goes wrong quietly -- a flood at
	three in the morning, one account arguing with itself -- and the first
	thing anybody asks is what happened and when.
	"""
	import json
	import logging

	author = getattr(comment, 'author', None)
	logging.getLogger('numberdb.edit').info(json.dumps({
		'event': 'comment',
		'action': what,
		'table': getattr(table, 'tid', None),
		'comment': comment.pk,
		'author': author.get_username() if author is not None else 'anonymous',
	}, sort_keys=True, default=str))

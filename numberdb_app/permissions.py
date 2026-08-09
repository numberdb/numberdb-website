"""Who may do what.

Three tiers, deliberately not two:

  * an **account** may edit. Edits publish immediately and are marked
    unreviewed, which is what keeps the barrier to contributing low while
    keeping unchecked digits out of search by number.
  * a **verified identity** is an account that has proved itself through a
    provider, ORCID in particular. It earns higher limits and a visible marker,
    and nothing else. An ORCID iD is free and self-registered with no
    institutional check, so treating it as trust would be a very thin gate on
    exactly the failure that matters.
  * the **board** may mark revisions reviewed, and its own edits are reviewed
    on save.

Board membership is a Django group rather than ``is_staff``, because staff is
Django's administrative flag and grants access to the admin site. Somebody who
can confirm a digit is not thereby somebody who should be able to delete a user.
"""

from django.contrib.auth.models import Group

__all__ = ['BOARD_GROUP', 'is_board_member', 'may_edit', 'board_group',
           'TRUSTED_AFTER', 'accepted_edit_count', 'is_trusted',
           'edits_are_reviewed', 'may_write_through_api',
           'may_create_tables_through_api']

#: Accepted edits after which an account is trusted. Five is enough to have
#: made and had confirmed a handful of real corrections, and few enough that
#: somebody working steadily reaches it in a week rather than a year.
TRUSTED_AFTER = 5

#: The group whose members may review.
BOARD_GROUP = 'board'


def board_group():
	"""The board group, created on first use so a fresh install has one."""
	group, _ = Group.objects.get_or_create(name=BOARD_GROUP)
	return group


def is_board_member(user):
	"""Whether ``user`` may mark work reviewed.

	A superuser counts, so that a new installation is not locked out of its own
	review queue before anybody has been added to the group.
	"""
	if not getattr(user, 'is_authenticated', False):
		return False
	if user.is_superuser:
		return True
	return user.groups.filter(name=BOARD_GROUP).exists()


def may_edit(user):
	"""Whether ``user`` may change a table.

	Any confirmed account. The protection against bad edits is that they are
	marked and held out of search by number until reviewed, not that people are
	kept from making them.
	"""
	return bool(getattr(user, 'is_authenticated', False))


def accepted_edit_count(user):
	"""How many of ``user``'s revisions a reviewer has since confirmed.

	Counted from review rather than from thumbs-up. A review is a statement
	about whether the digits are right, which is the thing trust here is
	about; approval is a statement about whether people liked the edit, and a
	script can farm it. It is also data the review queue already produces.

	A revision counts as accepted once its table has been reviewed at or after
	it, which is what `reviewed_at_revision` advancing means.
	"""
	from django.db.models import F

	from .models import TableRevision

	if not getattr(user, 'is_authenticated', False):
		return 0
	return TableRevision.objects.filter(
		author=user,
		table__reviewed_at_revision__isnull=False,
		created__lte=F('table__reviewed_at_revision__created'),
	).count()


def is_trusted(user):
	"""Whether ``user`` has a track record here.

	Board members are trusted by definition; they are the ones doing the
	confirming.
	"""
	if not getattr(user, 'is_authenticated', False):
		return False
	if is_board_member(user):
		return True
	return accepted_edit_count(user) >= TRUSTED_AFTER


def edits_are_reviewed(user):
	"""Whether this account's edits are published as already reviewed.

	Requiring a board member to review their own work would make a queue of
	one person's edits waiting for that same person; requiring it of somebody
	with a confirmed track record turns review into a formality that trains
	reviewers to click through. Everybody else waits, which is what keeps
	unchecked digits out of search by number.
	"""
	return is_trusted(user)


def may_write_through_api(user):
	"""Whether ``user`` may change tables with a program.

	Deliberately higher than `may_edit`. A person editing a table exercises
	judgement about one table; a script does not exercise judgement at all, and
	it writes at a speed no reviewer can follow. Requiring a track record first
	means a bulk writer is somebody whose individual edits have already been
	checked by a person -- and that track record is measured in accepted
	reviews, which is the one signal a script cannot manufacture for itself.
	"""
	return is_trusted(user)


def may_create_tables_through_api(user):
	"""Whether ``user`` may create *tables* with a program.

	Higher than writing to one, and for a different reason. Writing numbers to
	an existing table is bounded: somebody chose that the table should exist,
	wrote what it is, and fixed its parameters, and the worst a bad run does is
	fill it with wrong values that review catches and history reverts.

	Creating tables is not bounded. Each one is a permanent T-number, a title
	in every listing, a namespace whose parameter order can never be changed
	because citations resolve on it, and prose that no reviewer wrote. A loop
	that means to make three and makes three hundred leaves three hundred of
	those, and reverting a table's existence is not something the history model
	does.

	So: board members. Everybody else creates tables on the site, one at a
	time, through a form -- which is the pace the decision deserves, since what
	is being decided is not a number but what a table *is*.
	"""
	return is_board_member(user)

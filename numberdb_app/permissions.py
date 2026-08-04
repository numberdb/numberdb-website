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

__all__ = ['BOARD_GROUP', 'is_board_member', 'may_edit', 'board_group']

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

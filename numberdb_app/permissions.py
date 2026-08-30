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
           'TRUSTED_GROUP', 'trusted_group', 'operator_of',
           'is_vouched_for',
           'TRUSTED_AFTER', 'accepted_edit_count', 'is_trusted',
           'edits_are_reviewed', 'may_write_through_api',
           'may_create_tables_through_api']

#: Accepted edits after which an account is trusted. Five is enough to have
#: made and had confirmed a handful of real corrections, and few enough that
#: somebody working steadily reaches it in a week rather than a year.
TRUSTED_AFTER = 5

#: The group whose members may review.
BOARD_GROUP = 'board'

#: The group whose members are trusted without having earned it by count.
#:
#: Trust is normally a track record, and it should be. This exists for the one
#: case the count cannot serve: an account that is a program, run by somebody
#: who is also its only reviewer. `accepted_edit_count` refuses to credit an
#: assistant's revision confirmed by its operator -- correctly, since that is
#: one person's judgement either way -- so such an account can never reach
#: TRUSTED_AFTER no matter how much good work it does. Somebody has to vouch
#: for it instead, in a place that is visible and can be taken back.
#:
#: What this grants is narrow, which is why granting it is reasonable. Trust
#: unlocks *writing* through the API. It does not unlock publishing, which is
#: board-only; it does not unlock reviewing, which is board-only; and it does
#: not stop a non-board account's edits being marked unreviewed and held out
#: of search by number until a person confirms them. A vouched-for program
#: still has every call it makes reviewed by somebody.
TRUSTED_GROUP = 'trusted'


def board_group():
	"""The board group, created on first use so a fresh install has one."""
	group, _ = Group.objects.get_or_create(name=BOARD_GROUP)
	return group


def trusted_group():
	"""The trusted group, created on first use."""
	group, _ = Group.objects.get_or_create(name=TRUSTED_GROUP)
	return group


def operator_of(user):
	"""The person who runs ``user``, or None.

	Set for an account that is a program. See `UserProfile.operated_by`.
	"""
	profile = getattr(user, 'profile', None)
	return getattr(profile, 'operated_by', None)


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


#: How a revision says an assistant produced it. Written by the client package
#: into `produced_by`, from the NUMBERDB_ASSISTED_BY environment variable, and
#: matched here rather than parsed: this is a human-readable field and the
#: phrase is the convention.
ASSISTED_MARKER = 'assisted by'


def may_edit(user):
	"""Whether ``user`` may change a table.

	Any confirmed account. The protection against bad edits is that they are
	marked and held out of search by number until reviewed, not that people are
	kept from making them.
	"""
	return bool(getattr(user, 'is_authenticated', False))


def _self_and_operator(user):
	"""``user``, and whoever runs them if anybody does.

	A list rather than a Q so the caller reads as what it means: these are the
	people whose confirmation says nothing new about this account.
	"""
	operator = operator_of(user)
	return [user] if operator is None else [user, operator]


def accepted_edit_count(user):
	"""How many of ``user``'s revisions a reviewer has since confirmed.

	Counted from review rather than from thumbs-up. A review is a statement
	about whether the digits are right, which is the thing trust here is
	about; approval is a statement about whether people liked the edit, and a
	script can farm it. It is also data the review queue already produces.

	A revision counts as accepted once its table has been reviewed at or after
	it, which is what `reviewed_at_revision` advancing means.
	"""
	from django.db.models import F, Q

	from .models import TableRevision

	if not getattr(user, 'is_authenticated', False):
		return 0
	return TableRevision.objects.filter(
		author=user,
		table__reviewed_at_revision__isnull=False,
		created__lte=F('table__reviewed_at_revision__created'),
	).exclude(
		#A revision an assistant produced is evidence about its author only
		#when somebody else confirmed it. The counter was already built
		#against farming -- it counts reviews rather than approvals, because
		#"a script can farm" approval -- and an assistant whose operator
		#reviews its own output farms it just as effectively and more
		#politely. Reviews from before `reviewed_by` was recorded are null and
		#so do not match, which is the right default: they were confirmed by
		#the board.
		#
		#`operated_by` is why the reviewer is a set rather than the author.
		#Giving an agent its own account is good practice -- attributable
		#work, a key that can be revoked on its own -- and it used to defeat
		#this check completely, because author and reviewer were then two
		#different usernames belonging to the same judgement. An account that
		#says who runs it does not get to launder its edits through them.
		Q(produced_by__icontains=ASSISTED_MARKER)
		& Q(table__reviewed_by__in=_self_and_operator(user))
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
	#Vouched for explicitly. See TRUSTED_GROUP for why the count alone cannot
	#serve an account that is a program.
	if user.groups.filter(name=TRUSTED_GROUP).exists():
		return True
	return accepted_edit_count(user) >= TRUSTED_AFTER


def is_vouched_for(user):
	"""Whether somebody granted this account trust it has not earned.

	See TRUSTED_GROUP. Separate from `is_trusted` because the two questions
	that used to share an answer are not the same question.
	"""
	if not getattr(user, 'is_authenticated', False):
		return False
	return user.groups.filter(name=TRUSTED_GROUP).exists()


def edits_are_reviewed(user):
	"""Whether this account's edits are published as already reviewed.

	Requiring a board member to review their own work would make a queue of
	one person's edits waiting for that same person; requiring it of somebody
	with a confirmed track record turns review into a formality that trains
	reviewers to click through. Everybody else waits, which is what keeps
	unchecked digits out of search by number.

	Deliberately not `is_trusted`, though it was until an agent account made
	the difference visible. Trust answers "may this account write with a
	program", and a vouch can answer that: it is a statement about who takes
	responsibility for the rate. This answers "are these digits right without
	anybody looking", and a vouch cannot answer that, because the digits are
	the thing nobody has looked at yet. Vouching for a program in order to
	let it write, and thereby exempting everything it writes from review,
	would undo the reason for having it write into a queue at all.
	"""
	if is_board_member(user):
		return True
	return accepted_edit_count(user) >= TRUSTED_AFTER


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


#: How many unpublished drafts an account may hold at once.
#:
#: Creating *published* tables with a program is board-only, and the reasoning
#: is about permanence: a T-number, a title in every listing, a parameter order
#: citations resolve on, and prose no reviewer wrote. A loop that means to make
#: three and makes three hundred leaves three hundred of those.
#:
#: A draft is none of those things yet. It is invisible, in no listing, answers
#: no search, and costs a number if abandoned. So a draft may be created with a
#: program, and this is what keeps the same loop bounded: the three-hundredth
#: attempt is refused, and what it leaves behind is a handful of drafts nobody
#: can see, which somebody can clean up.
#:
#: Five, because more than five tables genuinely in progress at once is not a
#: workflow anybody has, and a loop that has made five is already obviously
#: wrong. Board members are not capped: they are the ones who publish, and a
#: draft of theirs is one step from being a table.
DRAFTS_IN_FLIGHT = 5


def draft_allowance(user):
	"""How many more drafts ``user`` may create, and how many they hold.

	Returns ``(remaining, held)``. ``remaining`` is None for no limit.
	"""
	from .models import Table

	if is_board_member(user):
		return (None, Table.objects.filter(created_by=user,
		                                   published=False).count())
	held = Table.objects.filter(created_by=user, published=False).count()
	return (max(0, DRAFTS_IN_FLIGHT - held), held)


def may_create_drafts_through_api(user):
	"""Whether ``user`` may create an unpublished table with a program.

	Lower than creating a published one, because a draft is reversible in the
	way a table is not: nobody has cited it, nothing links to it, and no
	search answers with its numbers. Publishing stays a person's act.
	"""
	if not may_write_through_api(user):
		return False
	remaining, _ = draft_allowance(user)
	return remaining is None or remaining > 0


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

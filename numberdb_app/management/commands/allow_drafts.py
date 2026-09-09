"""Let an account hold the larger number of unpublished drafts.

    manage.py allow_drafts zeta3 bmatschke      # add to the group
    manage.py allow_drafts --remove zeta3       # take it back
    manage.py allow_drafts --list               # who has it

Membership of `bulk drafts` raises only the ceiling on drafts in flight, from
NUMBERDB_DRAFTS_IN_FLIGHT to NUMBERDB_BULK_DRAFTS_IN_FLIGHT. It grants nothing
else: publishing stays a person's act, reviewing stays the board's, and a
draft is still invisible to everybody but its author and the board.

It is meant for an account that runs campaigns -- a batch of tables built in a
night and reviewed in a sitting -- which is the one legitimate way to reach
the ordinary ceiling.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from numberdb_app.permissions import (BULK_DRAFTS_IN_FLIGHT, bulk_drafts_group,
                                      draft_allowance)


class Command(BaseCommand):

	help = 'Add or remove accounts from the bulk-drafts group.'

	def add_arguments(self, parser):
		parser.add_argument('usernames', nargs='*',
		                    help='accounts to add, or to remove with --remove')
		parser.add_argument('--remove', action='store_true',
		                    help='take the allowance back')
		parser.add_argument('--list', action='store_true',
		                    help='say who has it, and change nothing')

	def handle(self, *args, **options):
		group = bulk_drafts_group()
		if options['list']:
			return self.report(group)

		usernames = options['usernames']
		if not usernames:
			raise CommandError('Name at least one account, or pass --list.')

		users = get_user_model().objects
		for username in usernames:
			try:
				user = users.get(username=username)
			except users.model.DoesNotExist:
				raise CommandError('No account is called %r.' % (username,))
			if options['remove']:
				user.groups.remove(group)
				self.stdout.write('%s: allowance taken back' % (username,))
			else:
				user.groups.add(group)
				remaining, held = draft_allowance(user)
				self.stdout.write(
					'%s: may hold %d drafts, holds %d, %s remaining'
					% (username, BULK_DRAFTS_IN_FLIGHT, held,
					   'no limit' if remaining is None else remaining))
		self.report(group)

	def report(self, group):
		members = list(group.user_set.all().order_by('username'))
		if not members:
			self.stdout.write('Nobody is in %r.' % (group.name,))
			return
		self.stdout.write('In %r (ceiling %d):'
		                  % (group.name, BULK_DRAFTS_IN_FLIGHT))
		for user in members:
			remaining, held = draft_allowance(user)
			self.stdout.write(
				'  %-20s holds %3d, %s remaining'
				% (user.username, held,
				   'no limit' if remaining is None else '%3d' % (remaining,)))

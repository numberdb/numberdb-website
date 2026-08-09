"""Put a banner across every page, or take it down.

For the hour when the site is not itself -- a rebuild, a migration, a long
import. A visitor cannot tell "slow because somebody is rebuilding every table"
from "slow because it is broken", and the second reading is the one they leave
with.

    manage.py notice on "Rebuilding the tables; searches may be slow."
    manage.py notice off
    manage.py notice            # say what is showing
"""

from django.core.management.base import BaseCommand

from ...models import SiteNotice


class Command(BaseCommand):
	help = 'Show or hide the site-wide notice.'

	def add_arguments(self, parser):
		parser.add_argument('state', nargs='?', default='',
		                    choices=['', 'on', 'off'])
		parser.add_argument('message', nargs='?', default='')

	def handle(self, *args, **options):
		notice, _made = SiteNotice.objects.get_or_create(pk=1)
		state = options['state']

		if not state:
			self.stdout.write(str(notice))
			return

		if state == 'off':
			notice.showing = False
			notice.save()
			self.stdout.write('notice off')
			return

		message = (options['message'] or '').strip() or notice.message
		if not message:
			raise SystemExit('Say what the notice should read.')
		notice.message = message[:300]
		notice.showing = True
		notice.save()
		self.stdout.write('notice on: %s' % (notice.message,))

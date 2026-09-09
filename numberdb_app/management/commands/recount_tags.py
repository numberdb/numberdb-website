"""Recount what each tag reaches, published tables only.

    manage.py recount_tags          # every tag
    manage.py recount_tags --dry-run

`sync_tags` keeps these two numbers up to date as tables are written, so this
exists for the one-off after the counts changed meaning: they used to include
unpublished tables, which put drafts on /tags -- by title and T-number, to
anybody -- and made a tag appear there whose only tables were drafts. A tag
that now reaches nothing keeps its row and drops to zero, which is what hides
it from the listing; it comes back when a table carrying it is published.
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum

from numberdb_app.models import Tag


class Command(BaseCommand):

	help = 'Recount tag table_count and number_count over published tables.'

	def add_arguments(self, parser):
		parser.add_argument('--dry-run', action='store_true',
		                    help='say what would change, and change nothing')

	def handle(self, *args, **options):
		dry = options['dry_run']
		changed = 0
		for tag in Tag.objects.all().order_by('name_lowercase'):
			count = tag.public_tables.count()
			numbers = (tag.public_tables.aggregate(total=Sum('number_count'))
			           ['total'] or 0)
			if tag.table_count == count and tag.number_count == numbers:
				continue
			changed += 1
			self.stdout.write(
				'%-32s %4d -> %-4d tables, %8d -> %-8d numbers'
				% (tag.name, tag.table_count, count,
				   tag.number_count, numbers))
			if not dry:
				tag.table_count = count
				tag.number_count = numbers
				tag.save(update_fields=['table_count', 'number_count'])
		self.stdout.write('%d tag%s %s' % (
			changed, '' if changed == 1 else 's',
			'would change' if dry else 'recounted'))

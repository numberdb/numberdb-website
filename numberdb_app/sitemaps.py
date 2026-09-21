"""What this site holds, for a crawler that cannot guess.

Google had indexed 85 pages and passed over 137, and the largest single
reason -- 73 of them -- was "crawled, currently not indexed", which is what a
search engine says when it found a page by following a link, had no reason to
think it mattered, and moved on. There was nothing to tell it otherwise:
`/sitemap.xml` and `/robots.txt` both answered 404, so a corpus of several
hundred tables was discoverable only by crawling the listings.

**Generated on request, never written to disk.** A sitemap that is built and
stored is a sitemap that is stale: this corpus gains tables nightly and every
one of them changes again under review. Django's sitemap framework reads the
database when Google asks, so "keep it up to date" is not a job anybody has
to remember -- and `lastmod` comes from each table's newest revision, which
is the same clock the history page shows.

Only published tables. A draft answers 404 to a reader, so listing one would
be an invitation to a page that does not exist for the crawler, which is
exactly how a "soft 404" is earned.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class TableSitemap(Sitemap):
	"""Every published table, at the address its page calls canonical.

	That is the T-number, and the reason is in table.html: a table answers at
	both `/T35` and `/Zeros_of_Dirichlet_L_functions`, the number is allocated
	once and never changes, and the slug is derived from a title that can be
	rewritten. A sitemap offering the other address would argue with the
	canonical link on every page, which is how a crawler is taught to trust
	neither.
	"""

	changefreq = 'weekly'
	priority = 0.8
	limit = 2000

	def items(self):
		from .models import Table

		return (Table.objects.filter(published=True)
		        .exclude(url='')
		        .order_by('tid_int'))

	def location(self, table):
		return reverse('db:table', kwargs={'tid': table.tid})

	def lastmod(self, table):
		#The newest revision, which is what the history page calls the table's
		#last change. Cheap: `head_revision` is a foreign key the row already
		#carries, so this costs no query per table beyond the join.
		revision = table.head_revision
		return revision.created if revision is not None else None


class TagSitemap(Sitemap):
	"""The tag pages, which are how a reader browses by subject."""

	changefreq = 'weekly'
	priority = 0.5

	def items(self):
		from .models import Tag

		return Tag.objects.all().order_by('name')

	def location(self, tag):
		#`url` is a method on Tag, not a field.
		return reverse('db:tag', kwargs={'tag_url': tag.url()})


class StaticSitemap(Sitemap):
	"""The pages that are not about one table: the front page, the help."""

	changefreq = 'monthly'
	priority = 0.6

	def items(self):
		return ['db:home', 'db:about', 'db:help', 'db:tables', 'db:tags',
		        'db:advanced-search', 'db:api-reference', 'db:wanteds']

	def location(self, name):
		return reverse(name)


#: What `/sitemap.xml` offers. Split by kind rather than served as one list,
#: so that a crawler fetching the index can see at a glance that the tables
#: are the substance of the site and the rest is furniture.
SITEMAPS = {
	'tables': TableSitemap,
	'tags': TagSitemap,
	'pages': StaticSitemap,
}

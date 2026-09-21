"""Values every template may need.

Only one so far: whether the viewer may review. The navigation has to decide
whether to offer the queue, and a template cannot ask about group membership
without either a query per render or a tag that hides one.
"""

from .permissions import is_board_member

__all__ = ['review_access', 'waiting_for_review']


def review_access(request):
	user = getattr(request, 'user', None)
	return {'is_board_member': is_board_member(user) if user else False}


def site_notice(request):
	"""The maintenance banner, if one is showing.

	One query per page. It is a single indexed row and the alternative -- a
	cache keyed on something -- would be a second thing to get wrong for a
	banner that is off almost always.
	"""
	from .models import SiteNotice

	try:
		return {'site_notice': SiteNotice.current()}
	except Exception:
		#Before the migration has run, and during one. A banner that breaks
		#every page is worse than no banner, and this is exactly the moment
		#the site is least able to afford it.
		return {'site_notice': None}

def drafts_in_progress(request):
	"""How many tables are being set up, for the navbar.

	Signed-in accounts only: a draft is invisible to everybody else, and
	counting them for a passer-by would leak that work is happening even
	though the count is all they would get.

	One indexed count per page against a table that holds a handful of rows.
	If drafts ever become numerous enough for this to matter, the count is the
	wrong thing to show anyway.
	"""
	user = getattr(request, 'user', None)
	if not getattr(user, 'is_authenticated', False):
		return {'drafts_in_progress': 0}

	from .models import Table

	return {'drafts_in_progress': Table.objects.filter(published=False).count()}


def waiting_for_review(request):
	"""How many tables are waiting to be confirmed, for the navbar.

	The queue told a board member it existed and not whether anything was in
	it, so the only way to find out was to open it -- and an empty page is
	what teaches somebody to stop looking. The drafts link beside it has
	carried its count since it was added.

	Board members only, because only they can act on it, and the same list the
	queue itself renders rather than a second count of it.
	"""
	from .permissions import is_board_member
	from .review import waiting_for_review as waiting

	user = getattr(request, 'user', None)
	if not user or not is_board_member(user):
		return {'tables_waiting_for_review': 0}
	return {'tables_waiting_for_review': len(waiting())}


def canonical_origin(request):
	"""Which host this site calls itself, for canonical links.

	Built from the request until now, so `numberdb.org/T313` declared the apex
	canonical and `www.numberdb.org/T313` declared www -- two complete copies
	of the site, each insisting it was the original. Google reported fourteen
	pages as "duplicate without user-selected canonical"; that is what it was
	looking at.

	A canonical address is a decision about the site, so it comes from
	settings. `NUMBERDB_CANONICAL_ORIGIN` when it is set; otherwise the first
	allowed host, which is right in production and harmless in development.
	"""
	from django.conf import settings

	import re

	origin = getattr(settings, 'NUMBERDB_CANONICAL_ORIGIN', '')
	if not origin:
		#A name, not a number: ALLOWED_HOSTS here reads
		#`['.localhost', '127.0.0.1', '45.33.90.86', 'numberdb.org',
		#'.numberdb.org']`, and the first entry that is neither a wildcard nor
		#localhost is the server's IP address -- which would have put
		#`https://45.33.90.86/T313` on every page as the address to index.
		def looks_like_a_site(host):
			if host in ('*', 'localhost', '127.0.0.1'):
				return False
			if host.startswith('.') or host.startswith('www.'):
				return False
			if re.fullmatch(r'[\d.]+', host) or ':' in host:
				return False        # an IPv4 or IPv6 address
			return '.' in host

		hosts = [h for h in getattr(settings, 'ALLOWED_HOSTS', [])
		         if looks_like_a_site(h)]
		if hosts:
			origin = 'https://%s' % (hosts[0],)
		else:
			origin = '%s://%s' % (request.scheme, request.get_host())
	return {'canonical_origin': origin.rstrip('/')}

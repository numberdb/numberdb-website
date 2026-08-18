"""Values every template may need.

Only one so far: whether the viewer may review. The navigation has to decide
whether to offer the queue, and a template cannot ask about group membership
without either a query per render or a tag that hides one.
"""

from .permissions import is_board_member

__all__ = ['review_access']


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

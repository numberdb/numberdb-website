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

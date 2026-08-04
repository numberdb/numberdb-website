"""URL helpers for templates.

One filter, because the address of a single value is built in six places and
they had drifted into agreeing only by accident.
"""

from urllib.parse import quote

from django import template

register = template.Library()


@register.filter
def entry_suffix(param):
	"""The part of a link that identifies one entry.

	Both forms, deliberately:

	    ?entry=6,18/11   the server sees this, so it can confirm the entry is
	                     really there and say so when it is not
	    #6,18/11         the browser sees this, and scrolls

	A link with only the fragment is what the site had, and it fails silently:
	a citation to an entry that has since been renumbered loads the page and
	scrolls nowhere, with nothing to tell the reader that anything is wrong.

	Percent-encoded in the query and raw in the fragment, because the fragment
	has to match the element's id exactly, and 6736 of the identities contain a
	"/" that would otherwise end the query value early.
	"""
	if not param:
		return ''
	return '?entry=%s#%s' % (quote(str(param), safe=''), param)

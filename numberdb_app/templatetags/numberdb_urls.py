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

	    ?entry=6,18/11

	The query rather than a fragment, because a fragment is never sent to the
	server: a citation to an entry that has since been renumbered would load the
	page and scroll nowhere, with nothing to tell the reader anything was wrong.
	The server can confirm the entry is there, and say so when it is not.

	No fragment beside it. Carrying both said the same thing twice and made a
	citation twice as long as it needed to be; the page scrolls to the entry
	itself when asked for one. Fragments are still understood, because every
	link written before today is one.

	Commas are left as they are, being legal in a query string, so that the
	result reads as a citation rather than as 1611%2C432%2C-17496. The "/" in
	6736 of the identities is still encoded, since it would otherwise end the
	value early.
	"""
	if not param:
		return ''
	#Only "/" and the handful of characters that would end the value early are
	#encoded. A comma is legal unencoded in a query string, and encoding it
	#turned a readable citation into 1611%2C432%2C-17496.
	return '?entry=%s' % (quote(str(param), safe=',:'),)


@register.filter
def get(mapping, key):
	"""Look a key up in a mapping when the key is a variable.

	Django's template language has no syntax for it: `{{ values.field }}` looks
	for a key literally called "field". A section's fields are data -- read off
	what the corpus uses -- so they cannot be written out one by one.
	"""
	try:
		return mapping.get(key, '')
	except AttributeError:
		return ''

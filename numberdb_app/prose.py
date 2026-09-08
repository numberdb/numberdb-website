"""A little structure in a field that is one long paragraph today.

`Data properties: rigour details` answers "how well are these digits known",
and it is the one metadata field with something long to say: 139 tables carry
it, the median is 199 characters, and the longest five run to three thousand.
Every one of the 139 is a single paragraph, because until now a newline was
the only structure available and nobody reached for it.

So: blank lines separate paragraphs, a run of lines beginning "- " is a list,
and `backticks` mark code. Nothing else -- no headings, no tables, no links of
its own, because CITE{} and HREF{} already do that and a second syntax for the
same thing is how a corpus ends up with both.

It is a subset a person would write anyway if they thought the field allowed
it, which is the test a markup subset should pass.
"""
import re

#: A long note is folded: the first paragraph shows and the rest waits behind
#: a disclosure. Above this many characters of rendered prose, in a field
#: whose neighbours are one line each, the note stops being metadata and
#: becomes the page.
FOLD_ABOVE = 400

_CODE = re.compile(r'`([^`]+)`')


def _blocks(text):
	"""(kind, lines) for each paragraph or list in the text."""
	found = []
	current = None
	for line in (text or '').split('\n'):
		stripped = line.strip()
		bullet = stripped.startswith('- ') or stripped == '-'
		if not stripped:
			current = None
			continue
		kind = 'list' if bullet else 'paragraph'
		if current is None or current[0] != kind:
			current = (kind, [])
			found.append(current)
		current[1].append(stripped[2:].strip() if bullet else stripped)
	return found


def render(text, render_text, fold_above=FOLD_ABOVE):
	"""(first block, the rest) as HTML, both already escaped and linked.

	`render_text` is the table renderer's own, so mathematics, CITE and HREF
	behave exactly as they do everywhere else on the page; this only decides
	where the paragraphs and the bullets are.

	The rest is empty when the note is short, which is the common case: a
	field of one or two sentences should look like a field, not like a
	disclosure with nothing worth disclosing.
	"""
	pieces = []
	for kind, lines in _blocks(text):
		if kind == 'list':
			items = ''.join(
				'<li>%s</li>' % (_inline(line, render_text),) for line in lines)
			pieces.append('<ul class="prose-list">%s</ul>' % (items,))
		else:
			pieces.append('<p class="prose-paragraph">%s</p>'
			              % (_inline(' '.join(lines), render_text),))
	if not pieces:
		return '', ''
	head, rest = pieces[0], ''.join(pieces[1:])
	if len(head) + len(rest) <= fold_above:
		return head + rest, ''
	return head, rest


def _inline(line, render_text):
	"""One line, with `code` marked, through the page's own renderer.

	The backticks are replaced after rendering, not before: `render_text`
	escapes its input, so a tag put in first arrives as text.
	"""
	rendered = render_text(line, line_breaks=False)
	return _CODE.sub(r'<code class="prose-code">\1</code>', rendered)

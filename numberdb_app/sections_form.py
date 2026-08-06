"""The prose sections of a table, as something other than YAML.

The people this database is for are mathematicians, not people who enjoy
whitespace-significant markup. Nothing displays the schema either: a table's
source shows what *this* table happens to contain, so the way to discover that
references may carry a DOI is to find a table that has one. A form shows the
shape itself, which is the argument for covering everything foreseeable rather
than only the fields with fixed choices.

The sections are not one shape but four, and pretending otherwise would lose
data:

  text              `Definition` -- one string, 107 tables
  labelled text     `Comments` (144 items), `Formulas` (94) -- label: prose
  labelled records  `References` (71), `Programs` (45), `Links` (177) --
                    label: a small set of fields
  lists             `Tags`, `Keywords`, `Similar tables`

The labels are load-bearing. `CITE{Pla15}` and `HREF{Factorial}` point at them,
so a label is not decoration and renaming one breaks every citation to it --
the same failure as reordering parameters, and treated with the same care.

As with the metadata form, this **patches**: a section the form did not show is
never written, and the sections it does show keep their order and their
neighbours. What it owns inside a section is that section entirely, since an
ordered list of items cannot be patched item-wise without knowing which item is
which -- which is what the labels are for.
"""

from __future__ import annotations

__all__ = ['SECTIONS', 'sections_from', 'apply_sections', 'section_named']

#: The fields a record-shaped item carries, in the order they are shown. Read
#: off the corpus: References use `bib`/`doi`/`arXiv`/`MR`/`url`/`github`,
#: Programs `language`/`code`, Links `title`/`url`.
#:
#: `arXiv` and `MR` are spelt inconsistently in the data -- 14 `arXiv` against
#: 4 `arxiv`, 7 `MR` against 1 `mr` -- which is what a field with one spelling
#: quietly ends.
RECORD_FIELDS = {
	'References': ('bib', 'doi', 'arXiv', 'MR', 'url', 'github'),
	'Programs': ('language', 'code'),
	'Links': ('title', 'url'),
}

#: Fields that want more than a line.
LONG_FIELDS = frozenset(['bib', 'code'])

#: (name, shape, note). Order is the order they are offered in.
SECTIONS = (
	('Definition', 'text',
	 'What these numbers are, in a sentence or two. LaTeX is allowed.'),
	('Comments', 'labelled-text',
	 'Remarks about the table. A label lets a comment be cited with '
	 'CITE{label}.'),
	('Formulas', 'labelled-text',
	 'Identities and definitions, in LaTeX.'),
	('References', 'labelled-record',
	 'Papers and books. The label is what CITE{...} points at.'),
	('Programs', 'labelled-record',
	 'Code that produced or checks these numbers.'),
	('Links', 'labelled-record',
	 'Pages elsewhere about these numbers.'),
	('Keywords', 'list', 'Words a reader might search for.'),
	('Similar tables', 'list', 'Related tables, by name.'),
)

SHAPES = {name: shape for name, shape, _note in SECTIONS}


def section_named(name):
	for section, shape, note in SECTIONS:
		if section == name:
			return {'name': section, 'shape': shape, 'note': note,
			        'fields': RECORD_FIELDS.get(section, ())}
	return None


def sections_from(tree):
	"""Every section the form can show, with what this table has in it."""
	if not isinstance(tree, dict):
		tree = {}
	out = []
	for name, shape, note in SECTIONS:
		value = tree.get(name)
		entry = {'name': name, 'shape': shape, 'note': note,
		         'fields': RECORD_FIELDS.get(name, ()),
		         'long_fields': LONG_FIELDS}
		if shape == 'text':
			entry['text'] = value if isinstance(value, str) else ''
			entry['unshowable'] = value is not None and not isinstance(value, str)
		elif shape == 'list':
			entry['items'] = _as_list(value)
			#Three tables write `Similar tables` as a list of records --
			#{relation: contained in, table: HREF{...}} -- rather than names.
			#Read as a list of names it comes out empty, and saving would have
			#deleted it. Flagged and left alone instead.
			entry['unshowable'] = _has_non_strings(value)
		else:
			entry['items'] = _labelled(value, shape, RECORD_FIELDS.get(name, ()))
			#A section holding something the form cannot render is left alone
			#and said so, rather than shown empty and deleted on the next save.
			entry['unshowable'] = value is not None and not isinstance(value, dict)
		out.append(entry)
	return out


def _as_list(value):
	"""A list section's items.

	94 tables write `Keywords` as a bare string and 13 as a list, and
	`Similar tables` likewise. Both are read; one item per line is what the
	form offers back, and a single item stays a single item.
	"""
	if value is None:
		return []
	if isinstance(value, str):
		return [value] if value.strip() else []
	if isinstance(value, list):
		return [v for v in value if isinstance(v, str)]
	return []


def _has_non_strings(value):
	"""Whether a list section holds anything the form cannot show as a name."""
	return isinstance(value, list) and any(
		not isinstance(item, str) for item in value)


def _labelled(value, shape, fields):
	if not isinstance(value, dict):
		return []
	items = []
	for label, item in value.items():
		row = {'label': label, 'text': '', 'values': {}, 'extra': {},
		       'was_plain': False}
		if shape == 'labelled-text':
			row['text'] = item if isinstance(item, str) else ''
			row['unshowable'] = not isinstance(item, str)
		elif isinstance(item, dict):
			row['values'] = {f: str(item.get(f, '')) for f in fields}
			#Anything the form has no field for is carried through untouched
			#rather than dropped, which is how `github` survived before it had
			#a field and how the next one will.
			row['extra'] = {k: v for k, v in item.items() if k not in fields}
			row['unshowable'] = False
		else:
			#Ten Links are a bare string rather than a title/url pair. Read into
			#the field it belongs in, and remembered as plain so that saving
			#without touching it writes a string back: a form that silently
			#promoted them to records would change ten documents the first time
			#anybody opened them.
			row['values'] = {(fields[-1] if fields else 'url'): str(item)}
			row['extra'] = {}
			row['was_plain'] = True
			row['unshowable'] = False
		items.append(row)
	return items


def apply_sections(tree, data):
	"""Write back the sections the form submitted, and only those.

	A section is recognised by a marker field, so one the form was not showing
	is left exactly as it is. Within a submitted section the items are rebuilt
	in the order they arrive, which is how reordering and deleting are
	expressed: an item that is gone from the submission is gone.
	"""
	import copy

	out = copy.deepcopy(tree) if isinstance(tree, dict) else {}

	for name, shape, _note in SECTIONS:
		marker = 'section.%s.present' % (name,)
		if marker not in data:
			continue
		if shape == 'text':
			text = (data.get('section.%s.text' % (name,)) or '').strip()
			_put(out, name, text)
		elif shape == 'list':
			if _has_non_strings(out.get(name)):
				#Guarded here as well as in the template, because a section
				#the form cannot render must not be emptied by a submission
				#that simply did not mention its contents.
				continue
			raw = data.get('section.%s.items' % (name,)) or ''
			items = [line.strip() for line in raw.split('\n') if line.strip()]
			#A section written as one string keeps being one string: 94 tables
			#write Keywords that way, and turning them all into single-item
			#lists is a change to 94 documents for no gain.
			if isinstance(out.get(name), str) and len(items) <= 1:
				_put(out, name, items[0] if items else '')
			else:
				_put(out, name, items)
		else:
			_put(out, name, _rebuild(name, shape, data,
			                         RECORD_FIELDS.get(name, ())))
	return out


def _rebuild(name, shape, data, fields):
	"""One labelled section, from the rows the form sent."""
	built = {}
	for index in _row_order(name, data):
		label = (data.get('section.%s.%s.label' % (name, index)) or '').strip()
		if not label:
			#A row with no label cannot be cited and cannot be found again, so
			#an unlabelled one is an unfinished one rather than an anonymous
			#one; dropping it is what "delete" does.
			continue
		if shape == 'labelled-text':
			text = data.get('section.%s.%s.text' % (name, index)) or ''
			if text.strip():
				built[label] = text.strip()
			continue

		record = {}
		for field in fields:
			value = (data.get('section.%s.%s.%s' % (name, index, field))
			         or '').strip()
			if value:
				record[field] = value

		#A row that arrived as a bare string and still holds only that one
		#field goes back as a bare string. Filling in anything else is a
		#deliberate promotion to the record form.
		plain_field = fields[-1] if fields else 'url'
		if (data.get('section.%s.%s.plain' % (name, index))
				and set(record) <= {plain_field}):
			if record:
				built[label] = record[plain_field]
			continue
		carried = data.get('section.%s.%s.extra' % (name, index))
		if carried:
			import json

			try:
				record.update(json.loads(carried))
			except ValueError:
				pass
		if record:
			built[label] = record
	return built


def _row_order(name, data):
	"""The row indices this section submitted, in the order they were sent.

	The browser sends them in document order, so dragging a row changes the
	order without anything having to renumber.
	"""
	prefix = 'section.%s.' % (name,)
	seen = []
	for key in data:
		if not key.startswith(prefix) or not key.endswith('.label'):
			continue
		index = key[len(prefix):-len('.label')]
		if index not in seen:
			seen.append(index)
	order = data.getlist('section.%s.order' % (name,)) if hasattr(
		data, 'getlist') else []
	if order:
		#An explicit order wins, so a drag can be expressed without the fields
		#themselves moving in the document.
		return [i for i in order if i in seen] + [i for i in seen
		                                          if i not in order]
	return seen


def _put(tree, name, value):
	"""Set a section, keeping an emptied one in the form it already had.

	Most tables carry every section whether or not they have anything to put in
	it -- `Comments: {}` and `Keywords: ''` are written out -- so deleting the
	key when a section is empty is a change to every one of them, and to a
	reader of the exported file it says the section is not available rather
	than not filled in.

	So an empty result keeps whatever empty the document already had, and only
	a section that was never there stays away.
	"""
	if value:
		tree[name] = value
		return
	if name in tree:
		#Empty of the same kind: '' stays '', {} stays {}, [] stays [].
		existing = tree[name]
		tree[name] = type(existing)() if existing is not None else existing

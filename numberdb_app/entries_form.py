"""The entries of a table, as rows that can be edited.

The last part of a table that could only be edited as YAML, and the largest:
55945 records, the biggest table holding 1135 of them. A thousand entries is a
spreadsheet problem rather than a form problem, which is why this works in
pages and why the rules below are about not damaging what is off-screen.

**A page replaces only the rows it showed.** Rebuilding the entries from a
submission would delete every row on another page -- 1100 of them, silently,
from a save that looked like correcting one digit. So each row carries the
identity it was drawn with, and the save matches on that.

**What may change follows from what an identity is.** An entry's identity is
its parameter values, and citations, anchors, cross-references and search
results all resolve on it:

  the number, or a comment   free. This is what editing a table is for.
  a parameter value          renumbers that entry. Its citations do not break;
                             they resolve and point at a different number. So
                             it is refused on a published table and allowed on
                             a draft, as everywhere else identities are at
                             stake.
  adding a row               free: a new identity nobody can be citing yet.
  removing a row             allowed, and it is the honest failure -- a
                             citation to a removed entry says so, rather than
                             quietly meaning something else.
"""

from __future__ import annotations

from .flatten import entries_block, parameter_groups

__all__ = ['columns_of', 'rows_from', 'apply_entries', 'PAGE_SIZE']

#: Rows shown at once. Large enough that most tables are one page -- the median
#: table holds 119 entries -- and small enough that the biggest does not
#: produce a page nobody can use.
PAGE_SIZE = 200

#: Columns every row has beyond its parameters, in the order they are shown.
VALUE_COLUMNS = ('number', 'comment')


def columns_of(tree):
	"""The parameter names an entry is identified by, in order."""
	return [name for group in parameter_groups(tree) for name in group]


def identity_of(params, columns):
	"""The identity a row is matched on: its values, comma-joined."""
	return ','.join(str(params.get(name, '')) for name in columns)


def rows_from(tree, page=1, per_page=PAGE_SIZE):
	"""One page of entries, with what is needed to save them back.

	Returns (rows, meta). Each row carries the identity it was drawn with, so a
	save can find it again among entries it never showed.
	"""
	block = entries_block(tree)
	records = block if isinstance(block, list) else []
	columns = columns_of(tree)

	total = len(records)
	pages = max(1, (total + per_page - 1) // per_page)
	page = max(1, min(int(page or 1), pages))
	start = (page - 1) * per_page
	shown = records[start:start + per_page]

	rows = []
	for offset, record in enumerate(shown):
		if not isinstance(record, dict):
			continue
		params = record.get('params') or {}
		#Everything that is not a parameter or a known column is carried
		#through untouched: `proof`, `url`, `both signs`, and whatever the
		#format grows next.
		extra = {k: v for k, v in record.items()
		         if k not in ('params',) + VALUE_COLUMNS}
		rows.append({
			'index': start + offset,
			'params': {name: str(params.get(name, '')) for name in columns},
			'identity': identity_of(params, columns),
			'number': _as_text(record.get('number')),
			'number_is_list': isinstance(record.get('number'), list),
			'comment': str(record.get('comment') or ''),
			'extra': extra,
			'extra_json': _json(extra),
		})

	return rows, {
		'columns': columns,
		'page': page,
		'pages': pages,
		'total': total,
		'start': start,
		'per_page': per_page,
	}


def _as_text(value):
	if isinstance(value, list):
		#Several numbers share this identity; kept on one line so the row shape
		#does not change, and split again on the way back.
		return ' | '.join(str(v) for v in value)
	return '' if value is None else str(value)


def _json(value):
	import json

	return json.dumps(value) if value else ''


def apply_entries(tree, data, allow_identity_changes=False):
	"""Write back the rows a page submitted, leaving the rest of the table alone.

	Rows are matched by the identity they were drawn with. One that is gone
	from the submission was removed; one whose identity is not in the document
	is new and is appended.
	"""
	import copy

	out = copy.deepcopy(tree) if isinstance(tree, dict) else {}
	block = entries_block(out)
	if not isinstance(block, list):
		return out
	if 'entries.present' not in data:
		return out

	columns = columns_of(out)
	submitted, order = _submitted_rows(data, columns)

	#Which identities this page was responsible for. Anything else in the
	#document is untouched, which is what makes paging safe.
	covered = set()
	for value in data.getlist('entries.covered') if hasattr(
			data, 'getlist') else []:
		covered.add(value)

	kept = []
	for record in block:
		if not isinstance(record, dict):
			kept.append(record)
			continue
		identity = identity_of(record.get('params') or {}, columns)
		if identity not in covered:
			kept.append(record)
			continue
		if identity not in submitted:
			#Shown, and not sent back: removed.
			continue
		kept.append(_merge(record, submitted.pop(identity), columns,
		                   allow_identity_changes))

	#Whatever is left was added on the page.
	for identity in order:
		if identity in submitted:
			kept.append(_merge({}, submitted.pop(identity), columns,
			                   allow_identity_changes=True))

	out[_entries_key(out)] = kept
	return out


def _submitted_rows(data, columns):
	"""The rows a page sent, keyed by the identity they were drawn with."""
	rows = {}
	order = []
	prefix = 'entry.'
	seen = []
	for key in data:
		if key.startswith(prefix) and key.endswith('.was'):
			index = key[len(prefix):-len('.was')]
			if index not in seen:
				seen.append(index)

	for index in seen:
		was = data.get('%s%s.was' % (prefix, index)) or ''
		#A new row has no identity yet, so it is keyed by the field index
		#instead. Keying every new row on the empty string made a save with two
		#of them keep one: the second overwrote the first, silently.
		key = was or 'new:%s' % (index,)
		row = {
			'was': was,
			'params': {name: (data.get('%s%s.param.%s'
			                           % (prefix, index, name)) or '').strip()
			           for name in columns},
			'number': (data.get('%s%s.number' % (prefix, index)) or '').strip(),
			'comment': (data.get('%s%s.comment' % (prefix, index)) or '').strip(),
			'extra': data.get('%s%s.extra' % (prefix, index)) or '',
		}
		if not row['number'] and not any(row['params'].values()):
			continue
		rows[key] = row
		order.append(key)
	return rows, order


def _merge(record, row, columns, allow_identity_changes):
	"""One stored entry updated from its row."""
	import json

	out = dict(record)

	#The parameters, and therefore the identity.
	params = dict(out.get('params') or {})
	for name in columns:
		value = row['params'].get(name, '')
		if not value:
			continue
		if not allow_identity_changes and name in params and \
				str(params[name]) != value:
			#Refused rather than applied: changing it renumbers this entry and
			#leaves its citations resolving to a different number.
			continue
		params[name] = value
	if params:
		out['params'] = params

	if row['number']:
		out['number'] = ([part.strip() for part in row['number'].split('|')]
		                 if '|' in row['number'] else row['number'])
	if row['comment']:
		out['comment'] = row['comment']
	else:
		out.pop('comment', None)

	if row['extra']:
		try:
			out.update(json.loads(row['extra']))
		except ValueError:
			pass
	return out


def _entries_key(tree):
	for name in ('Numbers', 'Data'):
		if name in tree:
			return name
	return 'Numbers'

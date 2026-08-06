"""A form for the parts of a table whose vocabulary is closed.

Validation catches a mistake after it is made; a form that offers only valid
choices means it cannot be made. `type: Wombat` is unrepresentable in a select,
and a parameter's type cannot be misspelt if it is picked from a list. So the
form is not a convenience laid over the YAML editor, it is the place where a
whole class of error stops existing.

**It patches; it never regenerates.** This is the rule the whole idea depends
on. If switching to the form parsed a document into a form's own model and
switching back serialised that model, everything the form did not know about
would be silently dropped -- and the schema is *deliberately* open at the
annotation level, so a regenerating form would delete exactly the extensions
the format was designed to permit. Instead each field owns one path, and
applying the form writes those paths onto the parsed document and touches
nothing else. A form round trip with no edits must leave the document
byte-identical, including a document full of keys nobody has ever seen.

Which fields, decided by what the corpus actually contains:

  closed          `Data properties: type` (8 values), each parameter's `type`
                  (7), `Display properties: layout`
  closed + prose  `complete` -- yes/no/unknown, and a condition. Two tables say
                  `yes, assuming GRH` and `unknown (presumably not)`, and that
                  qualifier is mathematics rather than decoration. A free text
                  box welds it to the value, where no code can read it; a bare
                  dropdown throws it away. Two fields keep both.
  prose           `reliability`, `sources`, the parameters' `constraints`,
                  `title` and `display` -- left to the source view, since a
                  form cannot improve on a text box for a sentence.
"""

from __future__ import annotations

from .validate import (OTHER_TYPES, PARAMETER_TYPES, SEARCHABLE_TYPES,
                       TYPE_NAME_KEY)

__all__ = ['fields_from', 'apply_to', 'COMPLETENESS_ANSWERS', 'OTHER',
           'known_other_types']

#: The value the select carries for "something else".
OTHER = '__other__'

#: What `complete` may answer, before any condition.
COMPLETENESS_ANSWERS = ('yes', 'no', 'unknown')

#: The document paths the form owns. Anything not here is never written by it.
#: (name, section, key) -- a two-level path, which is as deep as the closed
#: vocabulary goes.
OWNED = (
	('data_type', 'Data properties', 'type'),
	('layout', 'Display properties', 'layout'),
)


def fields_from(tree):
	"""What the form should show for this document."""
	from .limits import claims_completeness, completeness_qualifier

	if not isinstance(tree, dict):
		tree = {}

	properties = tree.get('Data properties')
	properties = properties if isinstance(properties, dict) else {}
	display = tree.get('Display properties')
	display = display if isinstance(display, dict) else {}

	answer = _leading_word(properties.get('complete'))
	declared = str(properties.get('type') or '')
	is_other = bool(declared) and declared not in SEARCHABLE_TYPES
	return {
		'title': str(tree.get('Title') or ''),
		'data_type': '' if is_other else declared,
		'data_types': sorted(SEARCHABLE_TYPES),
		#The escape hatch, and what is already behind it. NumberDB was always
		#meant to be able to hold a kind of number it cannot parse; such values
		#are shown and cited and do not answer a search by their digits.
		'is_other_type': is_other,
		'other_type': declared if is_other else '',
		'other_type_name': (str(properties.get(TYPE_NAME_KEY) or '')
		                    or OTHER_TYPES.get(declared, '')) if is_other else '',
		#Not filled in here: reading the corpus is a query, and this function
		#is otherwise pure -- it is handed a document and answers about that
		#document. The view supplies the list.
		'known_other_types': [],
		'complete': answer if answer in COMPLETENESS_ANSWERS else '',
		'complete_answers': COMPLETENESS_ANSWERS,
		'complete_condition': completeness_qualifier(tree),
		'complete_is_odd': bool(properties.get('complete')) and
		                   answer not in COMPLETENESS_ANSWERS,
		'layout': str(display.get('layout') or ''),
		'parameters': _parameters_of(tree),
		'parameter_types': sorted(PARAMETER_TYPES),
	}


def _parameters_of(tree):
	parameters = tree.get('Parameters')
	if not isinstance(parameters, dict):
		return []
	out = []
	for name, spec in parameters.items():
		spec = spec if isinstance(spec, dict) else {}
		values = spec.get('values')
		out.append({
			'name': name,
			'type': str(spec.get('type') or ''),
			'constraints': str(spec.get('constraints') or ''),
			'display': str(spec.get('display') or ''),
			#The values a symbolic parameter may take, and how each is
			#written. The key is part of every identity of an entry using it,
			#which is why it is shown but not editable once saved.
			'values': [{'value': key, 'display': str(shown)}
			           for key, shown in values.items()]
			          if isinstance(values, dict) else [],
			'has_values': isinstance(values, dict),
		})
	return out


def apply_to(tree, data, allow_key_changes=False):
	"""Write the form's fields onto ``tree`` and return it.

	``data`` is a request's POST. Only the paths the form owns are touched, and
	a field absent from the submission leaves its path alone rather than
	clearing it -- a form that is not showing a field must not be able to
	delete it.
	"""
	import copy

	out = copy.deepcopy(tree) if isinstance(tree, dict) else {}

	title = (data.get('title') or '').strip()
	if title:
		out['Title'] = title

	properties = _section(out, 'Data properties')
	#Present-and-empty means "cleared"; absent means "not shown, leave it".
	#Those are different, and treating them the same lets a form delete a field
	#it never displayed -- which is the destructive behaviour this whole module
	#is arranged to avoid.
	if 'data_type' in data:
		chosen = (data.get('data_type') or '').strip()
		if chosen == OTHER:
			#Two parts, deliberately. A symbol on its own is a typo; a symbol
			#with a name beside it is somebody deciding that this database now
			#holds a kind of number it did not before.
			symbol = (data.get('other_type') or '').strip()
			name = (data.get('other_type_name') or '').strip()
			_set(properties, 'type', symbol)
			_set(properties, TYPE_NAME_KEY, name)
		else:
			_set(properties, 'type', chosen)
			if chosen in SEARCHABLE_TYPES:
				#A searchable type needs no name, and leaving a stale one
				#behind would describe the table as something it is not.
				properties.pop(TYPE_NAME_KEY, None)

	if 'complete' in data:
		answer = (data.get('complete') or '').strip()
		condition = (data.get('complete_condition') or '').strip()
		if not answer:
			properties.pop('complete', None)
		else:
			properties['complete'] = ('%s, %s' % (answer, condition)
			                          if condition else answer)
	_drop_if_empty(out, 'Data properties')

	display = _section(out, 'Display properties')
	if 'layout' in data:
		_set(display, 'layout', (data.get('layout') or '').strip())
	_drop_if_empty(out, 'Display properties')

	_apply_parameters(out, data, allow_key_changes)
	return out


def _apply_parameters(out, data, allow_key_changes=False):
	"""Each parameter's type, constraints and display.

	Names are not touched here. Renaming or reordering reassigns every entry's
	identity at once, which is refused on a published table and belongs to the
	parameter editor on a draft; a metadata form quietly doing it as a side
	effect of saving is exactly the accident the freeze exists to prevent.
	"""
	parameters = out.get('Parameters')
	if not isinstance(parameters, dict):
		return
	for name, spec in parameters.items():
		if not isinstance(spec, dict):
			continue
		for field, key in (('type', 'type'), ('constraints', 'constraints'),
		                   ('display', 'display')):
			form_key = 'parameter.%s.%s' % (name, field)
			if form_key in data:
				_set(spec, key, (data.get(form_key) or '').strip())

		if 'parameter.%s.values.present' % (name,) in data:
			_apply_values(spec, name, data, allow_key_changes,
			              _values_in_use(out, name))


def _section(tree, name):
	section = tree.get(name)
	if not isinstance(section, dict):
		section = {}
		tree[name] = section
	return section


def _set(section, key, value):
	"""Set a key, or remove it when the field was cleared."""
	if value:
		section[key] = value
	else:
		section.pop(key, None)


def _drop_if_empty(tree, name):
	"""Do not leave an empty section behind that was not there before."""
	if isinstance(tree.get(name), dict) and not tree[name]:
		del tree[name]


def _leading_word(value):
	from .limits import _leading_word as leading

	return leading(value)


def known_other_types():
	"""Types outside the searchable set that some table already declares.

	Read from the corpus rather than from a list in the code, so recording a
	new kind of number does not need a release: the next person choosing
	"something else" is offered what the last one entered.
	"""
	import yaml

	from .models import Table

	found = dict(OTHER_TYPES)
	rows = (Table.objects.exclude(head_revision=None)
	        .select_related('head_revision').only('head_revision'))
	for table in rows:
		try:
			tree = yaml.load(table.head_revision.content,
			                 Loader=yaml.BaseLoader) or {}
		except Exception:
			continue
		properties = tree.get('Data properties')
		if not isinstance(properties, dict):
			continue
		symbol = str(properties.get('type') or '').strip()
		if symbol and symbol not in SEARCHABLE_TYPES:
			found.setdefault(
				symbol, str(properties.get(TYPE_NAME_KEY) or '').strip())
	return [{'symbol': k, 'name': v} for k, v in sorted(found.items())]


def _values_in_use(tree, name):
	"""Which values of this parameter the entries actually use.

	A value nobody uses may be removed; one that is used may not, because the
	validator refuses an entry whose value is not listed -- so removing it
	would make the table unsaveable by way of a change that looked unrelated.
	"""
	from .flatten import entries_block

	block = entries_block(tree)
	if not isinstance(block, list):
		return set()
	used = set()
	for record in block:
		if isinstance(record, dict):
			value = (record.get('params') or {}).get(name)
			if value is not None:
				used.add(str(value))
	return used


def _apply_values(spec, name, data, allow_key_changes, in_use=()):
	"""The values a symbolic parameter may take.

	Adding one is always safe: it creates identities that did not exist and
	changes none that did. Changing how a value is *written* is safe too, since
	the display is not the identity.

	Renaming a value is not. `v: b` is part of the identity `1.629911,b`, so
	renaming it to `beta` renumbers every entry that uses it -- the citations do
	not break, they resolve and point at different numbers. So an existing key
	is kept as it was unless the table is still a draft, where nothing outside
	can be pointing at it yet.

	A value that entries still use cannot be removed either; the validator
	refuses an entry whose value is not listed, so this would otherwise make a
	table unsaveable by way of a change that looked unrelated.
	"""
	existing = spec.get('values') if isinstance(spec.get('values'), dict) else {}
	built = {}
	prefix = 'parameter.%s.values.' % (name,)

	seen = []
	for form_key in data:
		if form_key.startswith(prefix) and form_key.endswith('.key'):
			index = form_key[len(prefix):-len('.key')]
			if index not in seen:
				seen.append(index)

	for index in seen:
		key = (data.get('%s%s.key' % (prefix, index)) or '').strip()
		was = (data.get('%s%s.was' % (prefix, index)) or '').strip()
		shown = (data.get('%s%s.display' % (prefix, index)) or '').strip()
		if was and not allow_key_changes:
			#Shown, editable-looking or not, the stored key is what counts.
			key = was
		if not key:
			continue
		built[key] = shown or key

	#A value the entries still use may not disappear, whatever the form sent.
	#One nobody uses may: a list that can only grow is a list nobody tidies.
	for key, shown in existing.items():
		if key in in_use:
			built.setdefault(key, shown)

	if built:
		spec['values'] = built
	else:
		spec.pop('values', None)

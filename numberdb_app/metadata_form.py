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

from .validate import DATA_TYPES, PARAMETER_TYPES

__all__ = ['fields_from', 'apply_to', 'COMPLETENESS_ANSWERS']

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
	return {
		'title': str(tree.get('Title') or ''),
		'data_type': str(properties.get('type') or ''),
		'data_types': sorted(DATA_TYPES),
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
		out.append({
			'name': name,
			'type': str(spec.get('type') or ''),
			'constraints': str(spec.get('constraints') or ''),
			'display': str(spec.get('display') or ''),
		})
	return out


def apply_to(tree, data):
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
		_set(properties, 'type', (data.get('data_type') or '').strip())

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

	_apply_parameters(out, data)
	return out


def _apply_parameters(out, data):
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

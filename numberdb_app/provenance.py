"""What made this write, from what the submitter declared.

A write may say what produced it, in headers a runner sets and a person may
set by hand:

    X-Run-Id      20260918T072306Z         the run this belongs to
    X-Pipeline    table-build@2.7+9f3ac1d2 name, version and digest of the scope
    X-Stage       build
    X-Engine      codex-cli                or claude-code, or a script's name
    X-Model       gpt-5.5
    X-Effort      xhigh
    X-Session     01a0b365-...             the harness's own session id
    X-Campaign    20260918T035359Z
    X-Batch       BATCH-2026-09-17T2308
    X-Machine     aws-builder

All optional. A write that declares none of them is a person at a keyboard,
and that absence is the honest record of one -- see
docs/design/pipeline-provenance.md, which explains why an interactive session
is recorded as a run and a hand edit is not.

Nothing here is verified, for the same reason `rigour: heuristic` is not: the
machine checks what it can, and what it can check is that a digest matches the
version it claims. The rest is stated, attributed and revisable.
"""

from django.utils import timezone

#: Header to field. Kept as data because the same map documents the API
#: reference, and two lists of header names drift.
DECLARED = (
	('X-Pipeline', 'pipeline'),
	('X-Stage', 'stage'),
	('X-Engine', 'engine'),
	('X-Model', 'model'),
	('X-Effort', 'effort'),
	('X-Session', 'session'),
	('X-Campaign', 'campaign'),
	('X-Batch', 'batch'),
	('X-Machine', 'machine'),
)

#: How long a declared field may be before it is somebody's mistake rather
#: than a value. The model's own limits are larger; this is the polite cut.
LONGEST = 80


def split_label(text):
	"""`table-build@2.7+9f3ac1d2` -> (name, version, digest)."""
	name, _, rest = (text or '').strip().partition('@')
	version, _, digest = rest.partition('+')
	return name.strip()[:64], version.strip()[:32], digest.strip()[:64]


def declared(request):
	"""What this request says made it, as a plain dict. Empty when it says nothing."""
	found = {}
	for header, field in DECLARED:
		value = (request.headers.get(header) or '').strip()
		if value:
			found[field] = value[:LONGEST]
	run_id = (request.headers.get('X-Run-Id') or request.GET.get('run')
	          or '').strip()
	if run_id:
		found['run_id'] = run_id[:80]
	return found


def run_for(request, user):
	"""The run this write belongs to, created or updated. None when none is declared.

	Two rules, both learned from what the old free-text field did wrong:

	  * **a run is identified, not described.** Writes that name the same run
	    land on one row, so a campaign stage that sends fifty entries is one
	    run and not fifty producers;
	  * **nothing already recorded is overwritten with a blank.** A later write
	    in the same run may know less than the first -- the entries submission
	    knows the run id, the generator's publish knows the model -- and a
	    record that forgot what it had been told would be worse than none.
	"""
	from .models import AgentRun

	said = declared(request)
	if not said:
		return None

	run_id = said.pop('run_id', '') or said.get('session', '')
	pipeline, version, digest = split_label(said.pop('pipeline', ''))
	if not run_id:
		#Nothing identified the run, so identify it by what did speak: the
		#tool, the person and the day. A session that forgets to send its id
		#still groups, rather than leaving a row per request.
		stamp = timezone.now().strftime('%Y%m%d')
		run_id = '%s:%s:%s' % (pipeline or said.get('engine') or 'unknown',
		                       getattr(user, 'username', 'anonymous'), stamp)

	#A digest is computed by `agents/pipeline.py` and by nothing else, so a
	#label carrying one came from a runner that knows what it ran. Without it
	#the pipeline is a claim typed by hand, which is worth recording and worth
	#distinguishing.
	source = 'run' if digest else 'declared'

	run, created = AgentRun.objects.get_or_create(
		run_id = run_id[:80],
		defaults = dict(started=timezone.now(), source=source,
		                operator=user if user and user.is_authenticated else None,
		                pipeline=pipeline, pipeline_version=version,
		                pipeline_digest=digest, **said))
	if created:
		return run

	changed = []
	for field, value in list(said.items()) + [('pipeline', pipeline),
	                                          ('pipeline_version', version),
	                                          ('pipeline_digest', digest)]:
		if value and not getattr(run, field, ''):
			setattr(run, field, value)
			changed.append(field)
	if run.source == 'declared' and source == 'run':
		run.source = 'run'
		changed.append('source')
	if user is not None and getattr(user, 'is_authenticated', False) \
			and run.operator_id is None:
		run.operator = user
		changed.append('operator')
	if changed:
		run.save(update_fields=changed)
	return run


def sentence(run, fallback='api'):
	"""The one line `produced_by` shows, built from a run.

	The field stays because a reader wants a sentence rather than a join, and
	the sentence is now generated from the record instead of being the record.
	"""
	if run is None:
		return fallback
	parts = []
	if run.engine:
		parts.append(run.engine)
	if run.model and run.model != run.engine:
		parts.append(run.model)
	who = ' '.join(parts)
	label = run.label
	if who and label and run.pipeline not in ('interactive', 'script'):
		return '%s, %s' % (who, label)
	if who:
		return who
	return label or fallback

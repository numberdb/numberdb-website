"""Keeping computed values on disk, so a run can be resumed or abandoned.

A generator of expensive values fails in two ways that have nothing to do with
mathematics: the process dies, and the network does. Sending each value as it
is computed answers the first and depends on the second continuously -- a claim
refreshed over a connection that drops is a claim that lapses for a reason
unrelated to the work.

Computing into a local cache and submitting once answers both. The network is
needed at one moment, and if it fails then, nothing has been lost and the
submission can simply be repeated. It also makes stopping deliberate: a run
interrupted half way has published nothing, and whoever noticed the mistake
decides whether to send what is there.

**The cache must know when it is stale.** A cached value produced by code that
has since changed is the worst thing this could hand back: a wrong number that
looks exactly like a right one, arriving with the authority of having been
computed. So every entry is stored under a fingerprint of the code that made
it, and a fingerprint that does not match is not a cache miss to be worked
around -- it is a different computation, and its values are ignored.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Iterator, Mapping, Optional

__all__ = ['RunCache', 'fingerprint_of']


def _cache_root() -> str:
	"""Where caches live: $NUMBERDB_CACHE, else the usual per-user place."""
	named = os.environ.get('NUMBERDB_CACHE')
	if named:
		return named
	base = (os.environ.get('XDG_CACHE_HOME')
	        or os.path.join(os.path.expanduser('~'), '.cache'))
	return os.path.join(base, 'numberdb')


def fingerprint_of(generator, digits, bounds) -> str:
	"""What identifies this computation, so a changed one is not resumed.

	The generator's own source, its declared parameters and type, the precision
	asked for and the bounds it was called with. Change any of them and the
	values are a different computation's values.

	Falls back to the compiled code when the source cannot be read -- a class
	defined in a session has no file -- because the alternative is a cache that
	silently spans a code change.
	"""
	import inspect

	parts = [
		'parameters=%r' % (tuple(getattr(generator, 'parameters', ())),),
		'type=%r' % (getattr(generator, 'type', ''),),
		'digits=%r' % (digits,),
		'bounds=%r' % (sorted((str(k), repr(v)) for k, v in
		                      (bounds or {}).items()),),
	]

	source = None
	try:
		source = inspect.getsource(type(generator))
	except (OSError, TypeError):
		pass
	if source is not None:
		parts.append('source=%s' % (source,))
	else:
		#No file to read. The compiled bodies still change when the code does,
		#which is what this has to detect.
		for name in ('value', 'enumerate', 'all_entries'):
			method = getattr(type(generator), name, None)
			code = getattr(method, '__code__', None)
			if code is not None:
				parts.append('%s=%r' % (name, code.co_code))

	digest = hashlib.sha256('\n'.join(parts).encode('utf8')).hexdigest()
	return '%s-%s' % (type(generator).__name__[:40], digest[:16])


class RunCache:
	"""Computed values on disk, for one generator and one set of arguments.

	Written as YAML, one document per entry, appended as each is computed. It
	is a file somebody opens when a run misbehaves, so it is written to be
	read:

	    ---
	    identity: '17'
	    entry:
	      params: {n: '17'}
	      number: 3.14159?

	YAML rather than CSV because an entry may carry a comment or a proof
	alongside its value, and columns would either lose them or turn into a
	column holding a serialised blob. Appended rather than rewritten because
	the process may die at any moment: a document torn in half costs the one
	value it held, since a document that will not parse is skipped when the
	cache is read.
	"""

	def __init__(self, generator, digits, bounds, path=None):
		self.fingerprint = fingerprint_of(generator, digits, bounds)
		#Named for the fingerprint, so a changed generator reads an empty cache
		#rather than its predecessor's values, and so the file somebody opens
		#says which computation it belongs to.
		self.path = path or os.path.join(_cache_root(),
		                                 '%s.yaml' % (self.fingerprint,))
		self._known = None
		self._handle = None

	#-- reading ---------------------------------------------------------

	def known(self) -> Dict[str, Dict[str, Any]]:
		"""Every entry already computed, by identity.

		Entries written under another fingerprint are not here: the file is
		named for the fingerprint, so a changed generator reads an empty cache
		rather than somebody else's values.
		"""
		if self._known is not None:
			return self._known

		self._known = {}
		if not os.path.exists(self.path):
			return self._known
		with open(self.path, 'r', encoding='utf8') as handle:
			text = handle.read()

		for chunk in text.split('\n---\n'):
			chunk = chunk.strip()
			if not chunk:
				continue
			if chunk.startswith('---'):
				chunk = chunk[3:].lstrip('\n')
			row = _read_document(chunk)
			#A document torn in half by a process dying mid-write. One value
			#recomputed is the whole cost.
			if not isinstance(row, dict):
				continue
			identity = row.get('identity')
			if identity is not None:
				self._known[str(identity)] = row
		return self._known

	def has(self, identity: str) -> bool:
		return identity in self.known()

	def get(self, identity: str) -> Optional[Dict[str, Any]]:
		row = self.known().get(identity)
		return row.get('entry') if row else None

	def __len__(self) -> int:
		return len(self.known())

	#-- writing ---------------------------------------------------------

	def put(self, identity: str, entry: Mapping[str, Any]) -> None:
		"""Record one computed entry, and get it onto the disk now.

		Flushed and synced deliberately: a cache that loses the last hour
		because it was still in a buffer is not doing the one job it has.
		"""
		os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
		row = _write_document({'identity': identity, 'entry': dict(entry)})
		with open(self.path, 'a', encoding='utf8') as handle:
			handle.write('---\n' + row)
			handle.flush()
			os.fsync(handle.fileno())
		if self._known is not None:
			self._known[identity] = {'identity': identity, 'entry': dict(entry)}

	def entries(self) -> Iterator[Dict[str, Any]]:
		"""The cached entries, in the order they were computed."""
		for row in self.known().values():
			yield row['entry']

	def forget(self) -> None:
		"""Throw the cache away, for a run that should start again."""
		if os.path.exists(self.path):
			os.remove(self.path)
		self._known = None


def _read_document(text):
	"""One cached document, however it was written.

	YAML when PyYAML is installed, which it is wherever a generator runs, and
	JSON otherwise -- JSON being a subset, a file written by one is read by the
	other, so a cache does not become unreadable because an environment
	changed.
	"""
	try:
		import yaml
	except ImportError:
		try:
			return json.loads(text)
		except ValueError:
			return None
	try:
		return yaml.safe_load(text)
	except Exception:
		return None


def _write_document(row):
	"""One cached document, written to be read by a person."""
	try:
		import yaml
	except ImportError:
		return json.dumps(row, ensure_ascii=False) + '\n'
	return yaml.dump(row, sort_keys=False, allow_unicode=True,
	                 default_flow_style=False)

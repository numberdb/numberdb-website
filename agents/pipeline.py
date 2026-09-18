"""Which pipeline made this, and which version of it.

    python3 agents/pipeline.py label table-build       the label to record now
    python3 agents/pipeline.py history table-build     every version there ever was
    python3 agents/pipeline.py at <commit> table-build the label as of a commit
    python3 agents/pipeline.py list                    the pipelines and their scope

A *pipeline* is a prompt plus the code that runs it plus the instructions it
reads, and the question "which version of that made this table" had no answer:
`agents/table-build/PROMPT.md` changed 33 times between the first table and the
hundredth, and every revision recorded the same eight words.

What makes the question answerable is deciding **scope**, and scope cannot be
decided globally: the pipeline that builds a table from a proposal is not the
one that will build a tag's table, and neither is the critique-and-repair loop.
So each pipeline declares its own, in a manifest beside it:

    name:  table-build
    major: 2
    files:
      - agents/table-build/PROMPT.md
      - agents/run.sh
      ...

and the label is `table-build@2.7+9f3ac1d2`, where

  * `major` is declared by hand and bumped when the shape changes;
  * `7` is the position of this digest among the distinct digests that manifest
    has had, in commit order -- computed here, never typed, so it cannot drift;
  * `9f3ac1d2` is the first eight hex of sha256 over `(path, contents)` for the
    manifest's files in manifest order. It is the authority; the version is a
    name for it.

The manifest is part of its own digest: changing the list of files changes the
pipeline, and a scheme where that went unrecorded would be measuring the wrong
thing.

`history` reconstructs versions that existed before any of this was written, by
walking the commits that touched the scope. That is what the backfill uses.
"""
import argparse
import hashlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: Where the manifests live, one file per pipeline.
MANIFESTS = os.path.join(HERE, 'pipelines')


def _git(*args, at=None):
	"""git, from the repository root, as text. None when it fails."""
	try:
		out = subprocess.run(('git',) + args, cwd=ROOT, check=True,
		                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
	except (subprocess.CalledProcessError, OSError):
		return None
	return out.stdout.decode('utf-8', 'replace')


def _read(path, at=None):
	"""A file's bytes in the working tree, or at a commit. None when absent."""
	if at is None:
		full = os.path.join(ROOT, path)
		if not os.path.exists(full):
			return None
		with io.open(full, 'rb') as handle:
			return handle.read()
	try:
		out = subprocess.run(('git', 'show', '%s:%s' % (at, path)), cwd=ROOT,
		                     check=True, stdout=subprocess.PIPE,
		                     stderr=subprocess.DEVNULL)
	except (subprocess.CalledProcessError, OSError):
		return None
	return out.stdout


def _parse(text):
	"""The manifest, without a YAML parser.

	Three keys and a list of paths; a dependency for that would be a dependency
	the build machines have to carry.
	"""
	found = {'files': []}
	key = None
	for line in text.splitlines():
		line = line.split('#', 1)[0].rstrip()
		if not line.strip():
			continue
		if line.lstrip().startswith('- ') and key:
			found.setdefault(key, [])
			if isinstance(found[key], list):
				found[key].append(line.lstrip()[2:].strip())
			continue
		if ':' in line:
			key, _, value = line.partition(':')
			key = key.strip()
			value = value.strip()
			if value:
				found[key] = value
	return found


def manifest(name, at=None):
	"""One pipeline's manifest, as of the working tree or a commit."""
	path = 'agents/pipelines/%s.yaml' % (name,)
	raw = _read(path, at=at)
	if raw is None:
		return None
	found = _parse(raw.decode('utf-8', 'replace'))
	found['path'] = path
	found.setdefault('name', name)
	found.setdefault('major', '1')
	found.setdefault('majors', [])
	if not isinstance(found.get('files'), list):
		found['files'] = []
	return found


def _is_ancestor(older, newer):
	try:
		return subprocess.run(('git', 'merge-base', '--is-ancestor', older,
		                       newer), cwd=ROOT,
		                      stdout=subprocess.DEVNULL,
		                      stderr=subprocess.DEVNULL).returncode == 0
	except OSError:
		return False


def major_at(name, commit):
	"""Which major this pipeline was on at a commit.

	Declared in the manifest as `majors: - 2 from 33ab14c9`, because a major is
	a claim about when the *shape* changed and only a person knows that. Without
	the declaration every past version would be stamped with today's major,
	which would say the pipeline never changed shape at all.
	"""
	found = manifest(name)
	if found is None:
		return '1'
	major = '1'
	for line in found.get('majors') or []:
		number, _, since = line.partition(' from ')
		number, since = number.strip(), since.strip()
		if not number or not since:
			continue
		if since in ('start', 'beginning') or _is_ancestor(since, commit):
			major = number
	return major


def names():
	"""Every pipeline that declares itself, in name order."""
	if not os.path.isdir(MANIFESTS):
		return []
	return sorted(f[:-5] for f in os.listdir(MANIFESTS) if f.endswith('.yaml'))


def digest(name, at=None, manifest_at=None):
	"""sha256 over the scope, and which of its files were found.

	Missing files are recorded as missing rather than skipped: a pipeline whose
	prompt has been deleted is a different pipeline, and a digest that ignored
	the deletion would say it was the same one.
	"""
	found = manifest(name, at=manifest_at if manifest_at is not None else at)
	if found is None:
		#Before the manifest existed the pipeline still did, so the scope is
		#read from today's manifest and the digest says what those files held
		#then. That is what makes the history reconstructible at all; it also
		#means a file added to the scope later changes every past digest, which
		#is why `history` is recomputed rather than stored.
		found = manifest(name)
	if found is None:
		return None, []
	sha = hashlib.sha256()
	seen = []
	for path in [found['path']] + list(found['files']):
		body = _read(path, at=at)
		sha.update(path.encode('utf-8'))
		sha.update(b'\0')
		if body is None:
			sha.update(b'<absent>')
			seen.append((path, None))
		else:
			sha.update(hashlib.sha256(body).digest())
			seen.append((path, len(body)))
		sha.update(b'\n')
	return sha.hexdigest(), seen


def touching(name, at=None):
	"""Commits that touched this pipeline's scope, oldest first."""
	found = manifest(name, at=at)
	if found is None:
		return []
	paths = [found['path']] + list(found['files'])
	out = _git('log', '--reverse', '--format=%H %at', '--', *paths)
	if not out:
		return []
	commits = []
	for line in out.splitlines():
		parts = line.split()
		if len(parts) == 2:
			commits.append((parts[0], int(parts[1])))
	return commits


def history(name):
	"""Every version this pipeline has had: (major, minor, digest, commit, when).

	One entry per *distinct* digest, in commit order. A commit that touches a
	file in scope without changing what the scope hashes to -- a comment in
	run.sh, a file moved back -- is not a version.
	"""
	versions = []
	previous = None
	for commit, when in touching(name):
		major = major_at(name, commit)
		sha, _ = digest(name, at=commit, manifest_at=commit)
		if sha is None or sha == previous:
			continue
		previous = sha
		minor = sum(1 for v in versions if v[0] == major)
		versions.append((major, minor, sha, commit, when))
	return versions


def label(name, at=None):
	"""`table-build@2.7+9f3ac1d2`, or None when the pipeline is unknown.

	`at=None` means the working tree, whose digest may match no commit -- an
	edited prompt that has not been committed. The minor is then the next one,
	and the digest says which state it really was.
	"""
	sha, _ = digest(name, at=at)
	if sha is None:
		return None
	past = history(name)
	current = manifest(name, at=at) or manifest(name)
	major = (current or {}).get('major', '1')
	for one_major, minor, seen, _commit, _when in past:
		if seen == sha and one_major == major:
			return '%s@%s.%d+%s' % (name, major, minor, sha[:8])
	minor = sum(1 for v in past if v[0] == major)
	return '%s@%s.%d+%s' % (name, major, minor, sha[:8])


def resolve(text):
	"""Split a recorded label back into (name, major, minor, digest)."""
	name, _, rest = (text or '').partition('@')
	version, _, sha = rest.partition('+')
	major, _, minor = version.partition('.')
	return name, major, minor, sha


#---------------------------------------------------------------- commands

def cmd_list(args):
	for name in names():
		found = manifest(name)
		sha, seen = digest(name)
		print('%-16s major %-3s %d files  %s'
		      % (name, found.get('major', '1'), len(seen), label(name)))
		if args.verbose:
			for path, size in seen:
				print('    %-60s %s' % (path, 'absent' if size is None
				                        else '%d bytes' % size))
	return 0


def cmd_label(args):
	found = label(args.name, at=args.at)
	if found is None:
		print('no manifest for %r' % (args.name,), file=sys.stderr)
		return 2
	print(found)
	return 0


def cmd_history(args):
	past = history(args.name)
	if not past:
		print('no history for %r' % (args.name,), file=sys.stderr)
		return 2
	import datetime
	for major, minor, sha, commit, when in past:
		stamp = datetime.datetime.utcfromtimestamp(when).strftime('%Y-%m-%d')
		subject = (_git('log', '-1', '--format=%s', commit) or '').strip()
		print('%s@%s.%-3d %s  %s  %s  %s'
		      % (args.name, major, minor, sha[:8], stamp, commit[:8],
		         subject[:60]))
	return 0


def cmd_dump(args):
	"""Every version of every pipeline, as JSON.

	The backfill runs on the server, where the deployed tree is a copy with no
	`.git` in it, so the history cannot be reconstructed there. It is computed
	here, where the repository is, and carried over as data.
	"""
	import json

	found = {}
	for name in names():
		found[name] = [
			{'major': major, 'minor': minor, 'version': '%s.%d' % (major, minor),
			 'digest': sha, 'commit': commit, 'when': when}
			for major, minor, sha, commit, when in history(name)]
	print(json.dumps(found, indent=1))
	return 0


def cmd_at(args):
	found = label(args.name, at=args.commit)
	if found is None:
		print('no manifest for %r at %s' % (args.name, args.commit),
		      file=sys.stderr)
		return 2
	print(found)
	return 0


def main(argv=None):
	parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
	sub = parser.add_subparsers(dest='command')

	listing = sub.add_parser('list')
	listing.add_argument('-v', '--verbose', action='store_true')
	listing.set_defaults(run=cmd_list)

	naming = sub.add_parser('label')
	naming.add_argument('name')
	naming.add_argument('--at', default=None, help='a commit, not the tree')
	naming.set_defaults(run=cmd_label)

	past = sub.add_parser('history')
	past.add_argument('name')
	past.set_defaults(run=cmd_history)

	sub.add_parser('dump').set_defaults(run=cmd_dump)

	at = sub.add_parser('at')
	at.add_argument('commit')
	at.add_argument('name')
	at.set_defaults(run=cmd_at)

	args = parser.parse_args(argv)
	if not getattr(args, 'run', None):
		parser.print_help()
		return 2
	return args.run(args)


if __name__ == '__main__':
	sys.exit(main())

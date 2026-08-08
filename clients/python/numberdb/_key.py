"""Where the API key comes from when nobody passed one.

Exporting a variable works and is what a server wants. It is not what somebody
running a generator from a directory wants: the export lives in one shell, is
gone from the next, and the usual repair -- putting it in the script -- is how
a key ends up in a repository.

So four places are looked at, in this order, and the first that has one wins:

1. what the caller passed to ``Client(api_key=...)`` or `numberdb.configure`
2. ``NUMBERDB_API_KEY`` in the environment
3. ``.env`` in the working directory, or the nearest one above it
4. ``~/.config/numberdb/env``

Third and fourth exist for different people. A `.env` belongs to one project
and travels with it, which is convenient and is also how keys get committed;
the per-user file belongs to the person and is in no project directory at all,
so it cannot be committed by accident.

**Nothing here is executed.** A .env is read as `NAME=value` lines and nothing
else -- no shell, no substitution, no `export` semantics beyond ignoring the
word. A configuration file that runs is a configuration file that can be made
to run something else.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

__all__ = ['api_key', 'read_env_file']

#: The variable, in every place that has one.
VARIABLE = 'NUMBERDB_API_KEY'

#: How far up from the working directory a `.env` is looked for. Enough to
#: cover a script in a subdirectory of its project, and few enough that a run
#: in a home directory does not walk to the root reading files.
SEARCH_UP = 4


def api_key(given: Optional[str] = None) -> str:
    """The key to use, from the first place that has one.

    Never raises. A missing key is not an error here -- reading is public, and
    the refusal belongs at the point where writing is attempted, where it can
    say what was being attempted.
    """
    if given:
        return given

    from_environment = os.environ.get(VARIABLE)
    if from_environment:
        return from_environment

    found = _from_dot_env()
    if found:
        return found

    return _from_user_config() or ''


def _from_dot_env() -> str:
    here = os.path.abspath(os.getcwd())
    for _step in range(SEARCH_UP + 1):
        candidate = os.path.join(here, '.env')
        if os.path.isfile(candidate):
            value = read_env_file(candidate).get(VARIABLE)
            if value:
                return value
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return ''


def _from_user_config() -> str:
    base = (os.environ.get('XDG_CONFIG_HOME')
            or os.path.join(os.path.expanduser('~'), '.config'))
    path = os.path.join(base, 'numberdb', 'env')
    if not os.path.isfile(path):
        return ''
    return read_env_file(path).get(VARIABLE, '')


def read_env_file(path: str) -> Dict[str, str]:
    """``NAME=value`` lines, as a mapping. Anything else is skipped.

    Quotes around a value are removed, because every example anybody copies has
    them half the time, and a key with a quotation mark in it is a key that
    fails authentication for a reason nobody will guess.
    """
    found = {}  # type: Dict[str, str]
    try:
        with open(path, 'r', encoding='utf8') as handle:
            lines = handle.readlines()
    except OSError:
        return found

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[len('export '):].lstrip()
        if '=' not in line:
            continue
        name, _, value = line.partition('=')
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '\'"':
            value = value[1:-1]
        if name:
            found[name] = value
    return found

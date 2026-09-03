"""Keep the tests away from whoever is running them.

`numberdb.api_key()` looks in four places, and two of them belong to the
person at the keyboard: `NUMBERDB_API_KEY` in the environment, and
`~/.config/numberdb/env`. That is right for the package and wrong for its
tests, which then exercise a live credential instead of the absence of one.

On 2026-09-03 running this suite on a laptop that had a key in
`~/.config/numberdb/env` failed `test_no_key_sends_no_authorization_header`
-- and printed the key into the failure message, which is how a real key
ended up in a terminal transcript. The test was right that something was
wrong; it was reading the developer's credentials to find out.

Set at import, before any test is collected, because most of these are
`unittest.TestCase` classes and this must hold for all of them however they
are run.
"""

import os
import tempfile

os.environ.pop('NUMBERDB_API_KEY', None)
#`_from_user_config` reads $XDG_CONFIG_HOME/numberdb/env, falling back to
#~/.config. Pointing it at an empty directory covers both.
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='numberdb-tests-')

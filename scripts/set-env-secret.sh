#!/usr/bin/env bash
# Set one secret in .env without it being echoed, logged, or left in history.
#
#     ./scripts/set-env-secret.sh EMAIL_MG_API_KEY
#
# Typing a secret on a command line puts it in ~/.bash_history, in the process
# list while the command runs, and in any shell transcript. Editing .env in an
# editor is safer but easy to get wrong: a stray newline inside a value breaks
# the file in a way that only shows up when something fails to authenticate.
#
# This prompts with the terminal echo off, writes the value in place, and
# prints nothing but the length back.

set -euo pipefail

name="${1:-}"
env_file="${ENV_FILE:-.env}"

if [ -z "$name" ]; then
	echo "usage: $0 VARIABLE_NAME [--show-current]" >&2
	echo "  e.g. $0 EMAIL_MG_API_KEY" >&2
	exit 2
fi

if [ ! -f "$env_file" ]; then
	echo "no $env_file here. Run this from the deployment directory." >&2
	exit 2
fi

if ! grep -q "^$name=" "$env_file"; then
	echo "warning: $name is not currently in $env_file; it will be appended." >&2
fi

#-s turns off echo and -r stops backslashes being interpreted. Read from the
#terminal where there is one, so this still works with stdin redirected; fall
#back to stdin where there is not, which is what makes it testable and lets it
#be driven from a password manager:
#
#    bw get password numberdb-mailgun | ./scripts/set-env-secret.sh EMAIL_MG_API_KEY
printf 'Value for %s (input hidden): ' "$name" >&2
if [ -r /dev/tty ] && [ -t 1 ]; then
	read -rs value < /dev/tty
else
	read -rs value
fi
echo >&2

if [ -z "$value" ]; then
	echo "empty value, nothing changed." >&2
	exit 1
fi

#Written by python rather than sed: a key containing &, |, / or a backslash
#would otherwise be mangled by the replacement syntax, and the result would
#look plausible while failing to authenticate.
VALUE="$value" NAME="$name" FILE="$env_file" python3 - <<'PY'
import os

name, value, path = os.environ['NAME'], os.environ['VALUE'], os.environ['FILE']
lines = open(path).read().split('\n')
prefix = name + '='
for i, line in enumerate(lines):
    if line.startswith(prefix):
        lines[i] = prefix + value
        break
else:
    #Appended before any trailing blank line, so the file keeps its shape.
    while lines and lines[-1] == '':
        lines.pop()
    lines.append(prefix + value)
    lines.append('')
open(path, 'w').write('\n'.join(lines))
print('  %s set (%d characters)' % (name, len(value)))
PY

unset value
chmod 600 "$env_file"
echo "  $env_file permissions: $(stat -c %a "$env_file")"
echo
echo "Next: docker compose up -d web    # then manage.py check should fall silent"

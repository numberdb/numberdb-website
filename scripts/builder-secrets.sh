#!/usr/bin/env bash
# Put a build machine's credentials in place, from Parameter Store.
#
#     scripts/builder-secrets.sh          # on the builder itself
#
# Three interactive logins per machine is not a way to have more than one
# machine: `claude /login`, `codex login` and `gh auth login` each need a
# browser and a person, and the person is the bottleneck. So the credentials
# live once, encrypted, in SSM under /numberdb, and a machine reads its own.
#
# Nothing is baked into an image and nothing is copied between laptops. The
# instance has a role -- `numberdb-builder-role` -- whose policy allows
# exactly `ssm:Get*` on `/numberdb/*` and `kms:Decrypt` through SSM, so there
# is no key on the disk to steal and rotating a credential in one place
# updates every machine that reads it.
#
# Re-runnable: rotate a value in SSM, run this again, and the machine has it.
set -euo pipefail

REGION="${AWS_DEFAULT_REGION:-eu-central-1}"
PREFIX="${NUMBERDB_SSM_PREFIX:-/numberdb}"

command -v aws >/dev/null 2>&1 || {
	echo "no aws cli here; install it first" >&2; exit 2; }

fetch() {  # parameter, destination, mode
	local name="$PREFIX/$1" out="$2" mode="${3:-600}"
	local value
	if ! value=$(aws ssm get-parameter --name "$name" --with-decryption \
			--region "$REGION" --query Parameter.Value --output text 2>/dev/null); then
		echo "  $1: not in Parameter Store, skipped"
		return 0
	fi
	mkdir -p "$(dirname "$out")"
	#Written through a temporary file with the mode set first, so the secret
	#is never briefly world-readable on its way to disk.
	local tmp
	tmp=$(mktemp)
	chmod "$mode" "$tmp"
	printf '%s' "$value" > "$tmp"
	mv "$tmp" "$out"
	chmod "$mode" "$out"
	echo "  $1 -> $out"
}

echo "fetching credentials from $PREFIX in $REGION"
fetch claude-credentials "$HOME/.claude/.credentials.json"
fetch codex-auth "$HOME/.codex/auth.json"
fetch zeta3-key "$HOME/.config/numberdb/zeta3-key"
fetch bmatschke-key "$HOME/.config/numberdb/bmatschke-key"

#gh reads a token from the environment rather than a file, so it goes where a
#login shell will find it. `gh auth login` is then never needed on a builder.
if token=$(aws ssm get-parameter --name "$PREFIX/gh-token" --with-decryption \
		--region "$REGION" --query Parameter.Value --output text 2>/dev/null); then
	umask 077
	printf 'export GH_TOKEN=%s\n' "$token" > "$HOME/.numberdb-gh"
	grep -q 'numberdb-gh' "$HOME/.bashrc" 2>/dev/null \
		|| printf '\n[ -f "$HOME/.numberdb-gh" ] && . "$HOME/.numberdb-gh"\n' >> "$HOME/.bashrc"
	echo "  gh-token -> \$GH_TOKEN via ~/.numberdb-gh"
fi

echo
echo "checking what they unlock:"
export GH_TOKEN="${GH_TOKEN:-$(sed -n 's/^export GH_TOKEN=//p' "$HOME/.numberdb-gh" 2>/dev/null)}"
printf '  gh      : %s\n' "$(gh auth status 2>&1 | grep -oE 'Logged in to [^ ]+ account [^ ]+' | head -1 || echo 'not working')"
printf '  claude  : %s\n' "$([ -s "$HOME/.claude/.credentials.json" ] && echo 'credentials in place' || echo 'missing')"
printf '  codex   : %s\n' "$([ -s "$HOME/.codex/auth.json" ] && echo 'credentials in place' || echo 'missing')"
printf '  numberdb: %s\n' "$([ -s "$HOME/.config/numberdb/zeta3-key" ] && echo 'keys in place' || echo 'missing')"

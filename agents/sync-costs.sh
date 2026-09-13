#!/usr/bin/env bash
# Send this machine's ledger to the site.
#
#     agents/sync-costs.sh
#
# Over the API, with the key the runs already use. It used to copy the file to
# the server over ssh and run a management command there, which works from the
# one laptop that has a key for that server and nowhere else -- so costs from
# the AWS builder never arrived at all, and the overview quietly under-counted
# whatever it had spent.
#
# Never fatal. A ledger that did not reach the site is worth a warning; it is
# not worth failing a run that produced a table.
set -uo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

LEDGER="${NUMBERDB_LEDGER:-agents/runs/COSTS.tsv}"
HOST="${NUMBERDB_HOST:-https://numberdb.org}"
KEY_FILE="${NUMBERDB_KEY:-$HOME/.config/numberdb/zeta3-key}"

[ -s "$LEDGER" ] || { echo "sync-costs: no ledger at $LEDGER"; exit 0; }
[ -s "$KEY_FILE" ] || { echo "sync-costs: no key at $KEY_FILE" >&2; exit 0; }

key=$(cat "$KEY_FILE")
# Base64: a header value may hold neither a newline nor a record separator,
# and a server refuses the second as firmly as the first.
attribution=""
[ -f agents/runs/ATTRIBUTION.tsv ] && \
	attribution=$(base64 -w0 < agents/runs/ATTRIBUTION.tsv)

# Direct first, then through the tunnel: the same reasoning as everywhere else
# here, since the laptop can only reach numberdb.org through a proxy and the
# builder cannot reach the proxy.
send() {
	curl -sS --max-time 120 -X POST "$HOST/api/costs" \
		-H "Authorization: Bearer $key" \
		-H "Content-Type: text/tab-separated-values" \
		${attribution:+-H "X-Attribution: $attribution"} \
		--data-binary "@$LEDGER" "$@"
}

answer=$(send --noproxy '*' 2>/dev/null)
if [ -z "$answer" ]; then
	answer=$(ALL_PROXY="${NUMBERDB_PROXY:-socks5h://127.0.0.1:1080}" send 2>/dev/null)
fi

case "$answer" in
	*'"rows"'*)
		echo "sync-costs: $(printf '%s' "$answer" | tr -d '{}"' )"
		;;
	'')
		echo "sync-costs: the site did not answer; the ledger stays here" >&2
		;;
	*)
		echo "sync-costs: refused: $(printf '%s' "$answer" | head -c 200)" >&2
		;;
esac
exit 0

#!/usr/bin/env bash
# Put the run ledger's costs into the site's database.
#
#     agents/sync-costs.sh
#
# The overview page reads `TableCost`, and the ledger that prices every run
# lives here, beside the runs, on whoever's machine ran them. Until this
# existed the two were joined by somebody remembering to run
# `manage.py import_agent_costs`, and nobody did: eleven tables built over two
# nights showed no cost at all on a page whose whole subject is what a table
# cost to make.
#
# Two steps, because the database is on the server and the ledger is not: copy
# the file into the deployed tree, where `on-server.sh` already mounts
# `agents` read-only, and then import it there. Rows are replaced rather than
# added, so running this twice leaves the same numbers.
#
# Called at the end of every run by `agents/run.sh`, and safe to run by hand.
# It never fails a run: a ledger that did not reach the database is worth a
# warning and nothing more.

set -uo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

REMOTE="${NUMBERDB_REMOTE:-linode}"
RPATH="${NUMBERDB_RPATH:-/opt/numberdb-website}"
LEDGER="agents/runs/COSTS.tsv"
ATTRIBUTION="agents/runs/ATTRIBUTION.tsv"

[ -f "$LEDGER" ] || { echo "no ledger at $LEDGER" >&2; exit 0; }

#Bounded, because this runs at the end of every agent run and a server that
#has stopped answering must not stop the campaign: on 2026-09-10 this hung on
#an unreachable host with no connect timeout, and the run behind it waited
#with it. A ledger that did not reach the site is worth a warning, so every
#step here fails fast and carries on.
ssh_opts=(-o BatchMode=yes -o ExitOnForwardFailure=no -o ConnectTimeout=15
          -o ServerAliveInterval=15 -o ServerAliveCountMax=4
          -o ControlMaster=auto -o ControlPath=/tmp/numberdb-ssh-%r@%h:%p
          -o ControlPersist=60)
STEP_TIMEOUT="${NUMBERDB_SYNC_TIMEOUT:-120}"

timeout "$STEP_TIMEOUT" ssh -n "${ssh_opts[@]}" "$REMOTE" \
	"mkdir -p '$RPATH/agents/runs'" || {
	echo "sync-costs: could not reach $REMOTE" >&2; exit 0; }
timeout "$STEP_TIMEOUT" scp "${ssh_opts[@]}" -q "$LEDGER" \
	"$REMOTE:$RPATH/$LEDGER" || {
	echo "sync-costs: could not copy the ledger" >&2; exit 0; }
#Beside it, where the importer looks: which table a run was about, for the
#runs whose ledger row could not say. Optional -- a corpus whose runs all
#named their table has no such file.
if [ -f "$ATTRIBUTION" ]; then
	timeout "$STEP_TIMEOUT" scp "${ssh_opts[@]}" -q "$ATTRIBUTION" \
		"$REMOTE:$RPATH/$ATTRIBUTION" || \
		echo "sync-costs: could not copy the attributions" >&2
fi
"$here/agents/on-server.sh" manage.py import_agent_costs "$LEDGER" \
	2>&1 | tail -1

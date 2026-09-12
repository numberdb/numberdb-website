#!/usr/bin/env bash
# Give a campaign a working tree of its own, so two can run at once.
#
#     scripts/campaign-worktree.sh knots
#     cd ../numberdb-campaign-knots
#     NUMBERDB_CAMPAIGN=knots NUMBERDB_BATCH=agents/table-ideas/BATCH-....md \
#     NUMBERDB_REMOTE=builder NUMBERDB_SAGE_IMAGE=numberdb/builder:latest \
#         agents/campaign.sh 15
#
# Campaigns cannot share a checkout. Every run refuses to start in a dirty
# tree, diffs the tree afterwards to see what it produced, and commits the
# cost ledger when it finishes -- so two campaigns in one directory read each
# other's half-written files as their own output, stop each other for
# uncommitted changes, and race on the same index.
#
# A git worktree is the cheap fix: separate tree, separate index, separate
# HEAD, one shared object store. Commits from either are ordinary commits on
# their own branch, and merging afterwards is the usual thing.
#
# What it does NOT fix, and what the branch name cannot: two campaigns working
# from the same batch will build the same proposal, because a build skips only
# what `generators/` in *its own* tree already answers. Give each campaign its
# own batch with NUMBERDB_BATCH until claiming moves to the site, where both
# campaigns can see the same answer.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

NAME="${1:-}"
[ -n "$NAME" ] || { echo "usage: $0 <campaign name>" >&2; exit 2; }

tree="../numberdb-campaign-$NAME"
branch="campaign/$NAME"

[ -e "$tree" ] && { echo "already there: $tree" >&2; exit 1; }

# From the current HEAD rather than from main: a campaign should start from
# what is deployed, and that is what you are standing on.
git worktree add -b "$branch" "$tree" HEAD

# The runs directory is per-tree and gitignored, so each campaign keeps its own
# transcripts; the ledger they append to is per-tree too, and reaches the site
# through sync-costs.sh, which is where the two campaigns' numbers meet.
mkdir -p "$tree/agents/runs"
cp -p agents/runs/COSTS.tsv "$tree/agents/runs/COSTS.tsv" 2>/dev/null || true

cat <<NOTE

=== worktree $tree on branch $branch

Run the campaign from there:

    cd $tree
    NUMBERDB_CAMPAIGN=$NAME \\
    NUMBERDB_BATCH=agents/table-ideas/BATCH-<pick one>.md \\
    NUMBERDB_REMOTE=<builder> NUMBERDB_SAGE_IMAGE=numberdb/builder:latest \\
        agents/campaign.sh 15

Stop just this one with:

    touch $tree/agents/campaign.$NAME.stop

When it is done, merge the branch and remove the tree:

    git -C $here merge --no-ff $branch
    git -C $here worktree remove $tree
NOTE

already fixed -- the live table no longer has 32 rows over $D=12,13,17$; it has 1171 rows over $D\in\{5,8,12,13,17,21\}$ with conductor norm at most $250$, and an `agents/sage.sh` source-count check against the pinned ecnf-data commit found the same 1171 positive-rank labels.
already fixed -- the live table already says the first positive-rank conductor norms over $D=5$ and $D=8$ are $199$ and $103$; I checked those minima from the pinned `mwdata` files with `agents/sage.sh`.
already fixed -- the conductor-norm bound has already been raised from $60$ to $250$, and the live/source counts now include $17$ rows for $D=5$ and $63$ rows for $D=8$.
declined -- I did not raise the bound to $500$, because the live table already has 1171 entries and the report itself names 1200 entries as the corpus soft limit.
already fixed -- the table has already added $D=21$, with 348 live rows matching the pinned source labels.
declined -- I did not add $D=24,28,29,33,\ldots$, because adding more fields would push a 1171-entry table past the soft limit before any mathematical gain was weighed by a person.
already fixed -- the source is still ecnf-data at commit `10b28418e80392032b106ea00e6c5aa109d28e7b`, as checked in the live rigour details.
already fixed -- every live number has 35 significant digits, and the rigour details still explain the truncation from unstable final source digits.
already fixed -- the live rank note has been rechecked and narrowed: $D\in\{5,8,12,13,17\}$ has only rank $1$ rows, while $D=21$ has rank $1$ and rank $2$ rows; I checked the rank split from the live comments.
already fixed -- the live rigour details still state the generator checks rank $1$ regulators against source generator heights, recomputes the rank $2$ height-pairing determinants over $D=21$, and checks the BSD quotient against the recorded analytic order of Sha.
already fixed -- the size warning is now active rather than theoretical: the live table has 1171 entries, so I left the range alone and the audit returned `clean: true`.

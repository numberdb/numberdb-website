1. already fixed -- changed nothing: the live table no longer has 32 rows; it has 823 positive-rank rows over $D\in\{5,8,12,13,17\}$ with conductor norm at most $250$, with counts $17,63,253,195,295$ for $D=5,8,12,13,17$.
2. already fixed -- the live table already states that the smallest positive-rank conductor norms over $D=5$ and $D=8$ are $199$ and $103$ in the pinned ecnf-data source, and the rendered page shows that comment.
3. already fixed -- the conductor-norm bound has already been raised to $250$ and the $D=5$ and $D=8$ entries are present; running the generator with `agents/sage.sh` reported `823/823 matched, 0 differing, 0 missing, 0 extra`.
4. left for a person -- did not add $D=21,24,28,29,33,\dots$: the report gives no cutoff or field range for that second axis, so extending beyond the five named fields is a range decision.
5. already fixed -- the generator and live rigour details still pin ecnf-data commit `10b28418e80392032b106ea00e6c5aa109d28e7b`.
6. already fixed -- the values are kept to $35$ significant digits, and the live rigour details still explain that the final source digits are not stable.
7. already fixed -- the rank statement has already been narrowed to the chosen range; every row verified by the generator is rank $1$.
8. already fixed -- the generator checks each regulator against the source height of the recorded generator and checks the BSD quotient against the source analytic order of Sha before returning the value.
9. already fixed -- the final table is 823 rows, below the soft entry limit, and the keyed audit endpoint returned no findings.

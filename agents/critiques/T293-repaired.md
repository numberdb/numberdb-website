1. done -- the live table still had 32 positive-rank rows over $D=12,13,17$ and a completeness note for $D\in\{5,8,12,13,17\}$ with conductor norm at most $60$; extended it to conductor norm at most $250$ over the same five fields.
2. done -- checked the pinned ecnf-data commit directly and confirmed the first positive-rank conductor norms are $199$ for $D=5$ and $103$ for $D=8$; added that fact as a table comment.
3. done -- regenerated the source data from ecnf-data commit `10b28418e80392032b106ea00e6c5aa109d28e7b`, previewed the generator, and added 791 rows without removing the existing 32.
4. left for a person -- did not add $D=21,24,28,29,33,\dots$: the report gives no cutoff, and using the same conductor-norm bound $250$ would produce 3577 rows and rank-$2$ cases, beyond the table's usual soft entry limit.
5. done -- kept the values at $35$ significant digits by truncating the source regulator strings, and a full preview checked that all 32 old rows remained unchanged byte-for-byte.
6. done -- rechecked the rank statement for the chosen extension: all 823 stored rows over $D\in\{5,8,12,13,17\}$ with conductor norm at most $250$ have rank $1$.
7. done -- the generator checked every stored regulator against the source height of the recorded generator and checked the Birch and Swinnerton-Dyer quotient against the recorded analytic order of Sha.
8. already fixed -- the live table no longer has the four-parameter address warned about in the report; it uses the two parameters $D$ and the LMFDB label without the field prefix.
9. done -- measured the final table at 823 rows, with counts $17,63,253,195,295$ for $D=5,8,12,13,17$, then verified `823/823 matched` and the audit endpoint returned no findings.

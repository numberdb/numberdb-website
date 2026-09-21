1. done -- Added the factorisation comment and first-Riemann-zero row links; checked with `agents/sage.sh` that the first Riemann zero occurs in exactly nine T385 rows.
2. done -- Completed the verified T4 row links for $D=49$ and $D=81$ and left $D=169,361$ unlinked because T4 has no conductor-13 or conductor-19 rows; checked the row map with `agents/sage.sh`.
3. done -- Replaced the conductor-$7$ wording with explicit $D=49$, $D=81$ and conductor-$\sqrt D$ wording after confirming the old wording was still live.
4. done -- Changed the prose and entry comments from bare `C3` and `S3` to $C_3$ and $S_3$; the edited render has no bare group occurrences in entry comments.
5. done -- Reworded the entry-comment description and changed the defining equations from $x$ to $a$; a mechanical check confirmed the numeric values and parameter order were unchanged.
6. done -- Added that no two cubic fields with $|D|\leq500$ share a discriminant, so $k=1$ throughout; checked this against T159 restricted to $|D|\leq500$ with `agents/sage.sh`.
7. done -- Removed `Links[Request72]`, which was still present, unused, and not a mathematical source for this table.
8. done -- Reworded `rigour details` to say every value is stored to 30 significant digits and the two computations agree to at least that many; checked all stored values have 30 significant digits with `agents/sage.sh`.
9. done -- Added that a missed zero would shift every later index in that field, preserving the existing PARI `lfunzeros` caveat.
10. done -- Added that the LMFDB label is the LMFDB number-field label and its final component is not this table's $k$.
11. done -- Added the meaning of $(r_1,r_2)$ to the completed-zeta formula; the edited render and live audit were clean.

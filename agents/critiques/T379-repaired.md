1. done -- rewrote the Definition and added `formula-moment`; checked CFKRS for the symmetry-type moment exponents and ran a Sage/Fraction check that the three product formulas still reproduce all 36 stored rows.
2. done -- retitled the draft to say it holds random-matrix factors $g_G(k)$, not the moments themselves; checked the live title still made the broader claim before changing it.
3. done -- added a scaling comment saying the table stores $e_G(k)!f_G(k)$; checked the stored rows from the formulas, including that the rows here are integral for $U$ and $O$ and rational for $USp$.
4. done -- cited `KeatingSnaith`, `MehtaNormand`, and `WikiRMT` from the prose; checked the repaired document has no uncited declared link or reference.
5. done -- replaced the unnamed "Euler-product tables" sentence with explicit `HREF{T377}` and `HREF{T378}` links; checked the repaired document contains both HREFs.
6. done -- replaced the Sage program with named imports for `factorial`, `prod`, and `QQ`, a `g(G,k)` function for all three groups, and a `print`; checked the original raises `NameError` and the replacement runs under `agents/sage.sh`.
7. done -- changed the unitary formula from $k^2!$ to $(k^2)!$; checked the formula output still matches every stored unitary row.
8. left for a person -- adding the `L-function` tag is plausible because of the sibling tables, but the table is also genuinely a random-matrix table, so I left the subject tag decision to review.

<<<<<<< HEAD
1. done -- added the $g=7$ and $g=8$ rows, after checking the live table still had only $g=1,\ldots,5$, verifying LT's lower-bound polynomials and the Aaber-Dunfield, Kin-Takasawa, and Hironaka realizations from the sources, and confirming in Sage that the isolated roots match the cited decimals.
2. done -- updated the kept generator, formula, program, references, completeness note, rigour details, and entry comments; `publish(overwrite=False)` preview reported 2 added, 0 updated, 5 left alone, and the final generator verification reported 7/7 matched.
3. done -- expanded `comment-salem` after checking in Sage that $g=2,\ldots,5$ have one conjugate outside the unit circle while $g=7,8$ each have three, so the new values are reciprocal Perron numbers but not Salem numbers.
4. done -- checked numeric lookup with the $g=5$ value as a control; the control returned T285, the Coxeter-triangle table, and T284, while the $g=7$ and $g=8$ values returned no reviewed corpus hits.
5. done -- refreshed `generators/minimum-dilatations-pseudo-anosov-maps/table.yaml` from the repaired live document, omitting the generated `Numbers` block, so it no longer carries the stale pre-repair prose.
=======
done -- reattached the seven-genus `generate.py`; before changing it I checked the live attachment still enumerated only $g=1,\ldots,5$, compared it with the updated source, and ran it under `agents/sage.sh`, which reported `7/7 matched, 0 differing, 0 missing, 0 extra`.
done -- changed the completeness note to say what genus $6$ is waiting for: Lanneau and Thiffeault's lower bound for genus $6$ is $\delta_5^+$ itself, and Hironaka's survey states that the exact value is not known. I checked the live note still had the old wording and verified in Sage that $x^{12}-x^7-x^6-x^5+1=(x^2-x+1)P_5(x)$ with the same real root greater than $1$ as $P_5$.
declined -- left the $g=7$ and $g=8$ entry comments as they are, because they state which realization theorem turns the cited lower bound into an exact value.
left for a person -- the two new values still wait on review for numeric search, and zeta3 may not publish or review them.
declined -- did not add neighbouring families to T285; the braid, nonorientable-surface, and Lanneau-Thiffeault-root families are different quantities and would need separate tables.
declined -- did not edit the stale campaign/w3 generator or `table.yaml`; the live repair used the verified updated generator from `main`, and the worktree lag is already recorded as an environment trap rather than a table fault.
>>>>>>> origin/campaign/w3

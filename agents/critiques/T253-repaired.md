1. *done* -- removed the claim that many radicals are also in T35; checked the live T35 document and the exact squared magnitudes in Sage, finding 158 distinct irrational squared magnitudes and only three non-rational T253 rows in T35.
2. *done* -- replaced the unscoped Mathar claim with the checks the generator actually performs, and added the all-row SageMath `wigner_6j` comparison; checked all 485 stored rows against Sage after initializing Sage fully.
3. *done* -- added Racah's finite sum and wrote out the Wigner $3j$ expansion; checked DLMF 34.4 and verified the $3j$ sum on sample rows in Sage.
4. *done* -- rewrote the symmetry comment to say which 24 tetrahedral symmetries are used and that the value is unchanged by them; checked the generator recomputes every row at all 24 images.
5. *done* -- rewrote the zero/all-zero omission sentence so it no longer gives the value $1$ as the reason; checked the stored set is the 485 nonzero nontrivial canonical classes.
6. *done* -- rewrote the admissibility comment to say the triangle conditions are necessary but not sufficient; checked there are 490 canonical admissible classes including the all-zero symbol and four nontrivial vanishing classes.
7. *done* -- rewrote the zero-entry formula in the table's $j_i$ notation and stated the transposed-pair condition; checked the formula against Sage examples, including a row needing symmetry first.
8. *left for a person* -- T252 is still a private draft link, and publishing order is a reviewer decision rather than an author repair.
9. *done* -- replaced the prose-only `formula-3j-sum` with the DLMF finite sum and changed the citation from Wikipedia to DLMF; previewed the formula with no broken `CITE` or `HREF` markers.
10. *done* -- removed the undefined Racah $W$ formula by replacing it with Racah's finite sum, and cited the existing Sage link from `rigour details`; previewed the changed citations.
11. *done* -- expanded `complete-note` to say the table holds the nonzero canonical classes through $j_i\leq7/2$, excluding the all-zero symbol, and that this gives a compact 485-row small-angular-momentum range; checked the count in Sage.
12. *declined* -- left the six parameter lines flat because the repaired symmetry and admissibility comments now explain the joint conditions, and giving the interchangeable positions different roles would be misleading.

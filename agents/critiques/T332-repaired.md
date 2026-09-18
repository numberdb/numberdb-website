1. left for a person - the live API still reports the slug `Chern_classes_of_smooth_complete_intersections_in_mathbb_P_n`, and `/T332` plus the slug page still return 404 for this private draft; recreating the draft under a new title is an address decision.
2. done - rewrote the completeness note to make the three bounds conjunctive and to say that $\prod_i d_i$ is the degree bound; Sage checked 999 expected rows, 999 stored rows, no missing rows, no extra rows and no formula mismatches.
3. left for a person - Sage confirmed the critique still applies, with 140 curve rows, 18 distinct curve values and two rows equal to `1`; removing them or justifying them changes the table's range.
4. done - replaced the Calabi-Yau comment with a scoped definition and added `CYWiki`; Sage checked on every row that $a_1=0$ is equivalent to $\sum_i d_i=n+1$, and the cited article supports the vanishing first Chern class/trivial canonical class wording.
5. done - reordered `rigour details` to lead with the Euler-characteristic and quintic checks; the final Sage run rechecked all stored polynomials and the revised program sample.
6. done - added the missing comment to entry `6,2,2,3`; Sage checked that the five Calabi-Yau threefold rows are exactly `(5)`, `(2,4)`, `(3,3)`, `(2,2,3)` and `(2,2,2,2)`.
7. done - changed the Programs block from `sage.all` to `numberdb.sage` plus named imports and added the quintic-entry comment; Sage executed the revised block and matched entries `4,5` and `10,9`.
8. left for a person - the final audit still has only the singleton `characteristic classes` tag finding; keeping it for the planned sibling tables is a reviewer decision, not a table edit.
9. done - the Calabi-Yau comment now cites Formula `formula-first` instead of restating it; Sage checked the cited equivalence on every row.
10. done - reordered `Links` so `CIWiki` precedes `ChernWiki` and added `CYWiki`; the live API now returns the order `CIWiki`, `ChernWiki`, `CYWiki`.
11. done - tightened the Definition so the coefficients $a_i$, not a dangling pronoun, carry the independence claim; the follow-up audit no longer reports the Definition-length finding introduced by the first draft.
12. done - added the reason for excluding $k=n$ beside the degree-one exclusion; Sage checked sample $k=n$ cases under the same formula and got $c(T_X)=1$.

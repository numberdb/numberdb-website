1. done -- added a blank line in `rigour details` after checking the live field still had a single newline, then confirmed the audit stayed clean.
2. done -- changed the node-family notation from $T_n$ to $X_n$ in the definition, parameter display, formula, and number header, leaving $T_n$ for the Chebyshev polynomial.
3. done -- rewrote `complete-note` to say the range is a rectangular comparison range and that the next Gauss--Legendre row is already multi-minute; Sage computed that $n=5$ row in about 236 seconds before the wrapper returned its timeout status.
4. done -- removed the private repository path and numberdb-data issue from `rigour details`, and replaced the vague independent-check sentence with the small-degree closed forms Sage checked from the node sets.
5. done -- added a comment explaining the shared $n=1$ and $n=2$ node sets, after Sage checked the node coincidences and the resulting values $1$ and $5/4$.
6. done -- changed the equally spaced and Newton--Cotes relations from "same nodes" to affine equivalence, after reading the linked tables and checking the affine map from $[-1,1]$ nodes to $0,\ldots,n$.
7. done -- replaced the repeated definition formula with a formula defining the Lebesgue function $\lambda_n(x;X_n)$ and then $\Lambda_n(X_n)$.
8. done -- linked the Chebyshev node coordinates to the $\cos(\pi x)$ table, after checking T61 holds rational arguments covering all Chebyshev coordinates in this table's range.
9. done -- replaced the circular `family` constraint with the six named node families.
10. done -- swept the displayed Gauss--Legendre, Gauss--Lobatto, and Newton--Cotes spellings in comments, family glosses, and Similar tables; ASCII keywords were left for search.
11. declined -- left `Programs` as the attached-generator snippet, because Sage ran it successfully for `equally-spaced, n=5` and there is no standard Sage/PARI/mpmath one-liner for this quantity.
12. left for a person -- did not add the optional odd-$n$ Chebyshev--Lobatto identity, because it is not a fault and a general theorem would need more than finite checking before becoming a formula.

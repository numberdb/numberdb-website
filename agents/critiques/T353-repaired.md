1. done -- added `formula-half-integers`; checked all 615 live rows in Sage against an independent closed form from `t = sin^2(theta)`, including the 336 algebraic rows and the 279 rows with an arcsin term.
2. done -- replaced the broad complement-check claim in `rigour details`; checked in Sage that the 297 rows with `x > 1/2` have their constructed complements and that the 21 rows at `x = 1/2` are the genuine direct complement checks.
3. done -- kept the distribution keywords but earned them with a visible comment about the beta CDF and the Student t two-sided tail; checked in Sage that all `nu = 1,...,5`, `t = 1,2` Student-tail arguments are stored.
4. done -- changed the maintained and attached `generate.py` so publishing uses `generator.publish(...)` instead of the private `fill_draft_once`; before attaching it, `agents/sage.sh` verified `615/615 matched`.
5. done -- added the Student t reason to `complete-note`; checked in Sage that the named `nu = 1,...,5`, `t = 1,2` grid is present.
6. done -- replaced the duplicate unregularised/regularised comment with the distribution comment; the regularisation formula remains in `Formulas`.
7. done -- replaced the principal-value sentence with the positive-real-branch convention for the powers in the integral; the live parameters still have `0 < x < 1` and `a,b > 0`.
8. done -- changed the Gamma similar-table relation so it explains the Gamma quotient used to normalise `B(x;a,b)` into `I_x(a,b)`.
9. done -- changed the generator docstring to name all `_is_rational_row` omission cases; checked in Sage that the grid has 775 possible rows, 160 rational omissions and 615 stored rows.
10. left for a person -- T348 is still a draft (`/T348` and its slug are 404 anonymously, while the keyed API reads it), so publication order remains a reviewer decision and I did not remove the intended companion link.
11. declined -- this was a list of things the critique explicitly was not asking to change; the live API readback and audit are clean, and T353 remains a private draft whose rendered page is 404.

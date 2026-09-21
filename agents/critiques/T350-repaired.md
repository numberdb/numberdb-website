1. done -- added the Similar tables row for T349 after reading T349 through the API and verifying `Values_of_the_incomplete_elliptic_integral_of_the_first_kind` resolves to that draft.
2. done -- added the amplitude-reduction formula; checked DLMF 19.2 and verified 40 finite ball-arithmetic cases in Sage with maximum difference radius about `1.3e-74`.
3. done -- replaced the `complete-note`; checked the live grid has 12 amplitudes, 46 elliptic parameters for each, and 552 entries with no omitted rows.
4. done -- rewrote the definition as sentences in the $m=k^2$ convention; checked the definition against DLMF and the cited Wikipedia article.
5. done -- rewrote the complete first-kind and third-kind Similar tables relations so each names the quantity and relation it means.
6. done -- changed "the row with $\varphi=\pi/2$" to "the entries with $\varphi=\pi/2$"; checked the live table has 46 such entries.
7. done -- changed the amplitude constraint to `$0<\varphi/\pi\leq 1/2$`; checked it matches the displayed parameter.
8. done -- changed the amplitude parameter title to "amplitude ratio" and added the `elliptic amplitude` keyword; checked the cited sources use amplitude for $\varphi$.
9. done -- added citations to the parameter-convention comment; checked DLMF for the modulus notation and Wikipedia for the modular-angle notation tied to Abramowitz and Stegun.
10. done -- renamed `comment_1` to `comment-parameter`; checked `comment_1` appeared only as its own key.
11. declined -- did not add the hypergeometric tag or Appell formula, because that is an optional expansion and the critique itself said not to add the tag without the formula.
12. declined -- left `period` and `elliptic curves`, because the critique judged the browse-sideways tag convention worth keeping and T25, T26, T59, and T349 use the same pair.
13. declined -- left the attached generator's `NUMBERDB_TABLE` override, because its default is `T350` and changing the source file was not needed to repair the table.

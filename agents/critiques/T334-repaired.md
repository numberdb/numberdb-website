1. done -- changed `complete-note` to say `\mathrm{Td}_8` is the first component needing more than six variables; checked by Sage that variable counts for `n=1..11` are `1,2,2,4,4,6,6,8,8,10,10` and locally confirmed seven-variable polynomial search keys are refused.
2. done -- replaced the website-search sentence in `comment-odd` with the coefficient formula; checked in Sage that the coefficient of `c_n` is `B_n^+/n!` through `n=11`.
3. done -- reordered `rigour details` so the visible first sentence contains the outside checks; checked the rendered repaired page shows those checks before the `more` fold.
4. done -- rewrote `comment-variables` to cite the two declared sources and removed the promise about characteristic-class tables; checked the cited pages and confirmed corpus search for Pontryagin tables returned none.
5. done -- added a Sage `Programs` block computing `todd_component(8)` by exact Bernoulli coefficients and Newton identities; ran that exact snippet with `agents/sage.sh`.
6. done -- removed `formula-zero` and rewrote `comment-zero` to state `\mathrm{Td}_0=1` once; checked the rendered page has only the two remaining formulas and no broken `formula-zero` citation.
7. done -- changed Formula (1) to say the `x_i` are the Chern roots; checked the cited Todd-class source states the Chern-root product definition.
8. done -- added the `\operatorname{td}` notation to `comment-variables` and added keyword `td polynomials`; checked the repaired render shows the notation sentence cleanly.
9. declined -- the audit still reports `characteristic classes` as reaching only this table, but the tag is shared by the draft batch and publishing order is a reviewer decision, so I left it.
10. declined -- this was already sound; Sage confirmed seven stored entries are exactly the range under the six-variable cap and the live page still orders rows `n=1` through `n=7`.
11. declined -- no separate table edit belongs to this observation; after the repair, `/api/table/T334/audit` reports only the same draft-tag finding.

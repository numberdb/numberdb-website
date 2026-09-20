1. *done* -- doubled the PARI comment marker in `Programs`; checked the live stored snippet failed in GP while the doubled version, and then the repaired live snippet, printed `2/15`.
2. *done* -- removed `Request22` from `Links`; checked the GitHub issue body is null and contains no mathematical content that would justify citing the request.
3. *done* -- removed both HREFs to the regulators draft; checked `/Regulators_of_quartic_fields` still answers 404 while the keyed API can see only an unpublished draft.
4. *done* -- removed the constant signature and `$w_K=2$` text from all 612 entry comments and from the attached generator, then stated them once in `comment-range`; checked all 204 fields had those constants before the edit.
5. *done* -- expanded `comment-index` to explain why `$k$` exists, to say the LMFDB label is `$4.4.D.k$`, and to name $D=16448,28224$; checked those are exactly the two repeated discriminants and the labels match every row.
6. *done* -- rewrote `rigour details` to say the generator uses PARI `nflist` over the five degree-4 transitive groups, pins the count at 204, and checks the functional equation at $\zeta_K(2),\zeta_K(4),\zeta_K(6)$; checked those claims in the attached generator.
7. *done* -- replaced the duplicated abelian factorisation in `comment-abelian` with `CITE{formula-abelian}` and named `$B_{2m,\chi}$`; adjusted the wording after audit flagged an unlinked Bernoulli phrase.
8. *done* -- added the Riemann zeta row to `Similar tables` and rewrote the Bernoulli rows to name `$B_{2m}$` and `$B_{2m,\chi}$`; checked the post-repair audit is clean.
noted-denominators. *done* -- removed the method sentence from `comment-denominators` and kept the recognition method in `rigour details`, where it belongs.
noted-definition. *done* -- shortened the Definition and made the analytic continuation explicit; checked the post-repair audit no longer reports a long definition.
noted-collisions. *declined* -- the repeated small values at $s=-1$ are a mathematical feature and the critique itself says no change is wanted.
noted-generator-leak. *declined* -- the draft generator being publicly readable is a site/deployment issue already recorded elsewhere, not a T366 table repair.
audit-notes. *done* -- ran `GET /api/table/T366/audit` after the edits and fixed the two findings I introduced; the final audit returns `{"findings": [], "clean": true}`.

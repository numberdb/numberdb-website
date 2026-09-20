1. done -- clarified the endpoint comment by spelling out T92's lower-bound Sobolev normalization; checked T92's live definition and ran T358's Sage generator checks, which matched all 18 endpoints against T354 and the available T92 rows.
2. done -- removed `formula-endpoint`; checked the live `rigour details` references only `formula-constant` and `formula-extremal`, and the final live formula keys are those two.
3. done -- rewrote the notation comment to name $a$ and the left-hand norm's exponent $2a$ directly; previewed the edited comment without MathJax errors.
4. done -- added the quantifier in the Definition and defined $D_a(\mathbb{R}^n)$ in Comments; checked Del Pino-Dolbeault's Theorem 1 defines $D_p(\mathbb{R}^d)$ by the same three conditions with $p=a$, $d=n$.
5. done -- extended the completeness note with the reason for denominator bound $8$; checked in Sage that denominator at most $4$ gives 43 rows and only endpoint rows for every $n>9$, while denominator at most $8$ gives the stored 145-row range.
6. done -- changed the Sage program's final line to `print(A)`; ran it in Sage and checked its ball overlaps the stored `n=3, a=2` value.
7. done -- put `CITE{DelPinoDolbeault2002}` before `CITE{WikiGN}` so the rendered citation order follows the reference numbering.
8. done -- rewrote the T356 and T357 similar-table relations to name their Fourier-transform and convolution inequalities; checked the live definitions of T356 and T357 before changing them.
9. declined -- the rendered `comment:` prefix is still a site label, not table text; the live JSON entry comments contain only the Sobolev endpoint sentence.
audit functional analysis tag. declined -- the audit still counts only published tables, while `/api/tag?url=functional%20analysis` lists published T92 and the live drafts T354 through T358 carry the same tag.
audit inequality tag. declined -- the audit still counts only published tables, while `/api/tag?url=inequality` lists published T92 and the live drafts T354 through T358 carry the same tag.

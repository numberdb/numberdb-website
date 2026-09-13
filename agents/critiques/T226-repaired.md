1. *done* -- Rewrote the Definition and `comment-convention` to define $\gamma$ and separate $\psi$ from $H_x$; checked the live draft still had the ambiguous sentence, T16 row `0` is $\gamma_0$, and the repaired comment renders its row link.
2. *done* -- Changed the `quantity` parameter title to `$\psi(x)$ or $H_x$`; checked the live draft still had `title: quantity` and left the parameter key/display unchanged.
3. *done* -- Deleted `comment-range` and moved the shift reason into `complete-note`; checked the live duplicate was present, the generator has no separate reason for denominator $12$, and Sage verified the $\psi$ and $H$ shift differences on 138 base/shift pairs.
4. *done* -- Changed stored `complete` from `false` to `no` and quoted `complete: 'no'` in `table.yaml`; checked `metadata_form.py` accepts only `yes`, `no` and `unknown`, and preview rendered "Table is complete: no (...)".
5. *done* -- Replaced the keyword `generalized harmonic number` with `harmonic number`; checked the cited harmonic-number source uses generalized harmonic number for $H_{n,m}$.
6. *done* -- Rewrote the Stieltjes similar-table relation to link `HREF{Stieltjes_constants#0}[$\gamma_0$]`; checked T16's row key is `0` and preview renders the row URL.
7. *done* -- Added "integers" to Gauss's formula; checked Sage's ball-arithmetic version of the formula for all 45 reduced $p/q$ with $q\leq12$.
8. *done* -- Rewrote `comment-exact-harmonic` to say $\psi(n)=H_{n-1}-\gamma$ for positive integers $n$; checked it from the recurrence and reran full table verification.
9. *left for a person* -- Left $H_0=0$ and $H_1=1$ in place because removing exact rows from the family is a range decision.
10. *declined* -- Left Formula (5) unchanged because T145 states the same $L(1,\chi)$ digamma identity and the wording is true enough to keep.
11. *done* -- Rewrote the Hurwitz zeta similar-table relation to the Laurent expansion at $s=1$ with constant term $-\psi(x)$; checked the relation against the Hurwitz zeta Laurent-expansion source and T94's title/definition.
12. *declined* -- Left the Programs snippet unchanged because it already runs and the full generator verification matched 729/729 entries after the repair.
13. *declined* -- Left the extra closed forms out because Gauss's formula covers the denominator $4$ and $6$ cases, so this is convenience rather than a correctness gap.

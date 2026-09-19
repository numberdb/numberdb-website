audit: declined -- nats and bits are two logarithmic units for the same $H(X)$, now stated in the definition and still converted by Formula (1); the audit warning is the known false positive checked against the live audit.
1. done -- changed the negative-binomial and Zipf labels to name tuple components in stored order; Sage checked `negative-binomial` uses `(r,p)` and Zipf `2,10` is `(s,N)`, not the reverse.
2. done -- added the hypergeometric symmetry formula; Sage checked every hypergeometric row in the table satisfies $H(N,K,n)=H(N,n,K)=H(N,K,N-n)$.
3. done -- removed `RequestedIssue55` after confirming it was only a request link and not cited by the mathematical prose.
4. done -- widened the generator to every two-decimal $p\leq0.50$ for Bernoulli and for the geometric/logarithmic rows while preserving existing entries; the generator's SciPy check passed, the API added 248 entries and left 469 alone, and `verify(sample=None)` matched 717/717.
5. done -- shortened the definition so it names nats and bits without restating the conversion rule, leaving the checked conversion in `Formulas`.
6. done -- rewrote the omitted-rational-bits comment and the seven nats-row comments; Sage checked the omitted bit values are exactly $1$, $2$, $3/2$, $1$, $2$, $3$ and $4$.
7. done -- changed live `complete: false` to `complete: no` and re-read the API document to confirm it.
8. done -- replaced the `shape` constraint with the tuple-order rule, after fixing the two labels whose order had been ambiguous.
9. left for a person -- adding an `information theory` tag needs a cross-table tag decision for T339, T241 and T153, not a one-table repair; T339 keeps the keyword.

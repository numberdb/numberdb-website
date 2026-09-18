Audit length finding: *declined* -- the normal-form list remains in the Definition because it is definitional; the surrounding prose was rewritten and `/api/table/T290/audit` still reports only this length warning.
1. *done* -- changed the reduced b-function root from $1$ to $-1$; Sage checked all rows, finding 26 with $-1$ in the reduced b-function and none with $+1$.
2. *done* -- scoped the table to simple, parabolic unimodal and exceptional unimodal singularities, and added that hyperbolic $T_{p,q,r}$ families are not included; the live parameter constraint and the weighted-homogeneity obstruction $1/p+1/q+1/r<1$ were checked.
3. *done* -- rewrote the Definition so $b_f(s)$ and the role of $n$ are stated directly; the repaired Definition was fetched back from the API and rendered through `/preview`.
4. *done* -- added definitions of $\mu$ and $\operatorname{lct}$ and rewrote row comments as sentences; the generator verified against the live draft with 87/87 rows matched.
5. *done* -- replaced the modulus comment with concrete exceptional-modulus behavior; Singular checked the $E_{12}$ and $Z_{11}$ changes, and the $P_8$, $X_9$ and $J_{10}$ parabolic examples.
6. *done* -- changed the $n$ constraint to "at least the corank of the singularity"; the computed range remains in `complete-note`.
7. *done* -- expanded the Similar-tables relation and fixed the Poincaré caption; Sage checked the ADE exponent residue sets for the rows with $n=3$.
8. *done* -- rewrote `rigour details` to say what was run; the generator self-check computed all 87 rows with Singular's `bfct` after the control.
9. *done* -- replaced the suspension prose by $\tilde b_{f+u^2}(s)=\tilde b_f(s+\frac{1}{2})$; Sage checked 46 adjacent suspension rows.
10. *declined* -- kept the single `polynomial` tag, because no existing tag fits better and a new singularity-theory tag would still be a one-table tag.

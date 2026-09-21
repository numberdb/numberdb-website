done -- Replaced the `Programs` snippet with an mpmath `findroot` example for the next $a=1/3$ zero; `agents/sage.sh /tmp/t386_check.py` reproduced the old `TypeError`, the new root has residual about $10^{-55}$, and arb evaluation of six stored zeros gave residuals at the stored precision.
done -- Defined the Hurwitz zeta convention in a rendered comment, using the $n=0$ series checked against the neighbouring Hurwitz-values table; the first draft made the Definition too long, so I moved the definition out of it and reran the audit cleanly.
done -- Defined $t_n$ in `comment-special-a` as the positive ordinate of the $n$th non-trivial Riemann zero, after checking the live entry comments still used that symbol.
done -- Added Spira's paper title and `zbl: 0341.10034`; Crossref confirmed the DOI metadata and web search confirmed the zbMATH identifier.
done -- Removed the run-mechanics sentence from `comment-strip` and kept the vertical-strip statement Crossref/JSTOR abstracts verify; I did not write the proposed exact endpoints because I could not verify them from accessible paper text.
done -- Deleted the dead `Parameters.n.comments` field after confirming the same ordering sentence remains in the rendered Definition.
done -- Moved the uncertified-zero caveat to the start of `rigour details`, previewed the changed text, and reran the audit cleanly.
done -- Rewrote the $a=1/2$, $n=1$ entry comment as $2\pi\mathrm{i}/\log 2$; this is the $k=1$ case of the same exact factor-zero formula.
done -- Replaced the method-based Dedekind-zeta similar-table relation with a mathematical relation, "stores zeros of another zeta function family".
declined -- Left `complete-note` without a range rationale because the critique did not give a verifiable reason for denominator at most $4$, and guessing one would be worse than the current accurate coverage statement.
done -- Added `CITE{Spira}` to the real-zero caveat after checking Spira's abstract says the paper treats real zeros; I did not add interval claims because I could not verify them from the paper text.
done -- Changed the Dirichlet neighbour caption to the live title, "Zeros of Dirichlet L-series", after checking the linked table.
declined -- Left the exact real parts as stored; the comments now define $t_n$ without adding a new theorem citation, and the Riemann table remains the linked source for the ordinates.
declined -- Left `repeats` absent because T386 stores complex zeros while the Riemann-zero table stores ordinates, so the searchable values are not duplicates.

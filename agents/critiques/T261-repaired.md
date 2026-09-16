1. done -- put the Schur and monomial table links on their captions; the rendered preview shows "the Schur polynomial" and "the monomial symmetric polynomial" rather than bare slugs.
2. done -- added `title: shape` to the $\lambda$ parameter; the rendered preview shows "$\lambda$ -- shape" and no "Unknown type".
3. done -- added `CITE{formula-symmetrization}` to the Definition and moved the monomial-triangular $P$ normalisation into the convention comment; Sage checked all 33 stored partitions have coefficient $1$ on $m_\lambda$ and only lower dominance-order terms.
4. done -- replaced the false $Q_\lambda$/$Q'_\lambda$ sentence with the scalar $Q_\lambda$ normalisation and the transformed $Q'_\lambda$ statement; Sage checked $Q$ and $Q'$ in the $P$ basis for $\lambda=(1,1)$ and $(2,2)$.
5. done -- defined $m_r(\lambda)$ and $\ell(\lambda)$ in the symmetrization formula; the final table audit is clean.
6. left for a person -- T259 still answers 404 at `/T259` while T261 is also a draft, and `GET /api/table/T261/audit` is clean; the publication order remains a reviewer decision.
7. done -- replaced the load-bearing Sage submodule imports with `from sage.all import ...` and made the snippet print the table-style expanded polynomial; the live `Programs` block executed successfully under Sage.
8. done -- changed the completeness note and generator docstring to $1\leq|\lambda|\leq4$; Sage checked $P_\varnothing=1$ while the table stores no empty-partition row.
noted spelling. declined -- both "normalisation" and "specialization" are valid English, and the mixture does not make the mathematics or rendering wrong.
noted keyword. done -- changed "Macdonald Hall polynomials" to "Macdonald Hall-Littlewood polynomials"; this names the intended search phrase without pointing at Macdonald polynomials.
noted formula (4). done -- added the missing $x$ argument and the range of the sum over $\mu$; the final table audit is clean.
noted lambda spacing. declined -- the space in displayed partitions is the site's rendering and the citation key remains the unspaced entry identity.

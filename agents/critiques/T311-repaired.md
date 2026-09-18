1. already fixed -- the live API document already had proper `\tau` and `\ne` before I edited; I checked that by `GET /api/table?id=T311`.
2. done -- changed the T310 caption to `Class polynomials of $\gamma_2$` and checked a live preview snippet renders the whole link without a stray `{j}$]`.
3. done -- rewrote the Definition to identify the monic minimal polynomial; checked every stored row is monic of degree $\ell+1$, matches PARI, and is irreducible over $\mathbb Q(y)$.
4. done -- identified $j$ as the modular $j$-invariant in the Definition; the proposed HREF was not used because the audit rejects table links in Definition.
5. done -- added a level-$3$ comment scoped to the invariant-$5$ modular polynomial; checked `polmodular(3,5)` raises PARI's incompatible-invariant error.
6. done -- changed the PARI program to `polmodular(11, 5)` with a comment distinguishing prime level from invariant number; checked the stored rows match `polmodular(ell,5)`.
7. done -- named the monomial set in rigour details from the generator code, and kept it scoped to the rows in this table.
8. done -- added the symmetry statement to the variable comment; checked every stored row is symmetric in Sage.

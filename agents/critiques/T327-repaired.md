1. done -- added the Ris-Parter explanation to comment (2), after Sage checked exactly for $2\leq n\leq20$ that the Ris matrix is one half of the row-reversed Parter matrix and that the stored strings agree.
2. done -- added the tridiagonal definition of the second-difference matrix to comment (1), after Sage checked the $n=2$ value $3$, the $n=3$ value $3+2\sqrt2$, and agreement between the matrix and $A^{\mathsf T}A$ condition-number routes for $2\leq n\leq20$.
3. done -- extended the Sage program to compute the condition number from the roots of the characteristic polynomial of $A^{\mathsf T}A$, after Sage checked the result lies in the stored interval for `hilbert,3`.
4. done -- replaced the private path in `rigour details` with "a dry run", preserving the list of checks and confirming the audit stayed clean.
5. done -- rewrote the definition to state the 2-norm condition number as the ratio of largest to smallest singular value, then read the whole sentence back from the API.
6. done -- added Wilkinson to the list of Test Matrix Toolbox families in comment (2), matching the Wilkinson definition already present in the same paragraph.
7. done -- replaced the MATLAB slice notation for the Riemann matrix with the equivalent $n\times n$ entry-wise formula, checked from the original $B(2:n+1,2:n+1)$ indexing.
8. left for a person -- the Chow keyword still may be useful because the table explains why no finite Chow entries exist; the critique itself judged this not clear-cut.
9. done -- changed the displayed Kac-Murdock-Szegő label and prose to the accented spelling while leaving the ASCII keyword in place for search.
10. done -- rewrote the singular-matrix sentence to say $\kappa_2(A_n)$ is infinite rather than a real number, so there is no entry.

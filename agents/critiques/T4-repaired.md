1. *done* -- rewrote the Definition and added a `complete-note`; checked the live API/page and verified in Sage that the stored Conrey labels are exactly the primitive characters of conductor $q \leq 11$, with 1075 ordinates.
2. *done* -- tightened the $n$ parameter to primitive Conrey labels and cited `CL`; checked in Sage that the stored labels match the primitive characters and that $q=2,6,10$ contribute none.
3. *done* -- changed `number-header` to $\gamma_k$ and defined $\rho_k=1/2+i\gamma_k$ in the Definition; checked the live table is type `R` and stores ordinates, not complex zeros.
4. *done* -- removed `both signs` from all 1075 ordinate entries and put the real/non-real sign convention in the comments; checked in Sage that the positive-only blocks are exactly the real nontrivial characters in the table.
5. *done* -- replaced `HREF{#CL}` with `CITE{CL}`; checked the old `/T4?entry=CL` warning and the rendered repair, where the parameter title now cites `[4]`.
6. *done* -- rewrote comment (1) to use $L(\chi,s)$, $\sum_{m=1}^\infty$, and convergence for $\Re(s)>1$; checked the statement before writing it.
7. *done* -- rewrote comment (2) to name $L(\chi,s)$, state the trivial zeros by parity, state GRH as a hypothesis, and describe the sign convention without a time-dependent claim.
8. *done* -- added `Similar tables` rows for T3, T145, T324, T142, T385, T386 and T387, and removed the valueless `1,1` entry; checked live slugs/pages and that the ordinate count stayed 1075.
9. *done* -- narrowed the rigour note to the transcription gap while citing Platt's rigorous method and LMFDB as the displayed source; kept `rigour: heuristic`.
10. *left for a person* -- did not reorder the complex-character blocks, because the critique names a real tradeoff between signed monotone order and positive-first paired order.
a. *declined* -- `url:` rendering as plain text is a renderer issue rather than a T4 document fault, and the per-entry LMFDB URLs are still useful.
b. *done* -- removed the costly and misleading `both signs` annotation; kept `url`, because it is the useful half of the repeated metadata.
c. *left for a person* -- did not rename the published title from "L-series" to "L-functions"; the critique identifies it as a title decision.
d. *declined* -- did not add a Programs snippet, because the note calls it optional and any PARI/Sage incantation should be checked as its own small build task.
e. *declined* -- kept the convention that negative ordinates of real characters are omitted; the repaired comment now states the convention explicitly.

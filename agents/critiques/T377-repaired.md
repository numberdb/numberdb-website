1. done -- Marked CITE{formula-moment} conjectural and added a comment scoping the theorem status; checked the CFKRS source calls the general moment formula conjectural and says the leading term agrees with the known second and fourth moment theorems.
2. done -- Reworded rigour details to say "the logarithm of the local factor in CITE{formula-ak}"; checked `/preview` rendered the old `$\log$ CITE{formula-ak}` as adjacent log-plus-citation text and the replacement without that ambiguity.
3. done -- Added a PARI comment saying the program is for positive integer $k$ only; checked under `agents/sage.sh` that the printed program returns the stored-leading digits for $k=3,4$ and fails for $k=5/2,7/2$.
4. done -- Defined $f_U(k)=G(1+k)^2/G(1+2k)$ in the factor comment and linked the Barnes $G$ table in Comments and Similar tables; checked in Sage that $f_U(1)=1$ and $f_U(2)=1/12$, and checked live T93 has every needed $G$ argument.
5. done -- Cited `PARIProdEulerRat` from rigour details beside `prodeulerrat`; checked the link key was already in `Links` and the final live audit was clean.
6. declined -- Adding `moments` made the live audit fail because the tag currently reaches only one published table, so I removed it and recorded the draft-tag lesson.
7. done -- Replaced the $k=2$ entry comment with "the local factor collapses"; checked in Sage that $(1-x)^4(1+x)/(1-x)^3=1-x^2$.

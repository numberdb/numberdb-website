1. *left for a person* -- splitting `radial` and `cartesian` into two tables is a structural decision about the draft's identity, so I left the title, parameters, entries and value header unchanged.
2. *done* -- bracketed the real and imaginary parts in `formula-cartesian`; Sage checked that all 88 Cartesian entries match the formula using `Re((x+i*y)^m)` and `Im((x+i*y)^m)`.
3. *done* -- added that the unnormalised entries are scaled by $R_n^m(1)=1$; Sage checked this on all 100 live radial entries.
4. *done* -- added the range reason to `complete-note`; Sage measured the live largest $n=12$ entries as 365 characters for Cartesian and 65 for radial.
5. *done* -- rewrote `comment-uses` to say the non-monomial entries with $n\leq4$ carry aberration names in both forms and none are given for $n>4$; the live comments have 16 named entries, all in degrees 2, 3 and 4.
6. *done* -- rewrote the Bessel-zero relation to say the Hankel transform has zeros at the positive zeros of $J_{n+1}$, scoped from the displayed $J_{n+1}(v)/v$ formula.
7. *done* -- replaced the circular "checked initial Noll and Fringe lists" wording with the four single indices tabulated for $n\leq4$ in `CITE{Wiki}`; I checked the cited table and the generator's stored source rows before changing it.
8. *done* -- expanded the Sage `Programs` snippet with the Cartesian conversion; Sage checked `radial(22,0)`, `cartesian(13,1)` and `cartesian(12,0)` against the generator.

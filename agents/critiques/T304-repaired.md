done -- changed the `coefficient` constraint from address-key patterns to the mathematical entries $c_i$, $a_{ij}$, and $b^{(q)}_i$; checked the live draft still had the bad key prose and previewed the replacement.
done -- rewrote the Definition so it defines a Butcher tableau and embedded weight rows, then kept the full step equation in Formulas after the audit objected to a longer Definition; checked the rendered preview and the final audit.
done -- replaced the Newton-Cotes relation with the quadrature-rule relation; checked the stored Kutta-3, RK4, and 3/8-rule fractions in Sage, including merging RK4's equal nodes, and left the optional Gauss-Lobatto wording unchanged because I did not verify it.
done -- changed `comment-embedded` to say that one row advances the solution and the other gives the local error estimate; checked the live entry comments name the advancing row for every embedded pair.
done -- replaced the inert checker in Programs with a SciPy inspection snippet; checked the frozen SciPy source for `RK23` and `RK45`, and noted local SciPy was unavailable so the snippet was source-checked rather than run here.
done -- changed visible Runge-Kutta-family hyphens to en dashes in prose, display names, entry comments, link titles, and similar-table captions; kept ASCII spellings in Keywords as search aliases and previewed the result.
done -- changed visible Nystrom text to Nyström while keeping `Nystrom` in Keywords as a search alias.
done -- changed the `coefficient` parameter display to `symbol`, so the rendered columns are no longer two adjacent coefficient headers; previewed the table chunks.
done -- changed `complete-note` to name Wikipedia's list of Runge-Kutta methods, revision 1346207143, and shortened `comment-range` to avoid repeating it.
done -- changed the `method` constraint to "a named explicit Runge–Kutta method or embedded pair with rational coefficients."
done -- changed `formula-error` so the difference is identified as the local error estimate used for step-size control.
declined -- kept the forward Euler first-entry comment, because the first-entry comments consistently list each method's weight rows and removing only this one would cost consistency for little gain.
done -- added `Butcher tableau` to Keywords, along with Runge-Kutta spelling aliases.
left for a person -- did not add a `numerical analysis` tag; the critique frames that as a cross-table tag decision rather than a one-table repair.

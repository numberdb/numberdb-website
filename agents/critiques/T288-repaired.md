1. left for a person -- verified in Sage that T288's $\ell=1$, $3\leq k\leq7$ rows are byte-for-byte the same as T287's rows, but did not choose whether to keep both tables with `repeats`/`equals` or withdraw T287.
2. done -- removed the $(k,\ell)=(2,1)$ row and the zero convention from the definition, formula, program and rigour details; checked the no-root claim by reducing it to $h(x)=x-2+(x+2)e^{-x}$ with $h'(x)>0$ for $x>0$, and ran the edited program for $(3,1)$, $(2,2)$ and $(2,1)$ under `agents/sage.sh`.
3. done -- deleted `formula-root`, whose content repeated the definition; the final live audit is clean.
4. done -- rewrote `comment-convention` to say what threshold the root determines and to cite the declared links; checked the rendered preview for resolved `HREF`s and `CITE`s.
5a. done -- rewrote `comment-capacity-one` to say $\xi_{k,1}$ is T287's XORSAT root and points to T272's threshold table; checked the rendered preview.
5b. done -- defined $\mathrm{Po}(x)$ in `formula-tail`, after the first repair made the definition too long and the audit caught it.
5c. done -- changed `complete-note` to name the actual covered rectangle with $(2,1)$ excluded.
5d. declined -- did not add the near-integer asymptotic sentence, because the critique marked it as a nice fact rather than a fault.
5e. declined -- did not add the `XORSAT` keyword, because that belongs only if a person chooses option 1(b) and folds T287 into this table.

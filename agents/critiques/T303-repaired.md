1. done -- changed `formula-lagrange` and the Lagrange similar-table relation to T112's shifted notation; Sage checked $a_{m,r,j}=\ell_{2r,r+j}^{(m)}(r)$ for every offset in every stored stencil.
2. done -- rewrote the 24 stencil comments as "Accuracy order ...", removing the repeated derivative order and the factor $1$; Sage checked the accuracy order from the first nonzero Taylor term for every stencil.
3. done -- rewrote `formula-accuracy` to state the divided approximation $f^{(m)}(x)\approx h^{-m}\sum_j a_{m,r,j}f(x+jh)$; Sage checked the moments and the first nonzero error term for every stencil.
4/comment-step. done -- replaced the repeated formula with the sentence that the coefficients do not depend on $h$, because $h^m$ is on the derivative side.
4/comment-ordering. declined -- the symmetry is duplicated by `formula-symmetry`, but the comment's ordering sentence is true and useful enough to leave alone.
4/comment-zeroes. done -- dropped the clause assigning $0$ to coefficients outside the defined stencil.
4/Newton-Cotes. declined -- the ASCII hyphen in the caption is harmless, and changing it would add non-ASCII only for typography.
4/comment-neighbours. declined -- it overlaps Similar tables, but it is true prose about the construction and is not a table fault.
4/complete-note. left for a person -- only the builder can say why the range stops at $m=6$, $r=5$.
4/tag. left for a person -- proposing a new corpus tag such as "numerical analysis" is a cross-table decision.
4/program-sage. done -- changed the final bare call to `print(central_difference_coefficients(2, 2))`; running the live post-edit snippet under Sage printed `{-2: -1/12, -1: 4/3, 0: -5/2, 1: 4/3, 2: -1/12}`.

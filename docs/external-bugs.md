# Bugs found in other people's data

Things the corpus work turned up that are wrong *elsewhere* -- in OEIS, in
LMFDB, in a published table, in somebody's software. Kept here rather than
reported one at a time, so a person can send them in a batch, to the right
place, having checked each one again.

Nothing in this file has been reported yet unless its row says so. Nothing in
it should be reported without a person reading the evidence: a claim that
somebody else's data is wrong is worth making only when it is right, and every
entry here was found by an agent run in the course of doing something else.

## How to add one

    ## <source> <identifier>: <what is wrong, in one line>
    Found: which run, which table, what it was doing
    Evidence: how we know -- the independent computation, the source's own
              formula, the published value it contradicts
    Confidence: what would have to be true for us to be the wrong ones
    Reported: no | yes, <when and where>

---

## OEIS A382103 and A382104: the labels are swapped

**Found:** building T132, *Nodes and weights of Gauss-Legendre quadrature*,
on 2026-09-02. Twenty OEIS weight expansions were compared with the computed
weights; eighteen agreed and these two did not.

**Evidence:** A382103's `%N` line says it is the weight corresponding to
A372267, which is the *smallest* positive zero of $P_4$, $0.33998\ldots$; the
sequence holds $0.34785\ldots$. Its own `%F` line gives
$\frac12 - \frac16\sqrt{5/6} = (18-\sqrt{30})/36$, which is the weight at the
*largest* zero, $0.86114\ldots$ -- so the entry contradicts itself, and the
`%F` line is the one that is right. Wikipedia's four-point row, Abramowitz &
Stegun 25.4, and the rule's exactness on $x^2$ all agree with `%F`.
A382104 is the mirror image of the same swap. The eighteen other labels,
including both at $n=5$, are correct.

**Confidence:** high. Two independent published tables and the sequence's own
formula line agree against its name line. For us to be wrong, the standard
four-point Gauss-Legendre rule would have to be wrong.

**Reported:** no.

## DLMF Table 3.5.7: one weight of the 10-point Gauss–Laguerre rule is misrounded in its last digit

**Found:** building the Gauss–Laguerre table (proposal 3 of
`agents/table-ideas/BATCH-2026-09-02.md`) on 2026-09-03. The hundred nodes
and weights of DLMF Tables 3.5.6–3.5.9 ($n=5,10,15,20$) were compared with
the computed balls, each printed value read as its last digit $\pm 1$;
ninety-nine agreed and this one did not.

**Evidence:** DLMF prints the weight at the node $3.40143\,36978\,54899\,51$
of the 10-point rule as $0.62087\,45609\,86777\,475\times 10^{-1}$. The
value in ball arithmetic at 461 bits is
$0.062087456098677747392902\ldots$, and mpmath on another machine, from the
closed form of $L_{10}$ and $w=x/(121\,L_{11}(x)^2)$ at 40 digits, gives
$0.06208745609867774739290213$. Correctly rounded to DLMF's eighteen
significant digits that is $\ldots 777\,474$, not $\ldots 777\,475$: the
printed value exceeds the true one by $1.08$ units in its last place. The
same rule's nine other weights and all ten nodes, and the ninety values of
the other three tables, agree with the balls to the last printed digit.

**Confidence:** high; two computations sharing no code agree to 25 digits
against DLMF's 18, and the rule's exactness on $x^m$ for $m\leq 19$ holds
with the computed weight. A last-digit rounding slip in a table transcribed
from a longer computation is the ordinary way this happens.

**Reported:** no.

## QUADPACK dqk51.f: the central weight of the 51-point Gauss–Kronrod rule is misrounded in its last digit

**Found:** building T136, *Nodes and weights of Gauss–Kronrod quadrature*
(proposal 4 of `agents/table-ideas/BATCH-2026-09-02.md`), on 2026-09-03. The
281 constants of netlib's `dqk15.f` to `dqk61.f` (`xgk`, `wgk`, `wg`, 33
digits each) were compared with the computed balls, each printed value read
as its last digit $\pm 1$; 280 agreed and this one did not.

**Evidence:** `dqk51.f` gives `wgk(26)`, the weight at the central node
$x=0$ of the 51-point rule, as
`0.061580818067832935078759824240066`. That weight is a rational number,
$q_{\omega}(0)/\omega'(0)$ for $\omega=P_{25}E_{26}$, and it was computed
exactly in three independent ways (two in Sage over $\mathbb{Q}$, one in
plain Python with `fractions`): it is
$0.0615808180678329350787598242400645531904\ldots$, so correctly rounded to
33 places the last three digits are `065`, not `066`; the printed value
exceeds the true one by $1.45$ units in its last place. Every other constant
in the six files, the ball at 493 bits, and the rule's exactness on $x^m$ for
$m\leq 77$ with the rational weight all agree.

**Confidence:** high; an exact rational against a printed rounding. For us
to be wrong, the rule's exactness would have to fail with our weight, and
it holds. Harmless in use: the constant is read into a double.

**Reported:** no.

## KnotInfo `determinant` of the unknot `0_1`: listed as 0, the determinant is 1

**Found:** building T140, *Conway polynomials of the prime knots with at
most ten crossings*, on 2026-09-03, comparing the entry comments'
determinants with the `determinant` column of `database_knotinfo`
2026.9.1 (`knotinfo_data_complete.csv`).

**Evidence:** the row for `0_1` has `determinant` = `0`, while its
`alexander_polynomial`, `conway_polynomial` and `jones_polynomial` columns
are `1`; the determinant is $|\Delta(-1)|=|V(-1)|=|\nabla(2i)|=1$, and the
double branched cover of the unknot is $S^3$, whose first homology has
order $1$. The 249 other rows to ten crossings agree with all three
formulas.

**Confidence:** high that the value is not the determinant; it may be a
placeholder for "not computed" rather than an error, since the `arf_invariant`
and `unknotting_number` columns of the same row are empty rather than
`0`. Either way a reader of the CSV who takes the column at its word gets
$0$.

**Reported:** no.

## OEIS A394567: the second `%F` formula does not produce the sequence

**Found:** building T143, *Jacobi sums of pairs of Dirichlet characters
modulo a prime*, on 2026-09-03, while using the sequence as an outside check
on the cubic entries $J(\chi,\chi)=a+b\zeta_3$ through $L=2a-b$.

**Evidence:** the entry's first formula, $a(n)=((c+3)q-1)/27$ with
$q=x^2+xy+7y^2$, $c=2x+y\equiv 1\pmod 3$, gives $1,-1,7$ for $q=7,13,19$,
which are the sequence's terms and which the table's cubic entries
reproduce ($L=c$: $1,-5,7$). Its second formula,
$a(n)=(L^3-3qL+3q-1)/27$ with $4q=L^2+27M^2$, $L\equiv 1\pmod 3$, gives
$0$ for $q=7$ ($L=1$), $4$ for $q=13$ ($L=-5$) and $0$ for $q=19$ ($L=7$),
none of which is a term. The two formulas are stated for the same $a(n)$
with the same $L=2x+y$; the first agrees with the data and the second does
not.

**Confidence:** high that the second formula as printed is not a formula
for $a(n)$; the intended identity is not obvious from it (perhaps a
different quantity of the cubic periods was meant). The b-file and the
first formula are unaffected, and the Lean verification linked from the
entry is of the sequence, not of this line.

**Reported:** no.

## Catalogue of Lattices, LAMBDA13, LAMBDA20, LAMBDA22: the HERMITE_NUMBER lines are wrong in their ninth or tenth digit

**Found:** building the table of packing densities and Hermite numbers of the
classical lattices (proposal 1 of `agents/table-ideas/BATCH-2026-09-03T1730.md`)
on 2026-09-05, comparing every HERMITE_NUMBER line of the catalogue pages
`LAMBDA9.html` to `LAMBDA23.html` and `K12.html` with the value computed from
the page's own DET and MINIMAL_NORM.

**Evidence:** each page prints twelve significant digits. From DET and
MINIMAL_NORM, $\gamma=\mu/\det^{1/n}$ is $4\cdot 1024^{-1/13}=2.34692092001\ldots$
for LAMBDA13, $4\cdot 64^{-1/20}=3.24900958542\ldots$ for LAMBDA20 and
$4\cdot 12^{-1/22}=3.57278019514\ldots$ for LAMBDA22 (arb at 400 bits, and
Python floats to fifteen digits). The pages print `.234692093077E+01`,
`.324900958600E+01` and `.357278019600E+01`: off by $4.6\cdot 10^{-9}$,
$1.8\cdot 10^{-10}$ and $2.4\cdot 10^{-10}$ relative, and the last two end in
`600`, as a nine-digit value padded to twelve would. The other eleven
HERMITE_NUMBER lines and both DENSITY lines agree with the computed values
to all twelve digits, so the DET and MINIMAL_NORM lines those three pages
carry are not in doubt, only the Hermite number printed from them.

**Confidence:** high. The quantity is a formula in two integers the same
page states, and two independent computations of it agree to fifteen
digits.

**Reported:** no.

## Schürmann–Vallentin (2006) Table 1 and Dutour Sikirić–Schürmann–Vallentin (2008) Table 2: the covering density of $A_3^{*}$ is printed as 1.463505; it is 1.4635031

**Found:** building the table of covering radii and covering densities of
the classical lattices (proposal 4 of `BATCH-2026-09-03T1730.md`) on
2026-09-05, comparing $\Theta(A_n^{*})$ with the six-decimal tables of
A. Schürmann and F. Vallentin, *Computational approaches to lattice packing
and covering problems*, Discrete Comput. Geom. 35 (2006), Table 1
(arXiv:math/0403272), and M. Dutour Sikirić, A. Schürmann and F. Vallentin,
*A generalization of Voronoi's reduction theory and its application*, Duke
Math. J. 142 (2008), Table 2 (arXiv:math/0601084, the line `3 A3∗ 1.463505`).

**Evidence:** $\Theta(A_3^{*})$, the covering density of the body-centred
cubic lattice, is $5\sqrt{5}\,\pi/24=1.46350306896\ldots$ (Bambah 1954;
Conway and Sloane, SPLAG Table 2.1, print $1.4635$). It was recomputed
exactly from the Voronoi cell of the adjugate of the $A_3$ Cartan matrix and
of the catalogue's own `A3*` Gram matrix ($R^2=5/16$ at minimal norm $3/4$,
determinant $1/4$, $24$ vertices), and from the stored packing density of
$A_3^{*}$ in T147 through $\Theta=(R/\rho)^3\Delta$. The printed $1.463505$
is $2\cdot 10^{-6}$ above it, beyond any rounding of six decimals. The
eleven other $A_n^{*}$ rows of the 2006 table ($n=2,4,5,10,12,16$ to $21$)
and the four other $A_n^{*}$ rows of the 2008 table agree with the computed
values to all six decimals, so this is a misprint in one row, copied from
the earlier table into the later one.

**Confidence:** high; the closed form is classical and three independent
computations agree with it. `/tmp/cv2_check_out.txt` and
`/tmp/cv2_dsv_out.txt`, 2026-09-05.

**Reported:** no.

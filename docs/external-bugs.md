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

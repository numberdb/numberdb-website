# Lessons proposed by a run, not yet accepted

Stage two appends here when it meets something the skill did not cover. Nothing
in this file is in force. A person reads it, and a lesson that is worth keeping
lands as a diff to `.claude/skills/numberdb-table/SKILL.md` **together with a
test in `numberdb_app/test_skill.py` asserting the sentence that carries it**,
in one commit.

The test is the point. Thirty-six of them assert that specific lessons are
present, so a later rewrite that drops one fails CI rather than passing
quietly. A lesson without a test is a sentence waiting to be edited away.

## What belongs here, and what does not

The skill is published at <https://numberdb.org/skill> and is written for
somebody who has installed Python, and perhaps Sage or passagemath, and wants
to contribute a table. That is the only reader.

So a lesson belongs here **only if it would still be true for that person on
their own machine**. The mathematics of checking a value, what the API does,
what the client returns, how the corpus search behaves, what a Sage import
does or does not bring with it: all of that is theirs as much as ours.

Everything about *this* deployment goes to `docs/agent-environment.md`
instead -- the containers, the ssh, the proxy, `agents/sage.sh`, the runner's
permissions, a bug in the site that has since been fixed. None of it is true
for the reader of the skill, and a skill that carries it teaches somebody
else's setup.

The test: could a contributor with a laptop and Sage hit this? If not, it is
an environment note, not a lesson.

## Format

    ## <short title>
    What happened: ...
    What the skill says now: ... (or "nothing")
    What it should say: ...
    Evidence: the command, the output, the table

---

## Search OEIS for a polynomial family too: it holds coefficient triangles

What happened: the proposal for the Hilbert class polynomials had screened
Wikipedia, MathWorld and the LMFDB and found no page of that name, and said
so. Nobody searched OEIS, because the family is polynomials rather than
integers. OEIS **A305474** is the irregular triangle of coefficients of
$H_D(x)$ for $D = -3, -4, -7, -8, \dots$, with a b-file to $D = -500$ -- an
independent copy of every coefficient the table holds, computed by somebody
else with PARI in 2018, and it settled the "all discriminants or only
fundamental ones" question by enumerating the family the same way. The
build compared all 250 rows; they agree.

What the skill says now: "Check new values against something independent";
OEIS is named as a link target, not as a place to look for a polynomial
family.

What it should say: a family of polynomials with integer coefficients is
usually in OEIS as a triangle (`tabl` or `tabf`), read row by row. Search it
by the family's name before writing the checks: it is the cheapest
independent source there is, and its b-file is worth more than any identity
because it shares no code and no author with the generator. The T108 link to
A011973 is the same thing for the Fibonacci polynomials.

Evidence: `https://oeis.org/search?q=hilbert+class+polynomial` returns
A305474 first; `/tmp/hcp_check.py`, "OEIS rows compared: 250 ... disagreements:
[]", 2026-09-01.

## `verify()` on a draft needs the key, though it says it needs none

What happened: after filling draft T129, `generator.verify(sample=None)`
raised `NumberDBError: Table with id 'T129' does not exist.` The table
existed and had 150 entries; a draft is served by `api/table` only to a
request carrying its author's key, and `verify()` -- documented as "writes
nothing, and needs no key: reading is public" -- had no key, so it was
answered as an outsider. With `numberdb.configure(api_key=...)` first (or
`NUMBERDB_API_KEY` set) it reported 150/150 matched.

What the skill says now: "`verify()` recomputes and compares against the
stored table. Needs no key, writes nothing." True for a published table.

What it should say: reading a draft is not public, so for a draft `verify()`
needs the same key that filled it. The refusal reads as if the table were
missing, which after a successful `publish()` a moment earlier is confusing;
the client could say "no table, or a draft this key may not see".

Evidence: `/tmp/verify_stored.py`, 2026-09-01, without and with the key.

## A `ComplexBall` has no `is_finite()`; its two real parts do

What happened: the generator's rigour check refused a coefficient ball that
was not finite, following the skill's rule that a nan ball agrees with
everything. Written as `ball.is_finite()` on the coefficients of a polynomial
over `ComplexBallField`, it raised `AttributeError: 'ComplexBall' object has
no attribute 'is_finite'`. `RealBall` has it; `ComplexBall` does not, so the
check is `ball.real().is_finite() and ball.imag().is_finite()`.

What the skill says now: "check that both sides are finite" -- in the
polygamma example, where the balls are real.

What it should say: the same sentence, plus: on a complex ball ask the real
and imaginary parts. And a related trap from the same check: `float(ball.rad())`
underflows to `0.0` once the radius is below about $10^{-308}$, which at
1500 bits it is, so a printed "worst radius 0" is not evidence of anything;
compare the radius as a ball or print `rad().log2()`, and run the same
check at 400 bits, where the radius is visible, as the control.

Evidence: the dry run of `generators/hilbert-class-polynomials/generate.py`,
2026-09-01, and "worst radius 0" in `/tmp/hcp_check.py` at 1500 bits against
`5.9e-105` at 400.

## `numberdb.sage` searches ignore `configure(api_key=...)`, and a key-less loop of lookups is throttled

What happened: the build of T130 looked up every short entry with
`numberdb.search_rational(...)` to find the values that identify nothing.
After about sixty lookups every call raised `RateLimitError: too many
requests; retry in 1307s. Anonymous use is limited -- an API key raises the
limit`. The first loop had no key, which was the run's fault. The second run
called `numberdb.configure(api_key=...)` first, read the draft with the key,
and was throttled as *anonymous* again. The cause is in the client:
`numberdb.sage` makes its own `_sage_client = Client(as_sage=True)` when it
is imported (`sage.py:102`), and every `search_*` wrapper in that module goes
through it via `_flavoured`, so `configure()` never reaches a search made
through `numberdb.sage`, while `numberdb.sage.table()` -- imported straight
from the package -- does see the key. A key in `NUMBERDB_API_KEY` works for
both, because `Client` looks the environment up lazily.

What the skill says now: "Check the shortest and the most common-looking
entries in your range before you fill, with `numberdb.search_number` or
`/api/lookup`"; nothing about the limit, and `search_number` is not a
function the client has.

What it should say: set `NUMBERDB_API_KEY` in the environment before a loop
of lookups, rather than calling `configure()`, until `_flavoured` in
`numberdb/sage.py` falls back to `numberdb._default_client`; and expect
about sixty anonymous lookups in a window before a refusal that lasts for
the rest of it. Name the function that exists: `search_rational`,
`search_integer`, `search_real_interval`.

Evidence: `/tmp/zk_check.py` (no key) and `/tmp/write_doc_t130.py` (key
via `configure`), 2026-09-01; the traceback ends in `_http.py:160
RateLimitError`, and `sage.py:113-115` shows the client it used.

## OEIS may hold a family under a transform: search for the mirrored values too

What happened: nothing in OEIS is indexed as $\zeta_K(-1)$ by discriminant,
and the searches for `1/30, 1/12, 1/6, 1/6, 1/3` and for `zeta real quadratic
negative` found nothing. **A370412 / A370411** hold the numerators and
denominators of $\zeta_K(2n)\sqrt{D}/\pi^{4n}$, read by antidiagonals over
$n$ and the real fundamental discriminants -- the same numbers as the
table's, carried across the functional equation, and computed by somebody
else with a different method (Hurwitz zeta sums). Their `%e` array gave 35
values to compare against, on top of the 29 b-file terms; all agreed.

What the skill says now: OEIS is a link target; the previous lesson says to
search it for a polynomial family's coefficient triangle.

What it should say: when a family has a functional equation or a standard
normalisation (a power of $\pi$, a $\sqrt{D}$, a factorial), search OEIS for
the values on the other side of it too. Searching by the family's name found
nothing; searching for `Dedekind zeta real quadratic` found the mirror.

Evidence: `curl 'https://oeis.org/search?q=Dedekind+zeta+real+quadratic+-1&fmt=text'`,
2026-09-01, first result A370411; `/tmp/zk_check.py`: "OEIS A370412 example
array, 35 numerators (n <= 6, D <= 17): mismatches []".

## A program offered under `Programs` is a claim; run it before writing it down

What happened: the PARI line first written for T130 was
`bestappr(lfun(lfuncreate(x^2 - 5), -1))`. It returns `1/30`, and at
`D = 12, s = -5` the same line returns a 42-digit fraction, because
`bestappr` with no bound recovers the floating error along with the
rational. With a denominator bound, `bestappr(..., 10^6)`, it returns
`1681/126`, and every entry of the table. The Sage line
(`kronecker_character(D).bernoulli(2*m)`) was right first time, but only
because it was run too.

What the skill says now: `Programs` is "the standard incantation ... for a
reader who wants one more value"; nothing says to run it.

What it should say: run every program in `Programs` on at least one entry
that is not the first, and put its output in the comment beside it. The
first entry of a table is the one a wrong program is most likely to get
right.

Evidence: `/tmp/dry.py` output, 2026-09-01: `pari program at D = 12: [1/6,
23/60, 491632182461319060852853197906891343109535/36850478875744319849767699545668238686378]`;
`/tmp/pari_prog.py` with the bound: `12 [1/6, 23/60, 1681/126]`.

## A generator of a unit group is any of four numbers; normalise it in the program line

What happened: the Sage line first offered under `Programs` for T131 was
`log(abs(RealField(400)(eps)))` with `eps = K.units(proof=True)[0]`. Run at
$D = 61$, as the lesson above asks, it printed $-3.664\ldots$: Sage's
generator was $1/\varepsilon_K$, and the line had allowed for the sign but
not for the inverse. A rank-one unit group is generated by any of
$\pm\varepsilon^{\pm 1}$ and `units()` picks none of them in particular --
the table's own generator tries all four and keeps the one that exceeds 1.
The fixed line is `abs(log(abs(RealField(400)(eps))))`.

What the skill says now: run every program in `Programs` on an entry that is
not the first. That is what caught it.

What it should say: the same, with this as the second example of why: a
program that reproduces the value up to sign, inverse or conjugate reads
as correct until it is run, and a unit, a root, or an eigenvalue is exactly
the kind of value that has such a twin.

Evidence: `/tmp/reg_identities.py`, 2026-09-02: `Sage program at D = 61:
-3.66421846088643752592...`; `/tmp/reg_programs.py` after the fix:
`3.66421846088643752592...`, the table's value.

## Compare a higher-precision rerun by rounding it back, not by taking its prefix

What happened: the T166 repair reran $C(x^2+1)$ at 160 decimal digits to
check that it gave the stored 100 digits. Comparing the first 100 significant
digits of the 160-digit string to the stored 100-digit string reported a
failure in the last place: the stored value was rounded by the table's
formatter, while the prefix of a higher-precision decimal is truncated.
Rounding the 160-digit value back through the same 100-significant-digit
formatter matched the stored value, and the same check passed for
$C(x^2+x+41)$.

What the skill says now: real numbers are stored as decimal intervals, and
`verify()` compares them correctly, but it does not say how to hand-check a
higher-precision rerun against a stored rounded decimal.

What it should say: when checking that a higher-precision recomputation
supports an already stored real decimal, compare after rounding the
higher-precision value to the stored precision with the same output convention;
do not compare a raw prefix, because the final stored digit may have been
rounded up.

Evidence: `/tmp/t166_examples_160.py`, 2026-09-09, first failed by prefix
comparison on $C(x^2+1)$ and then passed after formatting the 160-digit value
back to 100 significant digits.

## For a number field family, OEIS holds the unit exactly and the LMFDB API does not answer

What happened: the proposal named LMFDB field pages as the outside check for
every regulator. `https://www.lmfdb.org/api/nf_fields/?degree=2&...` answers
"Page Not Found", and `beta.lmfdb.org/api/` redirects to a captcha gate, so
there is no scripted way to fetch 302 regulators; a field page such as
`NumberField/2.2.61.1` shows eleven digits, and fetching eight of them by hand
was the practical limit. What checked every entry exactly was OEIS: A014000
and A014046 are the coordinates of the fundamental unit of the real quadratic
field of discriminant A003658(n), taken from Cohen's tables, with b-files to
$D = 32901$, and A014077 is its norm. A unit compared coordinate by
coordinate is a stronger check than eleven digits of its logarithm. Two
details: the b-file URL `oeis.org/A014000/b014000.txt` redirects to S3, so
`curl` needs `-L` or the file is a two-line HTML stub; and the coordinates
are over the integral basis $(1, \omega)$ with $\omega = (1+\sqrt{D})/2$ or
$\sqrt{D}/2$, which the `%C` line states and which has to be converted before
comparing.

What the skill says now: "Check new values against something independent";
the lessons above say to search OEIS for polynomial triangles and for values
across a functional equation.

What it should say: for a family of number-field invariants, look in OEIS for
the exact object underneath the real number -- the unit under the regulator,
the class group under the class number -- indexed by the discriminant
sequence A003658 or A003657; and do not plan a check on the LMFDB API
without first fetching one URL from it.

Evidence: `/tmp/reg_check.py`, 2026-09-02: `OEIS compared {'y': 302, 'x':
302, 'norm': 82} disagreements []`; `curl` of the three LMFDB API URLs, each
an HTML "Page Not Found" or a 302 to `gate.html`.

## Check what the entry comments claim, from the values read back

What happened: T131's comments carry $\varepsilon_K$ and its norm, and a
reader will use them -- to recover $h_K^+$, or to check the value by hand.
`verify()` compares the stored entry with the generator's and so cannot say
whether the comment is *true*. The read-back check parsed
$\varepsilon_K=(a+b\sqrt{d})/2$ and $N(\varepsilon_K)$ out of each stored
comment, required $a^2-db^2=4N$, and recomputed the stored value from the
comment alone as $\operatorname{arcosh}(a/2)$ or $\operatorname{arsinh}(a/2)$;
all 302 agreed and the controls failed. Had a comment carried the wrong unit
next to the right logarithm, nothing else would have noticed.

What the skill says now: check identities on the values read back, because
`verify()` cannot catch a generator wrong the same way twice.

What it should say: the same, and that a comment which states a fact about
its entry is a claim to check the same way -- parse it back out of the
stored table and test it against the stored value, rather than trusting
that the generator wrote what it computed.

Evidence: `/tmp/reg_stored.py`, 2026-09-02, "stored values checked: 302".

## Walking the corpus by T-number is more lookups than an anonymous hour allows

What happened: the skill says "there is no call that lists the corpus, so to
see everything you walk the T-numbers", and the stage-one prompt asks for
exactly that. The walk died at T60 with `RateLimitError`: the anonymous
limit is 60 requests per 60 minutes per address, and `numberdb.table()`
counts against it like every other call. The corpus has 131 tables. The
same hour's budget is shared with `curl .../api/lookup` from the same
machine, so a walk that runs out of it also stops every later lookup for
the rest of the hour -- the sign test this run wanted afterwards was
refused with `retry_after: 2665`.

What the skill says now: walk the T-numbers; the earlier lesson here says
sixty anonymous `search_*` calls are throttled and to set
`NUMBERDB_API_KEY` first.

What it should say: the walk is the first thing a contributor does and it
is already over the anonymous limit, so say at that sentence that it needs
the key in the environment -- with it the remaining 71 tables listed in
one go -- and that the limit is per address and shared with `curl`.

Evidence: `/tmp/list_corpus.py`, 2026-09-02: `T60 -- RateLimitError`
through `T139`; rerun with the key from T60, all listed; `api/lookup`
answering `{'error': 'Rate limit exceeded (60 requests per 60 minutes)...',
'retry_after': 2665}` forty minutes later.

## Search OEIS by the digits of a small member; the family's name finds nothing

What happened: `oeis.org/search?q=Gauss-Legendre` returned sums of squares
and pentagonal numbers; `q=Gauss-Kronrod`, `q=Lobatto` and `q=secondary
polynomials` returned nothing useful. The digits of one node,
`q=0.3399810435848562`, returned **A372267**, "smallest positive zero of
the Legendre polynomial of degree 4", and from its neighbours the whole
block: A372267-A372276 (zeros of $P_4$ to $P_7$), A382103-A382107 and
A382686-A382690 (the Gauss-Legendre weights), A393353-A393374 (Hermite
zeros and weights, $n = 4$ to $7$), A384277-A384281, A384586-A384589 and
A384463-A384467 (Laguerre, $n = 3, 4$), each with a b-file of 10000 digits
and the defining algebraic equation in `%F`. Entries from 2024-2025,
computed by other people from A&S Table 25.4. A 45-digit comparison of the
largest zero of $P_7$ and the smallest positive zero of $P_4$ agreed.

What the skill says now: OEIS is a link target; the lessons above say to
search it for a polynomial triangle and for values across a functional
equation.

What it should say: for a family of real constants indexed by a small
integer, OEIS may hold each member as its own decimal expansion, and the
name search will not find them because the `%N` line names the polynomial
and the index, not the family. Search by the first fifteen digits of the
smallest interesting member (not the first: $1/\sqrt 3$ is in a dozen
entries), and then read the entries adjacent in number, which is how a
block submitted together is arranged.

Evidence: the searches above, 2026-09-02; `/tmp/gq_out.txt` lines 40 and
57 against `b372276.txt` and `b372267.txt`.

## `roots(ring=RIF)` returns a ball around an exact rational root, and the table wants the exact value

What happened: the Gauss-Legendre rule of odd order has the node $x = 0$,
and the Lobatto rule has $\pm 1$. Isolated with
`p.roots(ring=RealIntervalField(400))` they came back as intervals of
radius $3 \cdot 10^{-140}$ around $0$ and $1.4 \cdot 10^{-120}$ around
$\pm 1$ -- correct enclosures, and written to a table at 100 digits they
would read `0.000...0` and `1.000...0`. The corpus writes such an entry as
the exact `0` or `1` (T22's $x = 0$ for $\alpha = 0$; T61's `1` with
`equals: HREF{One}`), and the same goes for a weight that is rational: the
central Gauss-Legendre weight of odd order ($8/9$, $128/225$) and every
Lobatto endpoint weight $2/(n(n-1))$.

What the skill says now: return exact values exactly rather than as a
hundred digits of an integer; nothing about a root isolator handing back an
enclosure of one.

What it should say: before isolating, take the rational roots off with
`p.roots(QQ)` and return them as exact values, and for a derived quantity
test whether it is rational (a weight at a rational node of a rational
polynomial is) before returning a ball. An enclosure of an exact number is
not wrong, but it is a hundred digits saying less than one character.

Evidence: `/tmp/gq_out.txt`, 2026-09-02: "n=7 zero node ball: mid
7.2198e-141 rad 2.6e-140"; "endpoint node radius 1.4e-120" for every
Lobatto order.

## Search by number is sign-sensitive, so a symmetric family must store both signs

What happened: deciding whether a table of Gauss nodes could store only
the nonnegative half, the run searched for T127's entry
$-0.50408300826445540\ldots$ both ways. `search_real_interval` with the
positive digits returned `[]`; with the minus sign it returned the T127
entry. (`search_text` with digits returns nothing either way: it searches
words, and the lesson above names the functions that search numbers.)

What the skill says now: nothing about sign; "include what is common, and
stop" would tempt a builder to halve a symmetric table.

What it should say: a reader who has $-0.7745966692$ types the minus sign,
and a table holding only $0.7745966692$ does not answer. A family with a
symmetry $x \mapsto -x$ stores both halves and states the symmetry in
Formulas; the digits are the same but the entries are not.

Evidence: `/tmp/gq_20260902_sign.py`, 2026-09-02: `interval +: []`,
`interval -: [Result('-0.5040830082644554...', table='Zeros of the
polygamma functions')]`.

## An OEIS name can be wrong: read the entry's own formula before trusting its label

What happened: the Gauss-Legendre weights were compared with OEIS
A382103-A382107 and A382686-A382690 by their `%N` lines, "weight factor
... corresponding to abscissa A37226x". Two of twenty failed, both at
$n = 4$. A382103 says it corresponds to A372267, the smallest positive
zero $0.33998\ldots$ of $P_4$, and holds $0.34785\ldots$; its own `%F`
line, $1/2 - \frac16\sqrt{5/6} = (18 - \sqrt{30})/36$, is the weight at the
*largest* zero $0.86114\ldots$, as Wikipedia's table, A&S 25.4 and the
rule's exactness on $x^2$ all say. A382104 is the mirror. The eighteen
other labels, including both at $n = 5$, are right. The value was compared
where it belongs, the label as written became the control, and the table's
link says which way round the two entries are.

What the skill says now: a b-file "shares no code and no author with the
generator", and the lesson above says to search OEIS by digits.

What it should say: the digits of a b-file are independent evidence; the
`%N` line is one person's sentence about them. Before comparing by label,
check that the entry's `%F` formula and its `%N` describe the same thing,
and when a labelled value disagrees with the table, look at the neighbouring
entry before suspecting the table -- two failures that are each other's
values is a swapped label, not a wrong rule. Worth a note to OEIS from the
person who publishes.

Evidence: `/tmp/gl_check_out.txt`, 2026-09-02, first run: `FAIL OEIS
A382103 weight n=4 k=3`, `FAIL OEIS A382104 weight n=4 k=4`, everything else
passing; `oeis.org/search?q=id:A382103&fmt=text`, the `%N` and `%F` lines.

## A `Symbolic` parameter holds nodes and weights in one table, and a value can be added to it later

What happened: the proposal asked for T15's shape -- parameters `n`, `k`
and `expression`, the last of type `Symbolic` with `values: {x: $x_k$,
w: $w_k$}` and `show-in-parameter-list: 'no'` -- and the skill does not
mention the type. It is enumerated like any parameter
(`{'n': n, 'k': k, 'expression': 'x'}`), the identity is `n,k,x`, and the
site shows it as the choice of column. The proposal left open whether to
add `c` and `b`, the rule on $[0,1]$, as two more values for small $n$; the
run left them out, because adding a value to a `Symbolic` parameter later
adds entries without touching the parameter order, whereas a table with
four columns for $n \leq 10$ and two beyond is a rectangle with a hole.

What the skill says now: the types listed are those of *values*; parameters
are described only as `Z`, `Q`, with `constraints`.

What it should say: a parameter may be `Symbolic`, with a `values` mapping
from key to display, for a family that has more than one quantity per
index; that its values are extensible without changing identities; and
that a symmetric or two-quantity table should be built complete in the
values it has rather than partial in more.

Evidence: T15 and T132's `Parameters` as `numberdb.table()` returns them;
`generators/gauss-legendre-quadrature/table.yaml`.

## The Definition names the object; the first `HREF` goes in the first comment

What happened: following "link the first mention of a thing to what
explains it", the Definition of T132 said "the roots of the
HREF{Legendre_polynomials}[Legendre polynomial] $P_n$". `audit_table`
answered "Definition links to another table; a cross-reference belongs in
Similar tables or a comment", and that the Definition was 379 characters
against a median of 195. The link moved into the first comment, which says
what $P_n$ is, and the Definition shrank to the rule and what is listed.

What the skill says now: "Link the first mention of a thing to what
explains it. A table if the corpus holds one ... first mention, once per
section"; and that a Definition is "one or two sentences saying what the
object *is*".

What it should say: the two rules meet in the Definition, and the audit
decides it: the Definition cites (`CITE{}`) and does not link (`HREF{}`);
the first `HREF` to a table belongs in the first comment that names the
thing, and the table also goes in Similar tables.

Evidence: `audit_table T132`, 2026-09-02, two findings, none after the edit.

## An entry's address joins its parameters by commas in identity order; take it from a search hit

What happened: the `equals` links for $\pm 1/\sqrt 3$ and $\pm\sqrt{3/5}$
needed the addresses of entries of T35, whose `Parameters` come back from
`numberdb.table('T35')` in the order `n, a0, a1, a2` and whose `Numbers`
nest as `a2, a1, a0` then `n`; neither says which is the identity. A search
hit does: `numberdb.search_real_interval(lo, hi)[0].url()` -- `url` is a
method on a `Result`, not an attribute -- printed
`.../Algebraic_numbers_of_degree_2?entry=3%2C0%2C-1%2C2#3,0,-1,2`, so the
link is `HREF{Algebraic_numbers_of_degree_2#3,0,-1,2}`. The read-back check
then opened each linked entry and required it to hold the same number.

What the skill says now: read a slug off `search_text(...).tables[0].url`;
nothing about the address of one entry.

What it should say: an entry's anchor is the parameters joined by commas in
identity order, which is the nesting order of `Numbers` and not the order
of `Parameters`; the safe way to get one is `Result.url()` of a search for
the value, and an `equals` link is a claim to check on read-back like any
comment.

Evidence: `/tmp/gl_check_out.txt`, 2026-09-02, the four `T35 address for`
lines; `/tmp/gl_stored.py`: `equals links checked: 22`.

## The Legendre function of the second kind lives on the complex balls, and so does rigorous integration

What happened: the check for T133 wanted arb's $Q_n$ to compare
$\frac12P_n(x)\ln\frac{1+x}{1-x}-\frac12q_n(x)$ against, and the skill's
list of what arb implements suggested `RealBall` would have it.
`RealBall` has no `legendre_Q`; `ComplexBall.legendre_Q(n, m, type)` exists
(type 2 for the Ferrers function on $(-1,1)$, type 3 outside), and the real
part is taken after checking that the imaginary part contains zero. The same
for integration: `RealBallField` has no `integral`;
`ComplexBallField.integral(f, a, b)` is the rigorous one, and its integrand
takes `(z, analytic)` and must pass `analytic` on to `log`, `sqrt` and
`pow`, or a box meeting a branch cut is enclosed rather than reported. All
80 comparisons and 600 orthogonality pairings then passed.

What the skill says now: "arb implements a great deal (`elliptic_k`, ...,
`zeta`, ...)", with the real ball field in mind.

What it should say: some of arb's special functions and its integrator are
reached only through `ComplexBallField`; when a `RealBall` lacks a method,
try the complex ball, check `imag().contains_zero()`, and take `.real()`.

Evidence: `/tmp/sp_check_out.txt`, 2026-09-02, first run
`'sage.rings.real_arb.RealBall' object has no attribute 'legendre_Q'`;
`/tmp/sp_orth_out.txt`, `'RealBallField_with_category' object has no
attribute 'integral'`; both passing after the change.

## Two more parts of Sage that named imports do not bring: power series and a rational's log

What happened: the Padé check built the series of $\operatorname{artanh}$
with `PowerSeriesRing(QQ, 't')`. Coercing a list into it went through the
lazy-series machinery into `sage.functions`, then `sage.symbolic`, and died
with "cannot access submodule 'function' of module 'sage.symbolic'
(most likely due to a circular import)". A truncated polynomial in
`PolynomialRing(QQ, 't')`, cut at the order wanted after each product, is
the same computation. Separately, `QQ(x).log()` for a tail bound reached
`sage.functions.log` and failed the same way; `CBF(x).log()` does not.

What the skill says now: "Expect the machinery to be missing ... power
series `.log()` and `.inverse()`, `matrix(...).determinant()`, and
`SymmetricFunctions(...).expand()` all reach for parts of Sage that are not
initialised."

What it should say: add `PowerSeriesRing` itself (not only its `.log()`)
and `Rational.log()` / `Integer.log()` to that list; write a series as a
truncated polynomial and take every logarithm in a ball field.

Evidence: `/tmp/sp_check_out.txt` and `/tmp/sp_orth_out.txt`, 2026-09-02,
the two tracebacks ending in `sage/symbolic/expression.pyx`.

## An integrand singular at the endpoint makes arb answer nan; cut the ends off and bound the tails

What happened: the orthogonality of the $q_n$ for the secondary measure
$du/(\pi^2+\ln^2\frac{1+u}{1-u})$ was checked with `CBF.integral` over
$[-1,1]$ and every pairing came back `nan` in 0.2 seconds -- including the
control $\langle q_1,q_1\rangle$, which is how it was noticed at once: the
integrator evaluates at the ends, where $(1+u)/(1-u)$ is $0$ or a division
by a ball containing zero, and a nan anywhere is a nan everywhere. Integrating
over $[-1+\varepsilon, 1-\varepsilon]$ and adding a hand bound for the two
tails ($\varepsilon$ times the largest the integrand can be there, which
$\ln^2$ makes small) gave enclosures of radius $10^{-18}$ at low degree.
The second trap was the pass criterion: "contains zero and radius below
$10^{-12}$" reported 21 failures at degrees above 40, every one a ball of
radius $10^{-11}$ to $10^{-8}$ around zero, because the polynomials' large
coefficients cancel in the evaluation and the enclosure widens with the
degree. Against norms $\int q_n^2\,d\mu = 2/(2n+1) \geq 0.0198$ those radii
are seven orders of magnitude below the value a non-orthogonal pair would
have; the criterion was wrong, not the claim.

What the skill says now: run the control first; an enclosure that contains
everything agrees with everything.

What it should say: the same, plus: a `nan` from a rigorous integrator
usually means an endpoint, and a tolerance for "encloses zero" must be set
relative to the size of the quantity that would appear if the claim were
false -- the norms, here -- not to a fixed number of digits, or a passing
check reads as a failing one at high degree.

Evidence: `/tmp/sp_orth_out.txt`, 2026-09-02, `control <q_1,q_1> = nan`
before the change and `[0.6666666667 +/- 5.56e-11]` after;
`/tmp/sp_orth2_out.txt`, 600 pairs and 50 norms, 21 "FAIL" lines all of the
form `[+/- 9.7e-12]`.

## A dry-run length warning is a threshold, and a companion table can be the reason to cross it

What happened: `dry_run.py` reported "longest 1365 characters at n=50 ...
TOO LONG: the tables here stop around 1100 to 1300 characters". The table of
Legendre polynomials, which these are the secondary polynomials of, stops at
$n=50$ with $P_{50}$ at 1302 characters; $q_{50}$ has the same number of
terms with slightly larger numerators. Stopping at $n=49$ to satisfy the
number would have left the one table one entry short of the other. The range
was kept at 50, the block is 28 KB, and the decision is written in the
generator and reported for the reviewer.

What the skill says now: "measure the largest entry before choosing the
range"; the dry run prints its threshold.

What it should say: when a table is built entry by entry alongside another
(the same index, the same range), matching that range is a reason a person
would accept, and the warning is for a range chosen without one. Say so in
the report rather than trimming silently.

Evidence: `/tmp/sp_dry_out.txt`, 2026-09-02; `P_50 as written: 1302 chars`
in `/tmp/sp_check_out.txt`.

## An OEIS b-file of a constant below $1/10$ begins with its leading zeros

What happened: the Gauss-Hermite weights were compared with the b-files of
OEIS A393353-A393374 at 100 digits, and five of twenty-five failed -- every
weight below $0.1$ and nothing else. A393356 is $0.0813128\ldots$ and its
b-file reads `0 0`, `1 8`, `2 1`, `3 3`: the offset-zero term is the digit
before the decimal point, which is $0$. The check had taken the first hundred
terms as a hundred significant digits and placed them by the value's own
magnitude, so its mantissa was a digit short and the box it built was ten
times too narrow -- a check failing on its own arithmetic, in the pattern of
"all the small ones fail" that says the checker and not the table. Stripping
the leading zeros before counting, and letting the value's magnitude fix the
power of ten, passed all twenty-five; a control shifted by $10^{-50}$ fails.

What the skill says now: search OEIS by digits; the digits of a b-file are
independent evidence.

What it should say: a decimal-expansion b-file lists digits from the units
place, so a constant in $(0, 1/10)$ starts with one or more zeros that are
not significant. Compare significant digits, and let the magnitude of the
value being checked (not the term count) place the decimal point; then a
misplaced point fails as loudly as a wrong digit.

Evidence: `/tmp/he_check_out.txt`, 2026-09-02, first run: `FAIL OEIS
A393356 vs n=4 k=4 w` and four more, all weights below $0.1$; second run
`OEIS expansions compared to 100 digits: 25`, no failures.

## DLMF's tables are MathML: the numbers are in `alttext`, an exponent is its own cell, and only half the nodes are there

What happened: DLMF Tables 3.5.10-3.5.13 hold the Gauss-Hermite nodes and
weights for $n = 5, 10, 15, 20$ to about twenty digits, the only published
check at $n > 7$. Fetched, the page is one HTML document for all of §3.5
(`dlmf.nist.gov/3.5.T10` serves the whole section), the cells are MathML
with the number in the `alttext` attribute as `0.95857\;24646\;13819` (or
with U+2004 thin spaces), a weight like $1.99532\times 10^{-2}$ is written
as a mantissa cell followed by a `\times 10^{-2}` cell, and only the
nonnegative nodes are listed. Two other traps: searching the captions for
"the 5-point Gauss" finds the Gauss-Legendre table (3.5.1) first -- name the
formula, "5-point Gauss–Hermite formula" -- and the 15-point table's first
match on "Nodes and weights for the 15-point" is the Gauss-Laguerre one.
Parsed that way, all 52 DLMF values agreed with the run's balls.

What the skill says now: DLMF is a link target; nothing about reading a
table from it.

What it should say: a DLMF table is a usable independent check at orders
OEIS does not reach, and the way to read one is the `alttext` of each cell,
folding a following `\times 10^{k}` cell into the number before it, matching
each listed node to the nearest computed one rather than by index, because
the table lists one sign only.

Evidence: `/tmp/he_dlmf_values.txt` and `/tmp/he_check_out.txt`, 2026-09-02:
`DLMF table values compared: 52`.

## A printed table can be off by one in its last digit; read it as $\pm 1$ ulp and record the slip, do not widen the box

What happened: the hundred nodes and weights of DLMF Tables 3.5.6–3.5.9
(Gauss–Laguerre, $n = 5, 10, 15, 20$) were compared with the computed
balls, each printed value read as the interval its last digit denotes.
Ninety-nine agreed; the weight at the node $3.4014\ldots$ of the 10-point
rule did not. The ball ($0.062087456098677747392\ldots$) and an mpmath
computation on another machine from the closed form of $L_{10}$ agree to 25
digits, and DLMF's eighteen-digit value $0.620874560986777475\times10^{-1}$
is the true value rounded up where it should have been rounded down: off by
$1.08$ units in its last place. The check now passes a value that is within
one further unit and prints it as "off by one in its last digit", fails
anything beyond, and the slip went to `docs/external-bugs.md`.

What the skill says now: check against something independent; "if your
recomputation disagrees with a stored value, suspect your recomputation
first"; the lesson above on DLMF's `alttext` cells.

What it should say: a printed table is a rounding of somebody's longer
computation, and one value in a hundred being misrounded in its last place
is ordinary. When exactly one printed value fails by about one unit, compute
it a third way before believing either side; then keep the $\pm 1$ ulp
criterion for everything else, so that a wrong digit still fails as loudly
as it should, and write the slip down where a person can report it.

Evidence: `/tmp/la_check_out.txt`, 2026-09-03: `DLMF table values compared:
100 of which off by one in the last digit: 1`; the mpmath value
`0.06208745609867774739290213`.

## A pattern "true for every small case" belongs in the generator as a check, where it can fail

What happened: the Gauss–Laguerre weights of every rule with $n\leq 6$
decrease from $w_1$ to $w_n$, as $e^{-x}$ suggests they should, and the
first draft of the generator asserted it for every $n$ so that entry
comments could call a weight "the largest root" of its minimal polynomial.
The assertion failed at $n = 7$, where $w_2 = 0.4218\ldots$ exceeds
$w_1 = 0.4093\ldots$; from $n = 24$ the largest weight is $w_3$. Had the
sentence been written into a comment without the check, the table would
have stated something its own rows for $n\geq 7$ refute -- which is the
T132 finding, "a comment claims degrees the table's own central rows
refute", in a new family. The check stayed, scoped to the four rules whose
comments rely on it, and the fact became a comment of its own.

What the skill says now: verify a claim before writing it into a table,
with the orthogonality example; the T131 lesson above says a comment is a
claim to test on read-back.

What it should say: the same, and where to put the test: a claim about
every entry is cheapest to state as a check inside the generator, next to
the exactness and symmetry checks, because there it fails before a table
exists and names the first $n$ that breaks it. A property observed on the
small cases is exactly the kind that fails at $n = 7$.

Evidence: the first dry run of `generators/gauss-laguerre-quadrature/
generate.py`, 2026-09-03: `ArithmeticError: n=7: the weights do not decrease
with k`; `/tmp/la_check_out.txt`, the lines `n=7: weights not decreasing;
the largest weight is w_2` through `n=30 ... w_3`.

## A control that vanishes by symmetry is not a control

What happened: the Stieltjes polynomial $E_{n+1}$ is defined by
$\int P_nE_{n+1}x^j\,dx=0$ for $j\leq n$, and the check's control was that
the same integral is *not* zero at $j=n+1$. It reported a failure at every
odd $n$ and none at even $n$ -- the parity signature the 2026-09-02 batch
had already met in the degree-of-exactness check. For odd $n$ the integrand
$P_nE_{n+1}x^{n+1}$ is odd, so the integral is zero by symmetry, whatever
$E_{n+1}$ is: the control "failed" for a reason that had nothing to do with
the claim. The right control is the first monomial beyond $n$ whose product
with $P_nE_{n+1}$ is even, $x^{n+1}$ for even $n$ and $x^{n+2}$ for odd
$n$; with that, every order passes and the polynomials agree with a second
linear system solved by Sage's own `solve_right`.

What the skill says now: "A measurement needs a control that returns a
known answer"; run the control first.

What it should say: the same, plus: before trusting a control, say why the
quantity it measures is nonzero when the claim is false. In a family with a
symmetry $x\mapsto -x$ half of the monomial controls are zero by parity and
a checker that picks one reads as a wrong table, always on exactly the odd
or exactly the even orders -- which is the signature to recognise.

Evidence: `/tmp/gk_check_out.txt`, 2026-09-03, first run: `FAIL n=1:
control: P_n E orthogonal to x^(n+1) too` through `n=29`, every odd $n$ and
no even one; second run after the parity fix, `FAILURES: 0`.

## A table of type `R` may hold exact entries; a reader of stored values must accept both forms

What happened: the read-back check compared the embedded Gauss nodes and
weights of the draft with the stored entries of T132. Its parser of a
written real took a decimal string and died on `5/9`, the exactly written
weight of T132's three-point rule (`ValueError: invalid literal for int()`).
The corpus writes a value that is rational exactly even in an `R` table --
the central node `0`, the central weights, whole small rules -- and the
skill says to do so; so anything that reads such a table back has to treat
a string with no `.` and no `e` as an exact rational and everything else as
the interval its last digit denotes. The same applied when the generator's
written values were diffed against the check's: 26 of the 816 differed only
in that one side wrote `8/9` and the other a hundred digits of it.

What the skill says now: "A string with no `.` and no `e` is an exact
integer, not an approximation"; return exact values exactly.

What it should say: a string with no `.` and no `e` is an exact integer *or
rational*, and a check that reads an `R` table back must parse both
forms -- and compare an exact entry exactly, not as the interval it would
be if it were rounded.

Evidence: `/tmp/gk_check_out.txt`, 2026-09-03, second run, the traceback
ending in `int('5/9')`; `diff` of the `VALUE` lines of `/tmp/gk_dry_out.txt`
and `/tmp/gk_check_out.txt`, 26 differing entries, all with a `/` on one side.

## When the nodes have rational squares, solve for the weights exactly and write the closed form

What happened: the small Kronrod rules have nodes whose squares are rational
($n\leq 2$: $3/5$; $1/3$ and $6/7$) or lie in a quadratic field ($n=3$:
$(55\mp 2\sqrt{330})/99$). For a symmetric rule the weights then satisfy a
linear system in $x_k^2$ of size $n+2$, and solving it over $\mathbb{Q}$ --
or over $\mathbb{Q}(\sqrt{330})$, with a fifteen-line class for
$a+b\sqrt{d}$ -- gave every weight of those rules exactly: $98/495$,
$27/55$, $28/45$; $12500/46557$ at the Gauss nodes of $n=3$, and
$(4057614\pm 130977\sqrt{330})/16036300$ at its new nodes. The rational
ones are written exactly in the table and the others as closed forms in the
entry comments, which is what a reader holding $0.4013974147\ldots$ wants
to be told. A ball can only say it has a hundred digits.

What the skill says now: return exact values exactly; the lesson above on
`roots(ring=RIF)` says to take rational roots off before isolating.

What it should say: the same for a *derived* quantity: where a value is
determined by exact data through a linear system (interpolatory weights on
algebraic nodes, a coefficient from moments), solve that system exactly in
the field the data lives in before reaching for balls; if the field is
quadratic, arithmetic in it is a few lines and the answer is a formula
rather than digits. Check the closed form against the ball, and put it in
the entry comment.

Evidence: `/tmp/gk_check_out.txt`, 2026-09-03: `n=2 exact weights (centre,
+-1/sqrt3, +-sqrt(6/7)): [28/45, 27/55, 98/495]`, the four `n=3 exact
weights` lines with their minimal polynomials, and `n=3 closed-form weights
vs balls` passing after the index mapping was corrected.

## A closed form quoted for an entry can be proved exactly by reducing modulo the minimal polynomial of $x^2$

What happened: Wikipedia gives the Gauss–Lobatto rules with $n=6$ and $n=7$
in closed form, nodes $\pm\sqrt{\tfrac13\mp\tfrac{2\sqrt7}{21}}$ with
weights $(14\pm\sqrt7)/30$, and the table wanted to put them in the entry
comments. Comparing them with the balls would have shown agreement to a
hundred digits and proved nothing about the form. Instead: with $y=x^2$ the
inner node satisfies $m(y)=y^2-\tfrac23y+\tfrac1{21}$, and
$\sqrt7=(\tfrac13-y)\cdot\tfrac{21}{2}$ there. In $\mathbb{Q}[y]/(m)$ the
claim $w=2/(30P_5(x)^2)$ is the congruence $15\,w\,P_5^2\equiv 1 \pmod m$,
with $P_5^2$ an even polynomial rewritten in $y$, and it holds exactly. One
congruence covers both conjugate nodes, because the other embedding sends
the same expression to $-\sqrt7$ and the same $w$ to $(14-\sqrt7)/30$. The
control, the two weights the other way round, fails. Twelve lines, no
quadratic-field class, and the comment states something proved rather than
something that matched.

What the skill says now: "Verify a claim before writing it into a table";
the Kronrod lesson above says to solve for a weight exactly in the field
the data lives in and write the closed form.

What it should say: the same, and the cheap way to *verify* a closed form
somebody else wrote: when the algebraic number is a square root of an
element of a quadratic field, reduce modulo the minimal polynomial of its
square and check the identity as a congruence; the check is exact, and it
distinguishes the two conjugates by the sign of the expression for the
square root.

Evidence: `/tmp/lo_check_out.txt`, 2026-09-03: `PASS n=6: (14 + sqrt7)/30
is 2/(30 P_5(x)^2) at the inner node, and (14 - sqrt7)/30 at the outer,
exactly`, the same for $n=7$ in $\mathbb{Q}(\sqrt{15})$, and both controls
failing as they must.

## sympy's quadrature module is an independent source for Gauss-type rules at any order

What happened: neither OEIS (searched by the digits of the $n=6$ nodes)
nor DLMF (§3.5 does not use the name) holds a Gauss–Lobatto rule, and the
published rows stop at $n=7$ on Wikipedia, $n=6$ on MathWorld and $n=10$ in
Abramowitz–Stegun Table 25.6, so nothing outside the generator reached
$n=30$. `sympy.integrals.quadrature.gauss_lobatto(n, 60)` -- plain Python,
mpmath root-finding on sympy's own Legendre polynomials, sharing no code
with the generator -- gave every rule with $n\leq 30$ to sixty digits in
under a minute on the near machine, and all 928 written values agreed to
fifty digits with the control failing. The same module has
`gauss_legendre`, `gauss_hermite`, `gauss_laguerre`, `gauss_gen_laguerre`,
`gauss_chebyshev_t`, `gauss_chebyshev_u` and `gauss_jacobi`, which the three
Gauss tables before this one could have used above the orders OEIS and DLMF
reach.

What the skill says now: "Check new values against something independent",
with OEIS, DLMF, published tables and software constants as the sources the
lessons above name.

What it should say: for nodes and weights of a Gauss-type rule, sympy's
quadrature functions are a checked implementation at arbitrary precision
and any order, available wherever Python is; use them where the printed
tables stop, and give the one-line call under `Programs` as the Python
program, since it is also the shortest way for a reader to get one more
value.

Evidence: `/tmp/lo_compare.py`, 2026-09-03: `entries compared to 50 digits:
928 disagreements: 0 worst relative difference: 2.50e-60`, `control (30,2,w
shifted by 1e-45 relative): fails as it must`.

## An entry read back through the API is a bare value or a record, and one table has both

What happened: the read-back checks of the Lobatto build parsed the stored
Legendre polynomials of T101 without trouble, then died twice: on T133,
where `Numbers['3']` is the string `5*x^2 - 4/3` but `Numbers['0']` is
`{'number': '0', 'comment': ...}`, and on T132, where a node with a comment
is a record and the node beside it is a string. `numberdb.table()` returns
an entry as its value alone when it carries no annotation and as a mapping
with `number`, `comment`, `equals` when it does, so a table in which some
entries are annotated holds both shapes side by side, and the T132 build's
own read-back script had already learned to test `isinstance(rec, dict)`.

What the skill says now: "`Numbers` is every entry the table holds", and
nothing about the shape of one.

What it should say: an entry is either its value or a record whose `number`
is the value; write the accessor once (`rec['number'] if isinstance(rec,
dict) else rec`) before reading any table back, because the first entry
looked at decides which shape the script expects and the other shape is on
the same page.

Evidence: `/tmp/lo_check_out.txt`, 2026-09-03, first two runs:
`AttributeError: 'dict' object has no attribute 'replace'` on T133 and
`TypeError: string indices must be integers, not 'str'` on T132; third run
173 checks passing.

## A key reads a draft through the API, not through its page

What happened: repairing T137 while it was a draft, `GET /api/table?id=T137`
with the owner's key answered the whole document, so the edit could be read,
changed and written back. `GET /T137` and `GET /<url>` with the same
`Authorization: Bearer` header answered 404, the same as to an anonymous
request: the page route knows only a browser session, and a key holder
checking how a draft renders gets "Not Found" with no hint that the key was
read and ignored. The critique had rendered the page another way, inside
the deployment, which a contributor cannot do.

What the skill says now: "A draft is invisible, in no listing, answers no
search" -- true, but a reader with a key and a draft of their own does not
learn from it which of the two doors the key opens.

What it should say: a key reads and writes a draft through the API only.
To see the page as it will render, log in to the site in a browser, or
read the sections back through the API and check the prose there; a `404`
on the page with the key set is the route ignoring the key, not the draft
being gone.

Evidence: 2026-09-03, `curl -K -` with the bearer header from the key file:
`api/table?id=T137` → 200 with the document, `/T137` → 404 with 179 bytes,
`/Nodes_and_weights_of_Gauss_Kronrod_quadrature` (T136, also a draft) → 404.

## Two standard tables of the same knots can be mirror images entry by entry; a chirality-sensitive invariant must name its diagram source

What happened: the 2026-09-03 ideas run computed the Jones polynomials of
the 249 prime knots up to ten crossings from Sage's `Knots().from_table`
(Knot Atlas braid words) and compared them with KnotInfo's
`jones_polynomial` column. 112 agreed and 137 were mirror images
($t \mapsto t^{-1}$); the signatures flipped sign on exactly those 137. The
Alexander and Conway polynomials, determinants and volumes agreed on all
249, so nothing pointed at the disagreement until a chirality-sensitive
value was compared. Neither source is wrong: $n_k$ names a knot up to
mirror image, and the two tables drew different mirrors (Knot Atlas's
$3_1$ is left-handed, KnotInfo's right-handed).

What the skill says now: "Which normalisation, branch, and indexing" --
nothing about a family whose *objects* have two conventional
representatives that a name does not distinguish.

What it should say: when the named object has a symmetry the name ignores
(a mirror image, a sign of a unit, a choice of orientation), and the value
depends on that choice, the table must say which representative it stores
and where that representative comes from -- or store both. Comparing only
symmetry-blind invariants against a second source will pass and prove
nothing about the choice.

Evidence: `/tmp/kn_compare.py`, 2026-09-03: `jones same chirality: 112,
jones mirror: 137, sig same: 143, sig opposite: 106, problems: []`;
`BATCH-2026-09-03T0305.md`, shared conventions.

## `RealBallField(p)("2.0298832128")` is a point, not the interval the digits claim

What happened: the figure-eight volume computed in arb at 400 bits
(radius $1.4 \cdot 10^{-119}$) was compared with OEIS A091518's 58 digits
and KnotInfo's ten by `overlaps`, and both said `False` although every
digit agreed. `RBF("2.0298832128")` has radius $5 \cdot 10^{-121}$: Sage
parses the string as the exact decimal, not as the interval "last digit
off by one" that the corpus (and OEIS, and a printed table) mean by it.
Widening by one unit in the last place, `RBF(s).add_error(RBF(10)**(-k))`
with `k` the number of decimals, made both comparisons pass and both
controls (last digit changed by three, or by two) fail.

What the skill says now: "Check the claim the digits make, not the value
at their midpoint" -- the right principle, illustrated with zeros.

What it should say: a published decimal is an interval, and Sage's string
constructor does not build that interval; add the radius by hand before
comparing, and keep a control that must fail.

Evidence: checked in Sage on 2026-09-03. The ball built from the string
has radius `5.4458324e-121`; the OEIS value overlaps the claimed
interval and the KnotInfo value `2.0298832128` does too, while both
controls fail as they must -- the 58th digit changed by 3, and
`2.0298832130`.

## `RealBall` has no `str` method, with or without `sage.all`

What happened: `ball.str(60)` raised `AttributeError: 'RealBall' object has
no attribute 'str'` in a script that had done `from sage.all import *`.
`hasattr(ball, 'str')` is `False` and `hasattr(ball.mid(), 'str')` is
`True` (Sage 10.9). `RealField(200)(ball.mid())` or `ball.mid().str()`
prints the digits; `ball.rad()` says how many of them are meant.

What the skill says now: "What else the named imports do not bring: root
finding, `RealBall.str`, and `QQ('1.25')`" -- which reads as though
importing `sage.all` would bring it.

What it should say: a `RealBall` has no `str`; print its midpoint (a
`RealNumber`, which has one) and its radius separately. The named-imports
sentence should drop `RealBall.str` from its list or say the method does
not exist at all.

Evidence: `/tmp/kn_vol2.py` output, 2026-09-03: `hasattr str: False mid has
str: True`.

## Sage's knot table: 249 knots, a symbolic Jones polynomial, and no unknot

What happened: three things met in the first minute of computing knot
invariants in Sage 10.9. `Knots().from_table(n, k)` holds the Rolfsen
table to ten crossings from Knot Atlas braid words, and the counts per
crossing number (1, 1, 2, 3, 7, 21, 49, 165) are OEIS A002863, which is
the check that nothing is missing. `jones_polynomial()` returns a
*symbolic expression*, not a Laurent polynomial -- links can have
half-integer exponents -- so `.dict()` fails; `expr.coefficients(t)` gives
(coefficient, exponent) pairs to rebuild it in `LaurentPolynomialRing(ZZ,
't')`. And `from_table(0, 1)`, the unknot, raises inside `BraidGroup(1)`;
its polynomials are $1$ and go in by hand. `alexander_polynomial()` is the
Conway-normalised Laurent form (`-t^-1 + 3 - t` for $4_1$), not Rolfsen's
positive-constant-term polynomial; `conway_polynomial()` prints in `t`,
not `z`. All 249 Alexander and Conway polynomials, and all Jones
polynomials up to mirror image, agree with KnotInfo.

What the skill says now: nothing about knots; the generator section
assumes a special function.

What it should say: for a finite named family that Sage ships as a table,
check the count against the OEIS sequence that counts it before anything
else; and read the docstring for what a method returns, since a symbolic
expression and a Laurent polynomial print alike.

Evidence: `/tmp/knot_all_run.py` output `/tmp/knot_all_out.txt`,
2026-09-03: `N knots 249`, `bad: []`, `counts per crossing number {3: 1,
4: 1, 5: 2, 6: 3, 7: 7, 8: 21, 9: 49, 10: 165}`; the first two runs' tracebacks
(`AttributeError: 'sage.symbolic.expression.Expression' object has no
attribute 'dict'`; `KeyError` in `BraidGroup` for `(0, 1)`).

## The knot table loads under named imports once `sage.symbolic.ring` has been imported first

What happened: the generator for T138 opened with `import numberdb.sage`
and `from sage.knots.knot import Knots`, as the skill asks, and the first
`Knots().from_table(3, 1)` died in `sage.groups.braid`, which imports
`sage.functions.generalized`, which reaches `sage.symbolic.function` while
`sage.symbolic.expression` is still initialising: "cannot access submodule
'function' of module 'sage.symbolic' (most likely due to a circular
import)" -- the same message the T133 build met from `PowerSeriesRing` and
`QQ(x).log()`. A probe of import orders found that `import
sage.symbolic.ring` succeeds on its own, and that after it
`sage.functions.generalized`, `sage.groups.braid` and `sage.knots.knot` all
import and `from_table` works. One named import, not `sage.all`, and the
generator passes `names_its_rings`.

What the skill says now: "Expect the machinery to be missing ... power
series `.log()` and `.inverse()`, `matrix(...).determinant()`, and
`SymmetricFunctions(...).expand()` all reach for parts of Sage that are not
initialised. Write the arithmetic out."

What it should say: the same, plus that the circular import is often only
an *order* problem: `import sage.symbolic.ring` before the module that
needs symbolic functions brings the symbolic ring up cleanly, after which
the braid group, the knot table and `sage.functions` load. Try that one
line before rewriting a library computation by hand; and still write the
independent check by hand, which is what the Burau determinant in T138's
generator is for.

Evidence: `/tmp/kn_dry_out.txt`, 2026-09-03, first run: the traceback
through `sage/groups/braid.py:78` and `sage/symbolic/function.pyx:155`;
`/tmp/kn_probe_out.txt`: `OK sage.symbolic.ring`, `OK sage.groups.braid`,
`OK sage.knots.knot`, `trefoil: t^-1 - 1 + t 3`.

## An identity stated for one normalisation must be carried through the unit before it is checked on another

What happened: the outside check for T138 tested the Conway substitution
$\Delta(s^2)=\nabla(s-s^{-1})$ against Sage's `conway_polynomial()` and
reported a failure on all 249 knots. The identity is exact for the
Conway-normalised Laurent form $\epsilon t^{-g}\Delta(t)$, which is what
the ideas run had compared a day earlier; the table stores Rolfsen's
polynomial $\Delta(t)$ with positive constant term, so the identity it
satisfies is $\Delta(s^2)=\epsilon s^{2g}\nabla(s-s^{-1})$. With the unit
carried across, all 249 pass and the control with the wrong power of $s$
fails. A failure on every entry at once is the signature of the checker,
not the table -- the same pattern as the "all the small ones fail" b-file
lesson -- and this one was a normalisation the check had forgotten the
table had chosen. The same run also mistyped a braid word in a control
(`1,1,1,2,-1,2,3,-2,3` for $7_4$'s `1,1,2,-1,2,2,3,-2,3`), and the control
"failed" because the mistyped braid closes to a knot with $\Delta(7_2)$;
a control that fails is a control to read again before the table is.

What the skill says now: "If your recomputation disagrees with a stored
value, suspect your recomputation first"; and the Definition should pin
down the normalisation.

What it should say: when the table's normalisation differs from the one an
identity is usually written in, rewrite the identity for the stored form
*before* running the check, and write the unit into the Formulas section
so that a reader with the other convention sees it too --
$\Delta(s^2)=\epsilon s^{2g}\nabla(s-s^{-1})$ with $\epsilon=\Delta(1)$
rather than the bare $\Delta(s^2)=\nabla(s-s^{-1})$.

Evidence: `/tmp/kn_check_out.txt`, 2026-09-03, first run: `FAIL Conway
substitution 3_1` through `10_165`, `FAILURES: 250`; second run after the
unit was carried across: `PASS count: 3295 FAILURES: 0`.

## A formula copied from a source keeps the source's letters; check them against the Parameters section

What happened: T138's Parameters define $n$ as the crossing number, and the
header of every row is $\Delta_{n_k}(t)$. Its Burau formula, taken from the
standard statement, read "for the closure of a braid on $n$ strands,
$\Delta(t)\doteq\det(I-\psi(\beta))\frac{1-t}{1-t^n}$" -- the same letter for
the number of strands, which for $10_{132}$ is four. A reader putting the
row's $n=10$ into the formula gets the wrong polynomial and no warning. The
rigour details repeated the formula with the same $n$. The obvious
replacement, $m$, was already taken too: the Definition says the polynomial
is defined up to $\pm t^m$. The letter that went in was $r$, the one letter
the page did not use.

What the skill says now: the definition must pin the variable names, and a
formula states a relation; nothing about letters a quoted formula brings
with it.

What it should say: before writing a formula, list the letters already
bound on the page -- the parameters, the display variable, the unit in the
definition -- and rename anything in the formula that collides, in the
Formulas section and in `rigour details` alike. A parameter's letter means
one thing everywhere on the page, and a formula using it for something else
is a false statement about every entry.

Evidence: T138 formula (4) and its rigour details, 2026-09-03; KnotInfo
`braid_index` of $10_{132}$ is 4 where $n=10$.

## A value that depends on a symmetry the name ignores: store both, and count coincidences up to that symmetry

What happened: the Jones polynomial of $n_k$ depends on which mirror image
$n_k$ means, and the two standard tables draw different ones for 137 of
the 249 knots (previous lesson). T139 stores both: a third parameter
`knot`, `Symbolic`, with values `K` (the diagram KnotInfo gives, rebuilt
from its braid word) and `mirror`, and one entry only for the 20
amphichiral knots, which are their own mirror images. The proposal had
counted the Jones coincidences in one chirality and found ten pairs; with
both mirrors stored there are fourteen. The four it missed ($8_8$ and
$10_{129}$, $10_{22}$ and $10_{35}$, $10_{60}$ and $10_{86}$, $10_{137}$
and $10_{155}$) coincide only across the mirror, $V_A(t)=V_B(t^{-1})$, in
either source's chirality; $5_1$ and $10_{132}$ do the same in KnotInfo's
and are equal in the Knot Atlas's, which is the one the proposal had
counted in. Two smaller
decisions came with the parameter: its values could not be `yes`/`no`,
which PyYAML reads as booleans when the document is parsed, so the entry
key and the declared value would silently differ; and an amphichiral knot
gets one entry rather than two equal ones, with the parameter's constraint
saying so, so the missing rows are explained by the schema rather than
left as holes.

What the skill says now: "Search by number is sign-sensitive, so a
symmetric family must store both signs" (a lesson above); "Which
normalisation, branch, and indexing" -- nothing about a family whose
objects, not values, come in symmetric pairs.

What it should say: when a name fixes an object only up to a symmetry and
the value sees the symmetry, store one entry per orbit element as a
`Symbolic` parameter whose values are plain words that no YAML parser
reads as something else, list the self-symmetric objects once and say so
in the parameter's constraint, and count coincidences up to the symmetry
-- a pair that agrees only across it is still a pair.

Evidence: T139; `/tmp/jn_check_out.txt`, 2026-09-03: `distinct up to
mirror: 235 pairs: 14`, where the batch said ten; the local PyYAML parse of
a `values: {no: ..., yes: ...}` block gives keys `False` and `True`.

## A theorem checked in the generator must be the theorem, not the stronger version one remembers

What happened: the T139 generator checks Thistlethwaite's theorem that
the Jones polynomial of an alternating knot is alternating. The first
version demanded consecutive nonzero coefficients of opposite sign with
no gaps, and the very first knot refused it: the right-handed trefoil is
$t+t^3-t^4$, with a zero at $t^2$. The theorem says $(-1)^ea_e\geq0$ for
all $e$ or $\leq0$ for all $e$, zeros allowed. The check was rewritten to
that, and every one of the 249 knots then passed, with span exactly $n$
and extreme coefficients $\pm1$ for the alternating ones and span below
$n$ for the non-alternating ones.

What the skill says now: "A pattern true for every small case belongs in
the generator as a check, where it can fail" (a lesson above); "Verify a
claim before writing it into a table, including one somebody suggested."

What it should say: the same, plus that a check which fails on the first,
simplest entry is nearly always the check: before weakening or dropping
it, look up the theorem's exact statement, and write that. The failure
that stops at the trefoil is the cheapest kind of wrong to have, and it
would have gone into the Formulas section as a false sentence had the
generator not been asked first.

Evidence: `/tmp/jn_dry_out.txt`, 2026-09-03, first run: `ArithmeticError:
3_1: alternating, but V = {1: 1, 3: 1, 4: -1}`; second run: 479 entries
clean.

## KnotInfo's braid words reproduce its chirality in Sage, and one of them is a list of two

What happened: the Jones polynomial of `Link(BraidGroup(r)(word))` with
`word` from KnotInfo's `braid_notation` column equals KnotInfo's
`jones_polynomial` column exactly for all 249 knots, and so do
`signature()` and `determinant()` -- Sage's generator and sign
conventions are KnotInfo's, so a builder who wants KnotInfo's mirror image
can embed its braid words (11 KB for 249 knots) and need nothing else.
`Link(pd)` from `pd_notation` gives the same. Two things bit on the way:
`braid_notation` for $10_{136}$ is a list of two words, so the JSON that
parses flat for 248 knots is nested for one, and `BraidGroup(4)(...)`
dies inside `free_group.py` with a `TypeError` about a list rather than
saying what it was given; and `jones_polynomial()` is symbolic, so the
coefficients come out of `V.coefficients(V.default_variable())` as
`[[coefficient, exponent], ...]`. Under the named imports (with
`sage.symbolic.ring` first), `jones_polynomial(algorithm='statesum')`,
`mirror_image()` and `LaurentPolynomialRing` all work, which gives the
independent computation for free: braid representation against Kauffman
bracket, on the same diagram.

What the skill says now: "Expect the machinery to be missing"; the knot
lessons above cover loading the table and the symbolic return type.

What it should say: for a family whose independent source is a published
dataset, check that the source's encoding reproduces the source's own
values in your software before trusting either (here: KnotInfo's braid,
through Sage, gives KnotInfo's polynomial, for every row); and inspect the
shape of every row of a data column before embedding it, since one
irregular row in 249 is the normal case rather than the exception.

Evidence: `/tmp/jn_probe_out.txt`, 2026-09-03: `braid == knotinfo 249`,
`pd == knotinfo 249`, `statesum == jonesrep (pd) 249`, `mirror_image ==
t->1/t 249`, `pd signature == knotinfo 249`; the first probe's traceback
`TypeError: unsupported operand parent(s) for >: 'Integer Ring' and
'<class 'list'>'` at `(10, 136)`.

## A `Symbolic` parameter without `display` is shown as `$name$`, in math italics

What happened: T139's third parameter is `knot`, of type `Symbolic`, with
`values: {K: $K$, mirror: $\bar K$}`, a title and a constraint, and no
`display`. The site falls back to `$knot$` for a parameter with no
`display` (`views.py`, `p_latex = … "$%s$" % (p,)`), so the head of the
third column of the entry table and the third line of the Parameters
section both typeset the word as $k\,n\,o\,t$, a product of four
variables, on the first screen of the page. The stored YAML looks fine;
only the rendering shows it. Every published table with a `Symbolic`
parameter either sets `display` (`Mass_ratios`: `$m_1$`, `$m_2$`) or
hides it with `show-in-parameter-list: no`.

What the skill says now: nothing about `display`; the `Symbolic` lesson
above describes `values` as a mapping from key to display and says
nothing about the parameter's own name.

What it should say: a parameter whose name is a word rather than a letter
needs `display` (plain text is inserted as it is, so `display: knot`
works; `$\text{knot}$` if it must be math like its neighbours), because
the default wraps the name in `$…$`; and a build should look at the
rendered column heads once, since this is invisible in the document.

Evidence: the T139 draft page rendered as its owner on 2026-09-03
(`/tmp/crit139_text.txt`, header row `$n$ $k$ $knot$ $t^{-m}V_K(t)$`);
`agents/critiques/T139.md` finding 1.

## A count of what a source draws must be decided for every row, and the invariant on the page may be blind to some

What happened: T139's comment said the Knot Atlas draws the mirror image
for "137 of the 249 knots". The 137 came from comparing Jones polynomials
of the two sources' braid closures and counting the rows where they
differ. Six chiral knots have $V(t)=V(t^{-1})$, so the Jones polynomial
cannot see their mirror image at all; the count treated all six as
"same diagram". Sage's `signature()`, which agrees with KnotInfo's column
on all 249 of KnotInfo's closures, is the negative on the Atlas closures
of $9_{42}$ and $10_{125}$, so the true count was 139. For the remaining
four ($10_{48}$, $10_{71}$, $10_{91}$, $10_{104}$) the signature is $0$
and HOMFLY is symmetric too; what decided them was that Sage's
`small_knots_table` holds KnotInfo's braid word letter for letter, so the
two sources draw the same diagram and no invariant is needed. The
critique had proposed "at least 137"; the checked answer was a different
number and a complete one.

What the skill says now: "Check every identity before you write it down",
and "narrow a claim rather than dropping it" in the repair prompt.

What it should say: a count in a comment about which representative a
source uses is a claim about every row, so it needs a decision procedure
that returns an answer for every row. When the invariant on the page is
symmetric for some entries, look for a second invariant, and when none
sees the difference, compare the sources' encodings (the braid words, the
PD codes) directly: two identical encodings settle it without any
invariant. "At least" is the fallback only when a row is genuinely
undecidable.

Evidence: `/tmp/t139_knots_out.txt`, 2026-09-03: `counts {'equal': 86,
'mirrored': 137, 'both': 26, 'neither': 0}`, `sage sig == KnotInfo sig for
249 knots`, `9_42 … sig Atlas-closure -2`, and for $10_{48}$ "Atlas table
entry (3, [-1, -1, -1, -1, 2, 2, -1, 2, 2, 2])", the same as KnotInfo's.

## Compare an exact family with every stored polynomial table, variable renamed, before writing `equals` links

What happened: the proposal for the Conway polynomials (T140) expected
no link but the Alexander table. Before the fill, the 250 values were
compared locally with every entry of the seven one-variable polynomial
tables the corpus holds (T95, T98, T99, T104, T108, T109, T115, read
through `api/table`), each entry rewritten in the same variable. Eight
coincided exactly: $\nabla(3_1)$, $\nabla(5_1)$, $\nabla(7_1)$,
$\nabla(9_1)$ and $\nabla(10_{132})$ are the Fibonacci polynomials $F_3$,
$F_5$, $F_7$, $F_9$, $F_5$ of T108, and $\nabla(3_1)$, $\nabla(9_{44})$,
$\nabla(7_7)$ are $\Phi_4$, $\Phi_8$, $\Phi_{12}$ of T95. The Fibonacci
coincidence is a theorem -- $\nabla_{T(2,q)}=F_q$, two lines from the
Binet form of $F_q$ and $\Delta_{T(2,q)}=(t^q+1)/(t+1)$ -- which none of
the screened sources states, and it became the table's cleanest formula
and five `equals` links. Five more values matched a stored entry only up to
sign ($-T_2$, $-U_2$, $-\mathrm{He}_2$), which are not equalities and were
left alone.

What the skill says now: search titles, tags and definitions before
linking; the T138 build found its cyclotomic links from a known
factorisation.

What it should say: for an exact polynomial family, fetch every
polynomial table the corpus holds and compare value by value with the
variable renamed, before the draft exists. A coincidence found that way is
either a fact worth an `equals` link or the family's own formula in
disguise, and a name search finds neither.

Evidence: the local comparison on 2026-09-03 (`EQUAL T108 ('5',) x^4 +
3*x^2 + 1 = 5_1`, `EQUAL T95 ('12',) x^4 - x^2 + 1 = 7_7`, ...);
`/tmp/cw_check_out.txt`, `nabla(T(2,q)) = F_q from (t^q + 1)/(t + 1)` for
odd $q\leq 25$ with the $F_{q+2}$ control failing.

## A second library method is a second computation only when its source says what it computes from

What happened: the plan for T140 was to accept Sage's
`conway_polynomial()` when it agreed with Sage's `alexander_polynomial()`
through the substitution, on the grounds that the two are different
methods. `inspect.getsource(Link.conway_polynomial)` showed that it
*calls* `alexander_polynomial()` and substitutes $t-t^{-1}$ into it, so
the agreement would have checked the substitution and nothing about the
Seifert determinant underneath. The independent computation in the
generator is the hand-written Burau determinant of the same braid word,
converted to $\nabla$ by a hand-written change of variable, which shares
no code with either method; the two agree on all 249 knots.

What the skill says now: "A generator checked against its own definition
proves nothing", and "compare against a computation sharing no code".

What it should say: the same, plus: two methods of one library are not
two computations until their sources show what each is computed from;
read the source (`inspect.getsource`) of any method taken as the second
computation, since a library routinely defines one invariant as a
substitution into another.

Evidence: `/tmp/cw_probe_out.txt`, 2026-09-03, the source of
`conway_polynomial` (`alex = self.alexander_polynomial()` ... `binom = t -
~t`); `compared 249 bad 0` for the Burau route.

## A comment assembled from fragments can put two `$` together

What happened: the T140 comment for $3_1$ was built as `'$\nabla=F_3$'`
followed by `'$=\Phi_4$'`, which the dry run printed as
`$\nabla=F_{3}$$=\Phi_{4}$`. The two adjacent dollars open display
mathematics in MathJax, so the line would have rendered wrongly on the
page while looking fine in the YAML. The fragments were joined inside one
`$...$` before the fill.

What the skill says now: use `$...$` for mathematics; nothing about
building a comment from pieces.

What it should say: when a comment is assembled from optional pieces,
join the mathematics first and wrap it once; and read the dry run's sample
comments for `$$`, which is the signature.

Evidence: `/tmp/cw_dry_out.txt`, first run, the line for `3,1`.

## SnapPy's Rolfsen table names the ten-crossing knots as Rolfsen did before Perko, and its 10_83 and 10_86 are each other's

What happened: the volume table T141 was to be built from
`snappy.Manifold('n_k')`. `snappy.LinkExteriors` holds 166 ten-crossing
knots, and `Manifold('10_161')` and `Manifold('10_162')` are isometric --
the Perko pair -- so SnapPy's `10_{k+1}` is the after-Perko $10_k$ of
KnotInfo, the Knot Atlas and Sage for $k \geq 162$. Worse, SnapPy's
`10_83` has the volume KnotInfo lists for $10_{86}$ and its `10_86` the
volume of $10_{83}$: neither is isometric to the exterior of the braid word
Sage's knot table gives for that name, nor to the exterior of KnotInfo's
diagram, while those two exteriors are isometric for all 243 hyperbolic
knots. A table built from SnapPy's names would have carried six wrong
entries ($10_{83}$, $10_{86}$, $10_{162}$ to $10_{165}$) with a hundred
proven digits each. The generator builds every exterior from the braid word
of Sage's table (`Link(braid_closure=word).exterior()`) instead, and the
table says whose numbering it follows.

What the skill says now: "Never guess a name the database resolves", about
slugs and tags; nothing about two libraries numbering one finite family
differently.

What it should say: when a family is looked up by name in a library, check
by an invariant, on every member, that the library's names agree with the
source the table cites, before computing; and where an object has a
description (a braid word, a diagram), build from the description rather
than from a lookup by name, so that the value is tied to the object and not
to somebody's index.

Evidence: `/tmp/hv_export2.py` output, 2026-09-03: `not isometric to
SnapPy name: [('10_83', '10_83'), ('10_86', '10_86')]`, `perko
{'isometric': True}`, `LinkExteriors` counts `(10, 166)`; KnotInfo
`volume` column 14.2580518491 for 10_83 where `Manifold('10_83').volume()`
is 14.3412561395.

## A proven hyperbolic volume needs only the integers of a triangulation: a Krawczyk test and the Bloch-Wigner dilogarithm in arb

What happened: SnapPy's `volume(verified=True)` needs SnapPy inside Sage,
and the Sage at hand had no SnapPy. But the gluing equations of an ideal
triangulation are integer exponent matrices, and SnapPy's shapes are only
a starting point. A Krawczyk test on $n-1$ edge equations and the meridian,
written as $\log(c\prod z_i^{a_i}(1-z_i)^{b_i})=0$ so the Jacobian is
$a_i/z_i-b_i/(1-z_i)$; a check that every shape ball has positive imaginary
part; the logarithmic equations evaluated on the balls within $0.1$ of
$2\pi i$ (edges) and $0$ (cusp curves), which pins each since at the
certified point it is an exact multiple of $\pi i$; and $\sum D(z_i)$ with
arb's `polylog(2)`: about 150 lines, 113 to 117 digits at 397 bits, a
second per knot, and the six torus knots refused by the same code because
their triangulations are flat. This is HIKMOT's criterion, the one SnapPy's
`verify_hyperbolicity` applies. Two things about SnapPy's numbers along the
way: `high_precision().volume()` prints 64 significant digits and is right
to 62 (five of 243 differ from the certified ball in the 63rd), and its
tiny numbers print with a space before the exponent, `2.30 E-52`, which
arb's string constructor refuses.

What the skill says now: prefer balls for anything transcendental, and a
list of the special functions arb implements; nothing about a value that
is a function of the solution of algebraic equations.

What it should say: a value that depends on the solution of a system of
polynomial equations -- shapes of a triangulation, a unit, a root -- is
proven in two steps in ball arithmetic: an interval Newton or Krawczyk test
proves the solution lies in a box of balls, and the function evaluated on
the box is the value. A library's own "verified" routine is then a
comparison, not a requirement. And a float another library prints is
accurate to fewer digits than it prints; measure where the agreement with
the ball stops before choosing the tolerance of the comparison, or the
comparison reports a disagreement that is the other side's roundoff.

Evidence: `generators/hyperbolic-volumes-prime-knots/generate.py`;
`/tmp/hv_all.py` output 2026-09-03: `certified 243 of 243 in 214.9 s`,
`agree with SnapPy quad-double: 238` at $10^{-63}$ with the five
differences between $1.1\cdot10^{-63}$ and $2.5\cdot10^{-63}$, `worst
radius 3.8e-114 at 10_122`; `/tmp/hv_core_test.py`: the conjugate solution,
a wrong meridian sign and a wrong logarithmic row each refused.

## A coincidence in a source's ten decimals is a hypothesis; certify both sides before stating it, and state what the digits show

What happened: KnotInfo's ten decimals name thirteen pairs of knots with
the same volume ($9_{42}$ and $10_{132}$ inside the table; $5_2$ and the
$(-2,3,7)$ pretzel knot $12n_{242}$, and ten more with eleven to thirteen
crossings). Ten decimals agree by accident among 12966 values often enough
that this could not be written into a comment. Certifying the partner
knots' volumes from KnotInfo's diagrams by the same code showed every pair's
balls overlapping, with differences below $10^{-114}$; the comments say
"agrees to the hundred digits listed with", which is what was shown, and
not "equal", which was not.

What the skill says now: verify a claim before writing it into a table,
including one somebody suggested.

What it should say: the same, with the form of the resulting sentence: a
comment states the agreement the digits certify, in the digits' own terms,
and leaves the equality to a reference that proves it.

Evidence: `/tmp/hv_all.py` output 2026-09-03, `5_2 vs 12n_242: difference
[+/- 3.20e-117], overlap True` and the twelve lines like it; the
`SAME_VOLUME` dictionary in the generator.

## The trivial character's value at $0$ is a convention, and a point-count identity depends on it

What happened: the stage-one check for a table of Jacobi sums compared the
number of solutions of $x^k + y^k = 1$ over $\mathbb{F}_p$, counted by
enumeration, with $\sum_{\chi^k = \psi^k = 1} J(\chi,\psi)$. It failed at
the first case, $p = 3$, $k = 2$: count 4, sum 2. Ireland-Rosen, whose
theorem it is, define the trivial character with $\varepsilon(0) = 1$, so
that $J(\varepsilon,\chi) = 0$; Sage's trivial character has value $0$ at
$0$, so the same sum is $-1$, and every trivial factor in the identity is
off by one. With $\varepsilon(0) = 1$ written into the checker, all 38 cases
with $p \leq 31$ agree.

What the skill says now: "Which normalisation, branch, and indexing";
nothing about a character's value off the units.

What it should say: a sum over $a \bmod q$ that includes $a = 0$ (or any
$a$ not coprime to $q$) has a convention hidden in it, and a library's
convention and a textbook's need not agree; when an identity from a book
fails on the smallest case by a small integer, look at the terms the book
defines and the library sets to zero. A table of such sums states the
convention in its Definition even when its entries avoid it.

Evidence: `/tmp/chars_check_0903.py`, 2026-09-03, first run
`AssertionError: (3, 2, 2, 4)`; after the change, "Fermat-curve point
counts match sums of Jacobi sums for p <= 31, all k | p-1: 38 cases".

## `CBF(x.complex_embedding(prec))` of an exact algebraic number is a point; evaluate its polynomial at a ball root of unity

What happened: the same check required $|J(\chi,\psi)|^2 = p$ in balls and
failed at $p = 7$ although the exact identity $J = \tau(\chi)\tau(\psi)/
\tau(\chi\psi)$ had passed on the same pair. The ball had been built as
`CBF(J.complex_embedding(300))`: the embedding is a 300-bit rounding, the
ball around it has radius zero, and $|J|^2$ computed from it misses $7$ by
$10^{-90}$ with a radius smaller than that. Building the ball as
`J.polynomial()(z)` with `z = exp(2 pi i / m)` in `ComplexBallField`, $m$
the order of the field's generator, gives an enclosure of the exact number
and every comparison passed. The Gauss sums had passed the same test only
because the *other* side was a ball with a radius.

What the skill says now: "`RealBallField(p)("2.0298832128")` is a point,
not the interval the digits claim" (a lesson above), for decimal strings.

What it should say: the same for an exact algebraic number handed to a ball
field through a floating embedding -- `complex_embedding`, `n()`,
`numerical_approx()` all round first. Enclose an element of a number field
by evaluating its polynomial at a ball enclosure of the generator, and treat
a zero-radius ball on either side of a comparison as a checker bug.

Evidence: `/tmp/chars_check_0903.py`, 2026-09-03, second run
`AssertionError: (7, 'abs')`; third run, with `to_ball`, "|J|^2 = p (p <=
31) and J = g g / g (p <= 13): OK".

## `RealNumber.str(20)` prints in base 20; the digits keyword is `digits=`

What happened: the Gauss sums were printed with `ball.mid().str(20)` to get
twenty digits and came out as `2.783f21j2f05hc94ec0cg79j24b95052fi631ff` --
the first positional argument of `RealNumber.str` is the base. `str(digits=20)`
prints what was meant.

What the skill says now: a lesson above says a `RealBall` has no `str` and
to print its midpoint; nothing about the signature.

What it should say: `mid().str(digits=n)`, with the keyword, and that a
printed value full of letters is base 20 or 36 rather than corruption.

Evidence: `/tmp/chars_check_out.txt`, 2026-09-03, first run.

## `ComplexBall` has no `digamma`; take `RealBall.psi()` and coerce it up

What happened: $L(1,\chi) = -\frac1q\sum_a \chi(a)\psi(a/q)$ was written
with `CBF(a/q).digamma()` and raised `AttributeError: 'ComplexBall' object
has no attribute 'digamma'. Did you mean: 'gamma'?`. `RealBall.psi()` is
the digamma (T128's own program uses it), and `CBF(RBF(a/q).psi())` is the
complex ball the sum needs. The mirror of the `legendre_Q` lesson above,
where the method existed only on the complex ball.

What the skill says now: the list of what arb implements, and the lesson
that some methods are reached only through `ComplexBallField`.

What it should say: the two ball classes expose different subsets of arb
under different names (`psi` on `RealBall`, `legendre_Q` and `integral` on
the complex side); when one lacks a method, try the other and coerce.

Evidence: `/tmp/chars_check_out.txt`, 2026-09-03, third run traceback;
fourth run, "digamma route vs Gauss-sum closed forms agree for all 76
primitive characters".

## OEIS holds Gauss sums by digits under their minimal polynomials, and LMFDB's character calculators answer `curl` a few times

What happened: OEIS searched for "Gauss sum" returns theta series;
searched for the digits $2.370469405$ of the cubic Gauss sum mod 7 it
returns A396260, "Decimal expansion of the largest root to $8x^3 - 42x -
7 = 0$", whose comment names the character, with A396261 the imaginary
part and A396258/A396259 the order-6 character, all with 10000-digit
b-files. The same author's A396254/A396255 give the degree of every
$\tau(\chi)$ mod $p$ by a formula ($d\varphi(d)$), an independent check on
the exact values' minimal polynomials. Separately, LMFDB's
`Character/calc-gauss/Dirichlet/7/2?val=1`, `calc-jacobi/...?val=2` and
`calc-kloosterman/...?val=1,1` answer a plain `curl` with ten decimals, or
the exact cyclotomic integer for the Jacobi sum; after about four requests
in a minute the answer is a JavaScript gate, so they are a hand check on a
few entries, not a source to loop over. The `api/` routes remain
unreachable as the earlier lesson says.

What the skill says now: search OEIS by the digits of a small member (a
lesson above); the LMFDB API does not answer.

What it should say: for an algebraic constant, OEIS's `%N` is the
polynomial, not the family, so search by digits and read the `%C` line for
the name; and LMFDB's per-object calculators are a different door from its
API -- fetch one value by hand to see whether it opens, and do not plan more
than a handful through it.

Evidence: `curl 'https://oeis.org/search?q=2.370469405&fmt=text'`,
2026-09-03; the six `calc-*` fetches the same day, of which the fifth and
sixth returned `window.wiz_progress...` instead of a value.

## `minpoly()` of a Gauss sum in a cyclotomic field of degree a thousand does not finish; count the Galois conjugates in balls instead

What happened: the comment on each entry of the Gauss-sum table was to give
the degree of $\tau(\chi)$ over $\mathbb{Q}$ and, when small, its minimal
polynomial. `chi.gauss_sum().minpoly()` is exact and one line, and for a
character of order 46 modulo 47 it works in $\mathbb{Q}(\zeta_{2162})$, of
degree 1012; a loop over the 471 characters was killed at the runner's
half-hour limit twice without reaching the end. What finished in 47 seconds
for the whole table: $\sigma_c(\tau(\chi))=\sum_a\chi(a)^c e^{2\pi iac/q}$
for $c\in(\mathbb{Z}/M)^\times$, $M=\mathrm{lcm}(q,d)$, is a sum of $M$-th
roots of unity, so every conjugate is $q$ table lookups and additions of
128-bit balls; the subgroup $\{c\equiv 1\ (d),\ \chi(c)=1\}$ fixes $\tau$, so
one $c$ per coset is enough (1012 of them at $q=47$); the number of pairwise
disjoint balls is the degree, with two balls that overlap compared exactly
(a single `gauss_sum(c)` of $\chi^c$, cheap); and the product over the
distinct conjugates, rounded to integers and required to vanish at the exact
value, is the minimal polynomial. The first version of the disjointness count
compared every pair and was itself the thing that timed out at $1012^2$
overlaps per character; sorted by real part, only neighbours can overlap.

What the skill says now: "Expect the machinery to be missing"; nothing about
machinery that is present and does not finish.

What it should say: an exact computation in a number field of degree in the
hundreds can be slower than a rigorous one in balls, and a degree is a count
of distinct conjugates: enclose them, prove them distinct by disjointness,
and settle any overlap exactly. Time the worst entry before looping over the
family, since the library call that is instant at $q=7$ is the one that
never returns at $q=47$.

Evidence: `/tmp/gs_probe_out.txt` (exit 124 at 1800 s), `/tmp/gs_probe3_out.txt`
(exit 124, the pairwise count), `/tmp/gs_probe4_out.txt`, 2026-09-03: "(47,5)
order 46: degree 1012 (d phi(d) = 1012) in 0.28 s", "all 471 entries in 47.1 s".

## The package refused every complex ball under `proven`: a complex interval carries its error in its parts

What happened: the first `publish()` of the Gauss sums, a type `C` table of
`ComplexBallField` values, stopped at its first ball with "rigour is
'proven', and this value carries no error of its own -- it is a point".
`_carries_its_own_error` in `numberdb/_generate.py` looked for `lower()` and
`upper()` on the value, which a real ball has and a complex ball does not,
and then asked the parent whether it is exact, which a ball field is not;
so every complex ball was a point. No complex table had been filled through
the package before. Fixed in the repository (a complex interval or ball is
a point only when both of its parts are), with tests; a contributor with the
released package sees the old behaviour until the next release, and the
fill here patched the function in the script that ran it.

What the skill says now: "`ComplexBallField(prec)(x)` -- complex interval,
from the ball -- `proven`", which was the intent and not, until now, the fact.

What it should say: the same, once released; and until then, that a refusal
of a complex ball as "a point" is the package, not the value, and an entry
with one exactly-zero part (the real part of $i\sqrt{3}$, written as `0 + i *
1.73...`) is still an enclosure.

Evidence: `/tmp/gs_fill_out.txt`, 2026-09-03, first run: `DisagreementError:
T142 entry 3,2: rigour is 'proven', and this value carries no error of its
own`; second run with the patch, `471 added`.

## `Integer.sqrt()` of a non-square is a symbolic expression, and `lcm` is not in `sage.arith.misc`

What happened: `ZZ(q).sqrt()` was used to decide whether $q$ is a square; for
$q=27$ it returned the symbolic $3\sqrt{3}$, and comparing it with an
integer reached `sage.symbolic` and `qqbar` and died with `NameError:
name 'RR_1_10' is not defined` under named imports. `ZZ(q).isqrt()` is the
integer square root and the test is `root**2 == q`. Separately, `from
sage.arith.misc import lcm` raises `ImportError`; `lcm` lives in
`sage.arith.functions` (and `gcd`, `euler_phi`, `factor`, `is_prime`,
`moebius`, `kronecker_symbol`, `inverse_mod` in `sage.arith.misc`). And
every one of these imports prints `UserWarning: Resolving lazy import ...
during startup`, which is noise and not a fault.

What the skill says now: name the rings; a list of what the named imports
do not bring.

What it should say: add `Integer.sqrt()` of a non-square to that list --
use `isqrt` -- and give the module for `lcm`; and that the lazy-import
warnings can be ignored.

Evidence: `/tmp/gs_dry_out.txt` first run, the traceback ending in
`qqbar.py ... NameError: name 'RR_1_10' is not defined`;
`/tmp/gs_probe2_out.txt` first run, `ImportError: cannot import name 'lcm'
from 'sage.arith.misc'`, 2026-09-03.

## `RealBall.rad()` is a 30-bit `RealNumber` that does not add to a ball

What happened: `rad_i + other.rad()` with one side a `RealBall` raised
`TypeError: unsupported operand parent(s) for +: 'Real Field with 30 bits
of precision' and 'Real ball field with 397 bits of precision'`, and so did
`rad / ball`. `rad()` and `mid()` return `RealNumber`s at low and full
precision respectively, and neither coerces into a ball field on its own;
wrap them, `RBF(ball.rad())`, before mixing.

What the skill says now: print the midpoint and the radius separately.

What it should say: the same, and that arithmetic between a radius and a
ball needs the radius wrapped in the ball field first.

Evidence: `/tmp/gs_probe3_out.txt` first run and `/tmp/gs_dry_out.txt`
second run, 2026-09-03.

## Ninety-two of the Gauss sums are $\sqrt{q}$ times a root of unity, and the draft prose had said none were

What happened: the proposal said the root number
$\varepsilon(\chi)=\tau(\chi)/(i^{\mathfrak a}\sqrt q)$ "is a root of unity
only for real $\chi$", and the first draft of the table's comments said so.
The dry run's sample comments showed $\tau(\chi_{16}(3,\cdot))$ and
$\tau(\chi_{16}(5,\cdot))$ both with minimal polynomial $x^8+65536$, that is
$4\zeta_{16}^k$. A check over every entry found 92 non-real characters
whose Gauss sum is $\sqrt q$ times a root of unity -- exactly those whose
component at every prime $p\mid q$ is quadratic or has conductor $p^e$ with
$e\geq 2$ (the explicit evaluation for prime-power moduli is in
Berndt-Evans-Williams), and none of the 348 others. The generator now
decides it per entry: $\tau^2/q$ lies in $\mathbb{Q}(\zeta_M)$, so it is a
root of unity only if its $z$-th power is $1$, $z$ the number of roots of
unity there; a ball for that power excluding $1$ proves it is not, and when
the ball allows it the exponent is read off the argument and confirmed
exactly. The comment then gives the root of unity, $4\zeta_{16}^{15}$.

What the skill says now: "Verify a claim before writing it into a table,
including one somebody suggested"; a pattern true for every small case
belongs in the generator as a check.

What it should say: the same, and that a statement of the form "for no
entry here" is a computation over every entry with a proof in each
direction -- a ball that excludes proves the negative, an exact identity
proves the positive -- and belongs in the generator, where the cases the
proposal did not foresee become entry comments instead of a false sentence.

Evidence: `/tmp/gs_probe4_out.txt` (the two $x^8+65536$ lines),
`/tmp/gs_probe5_out.txt` ("pure Gauss sums among the 440 non-real
characters: 46" found by the first version of the search, which missed the
odd ones by a sign, then 92 with the generator's test), 2026-09-03.

## A library's labelling of the objects is a claim: rebuild the Conrey character from its definition

What happened: the entries of the Gauss-sum table are indexed by the Conrey
label $(q,n)$, which Sage supplies as `chi.conrey_number()`. A wrong
labelling would publish right numbers under wrong identities, which
`verify()` cannot see. Conrey's definition is short -- discrete logarithms
to the least primitive root modulo each prime power, $(-1)^a5^b$ at $2$ --
and building $\chi_q(n,\cdot)$ from it by hand took forty lines; the two
constructions agreed on all 30882 values of every character of modulus at
most 60, primitivity decided by hand agreed with `is_primitive()`, and the
generator keeps the hand-built character as the one it sums, with Sage's
exact `gauss_sum()` as the check that must overlap. PARI's
`znchargauss(znstar(q,1), n)`, a third implementation of both the label and
the sum, agreed with all 470 values to 13 digits.

What the skill says now: "Never guess a name the database resolves";
nothing about a name a library resolves.

What it should say: when a parameter is a label some library assigns, the
label is part of the value and needs its own independent check -- build
the object from the label's definition, or compare two libraries that do
not share code -- because a table indexed by the wrong labels is wrong in a
way no recomputation of the values will find.

Evidence: `/tmp/gs_probe_out.txt`: "Conrey by hand vs Sage conrey_number:
q <= 60, 30882 values compared, 0 disagreements"; `/tmp/gs_probe5_out.txt`:
"PARI znchargauss ... 470 compared, failures []", 2026-09-03.

## `psi` is a PARI function, so a character called `psi` in a GP program is "variable name expected"

What happened: the PARI line offered under T143's `Programs` named its two
characters `chi` and `psi`, as the table's prose does, and running it through
Sage's `pari(...)` before writing it down raised `PariError: variable name
expected`. `psi` is GP's digamma function and cannot be assigned to; `chi`
can. The line went in with `chi1` and `chi2`, a comment saying why, and its
output beside it, after it had reproduced two entries to fifteen digits.

What the skill says now: run every program in `Programs` on at least one
entry that is not the first (a lesson above).

What it should say: the same, with this as the reason a name can fail: GP's
built-in function names (`psi`, `zeta`, `gamma`, `theta`, `eta`, `omega`)
are the letters a number theorist reaches for, and a program that assigns
to one is refused before it computes anything. The Sage line in the same
table is not affected, since `psi` is not bound under named imports.

Evidence: `/tmp/js_check_out.txt`, 2026-09-03, first run: the traceback
ending in `cypari2.handle_error.PariError: variable name expected`; second
run, `PARI program at (7,2,2): 0.500000000000000 - 2.59807621135332*I`.

## A value that is $\pm 1$ but lives in a bigger cyclotomic field carries a product out of the field whose basis you read

What happened: the quartic congruence $-\chi(-1)J(\chi,\chi)\equiv 1\pmod{2+2i}$
was checked in the generator by multiplying $J$, converted into
$\mathbb{Q}(i)$, by `-chi(-1)`, and reading off $a+bi$ from
`.polynomial().padded_list(2)`. It passed at $p=5$ and failed at $p=13$
with "$3+0i$": Sage's `chi(-1)` is an element of the character's base ring
$\mathbb{Q}(\zeta_{12})$, the product landed there, and the first two
coefficients of $3+2\zeta_{12}^3$ in the $\zeta_{12}$ basis are $3$ and
$0$. Taking `ZZ(chi(-1))` first keeps the product in $\mathbb{Q}(i)$, and
the check then passed for every quartic character to $p=19$.

What the skill says now: "Expect the machinery to be missing"; nothing
about machinery that silently changes the parent of a product.

What it should say: coefficients read off a number-field element are in
the basis of *its* parent, and Sage's coercion sends a product to the
larger of the two fields without a word; before reading coefficients,
convert every factor that is rational to `ZZ` or `QQ`, and assert the
parent of the element you read from is the field you think it is. The
signature is a check that passes at the first prime, where the two fields
coincide, and fails at the second.

Evidence: `/tmp/js_dry_out.txt`, 2026-09-03, first run: `ArithmeticError:
(13, 5, 5): quartic -chi(-1) J = 3 + 0 i is not 1 mod 2 + 2i`; second run
clean.

## An exact-value comment on every entry can outweigh the value; measure the block with the comments before choosing the range

What happened: the proposal for the Jacobi sums estimated "592 entries at
100 digits plus a short exact comment: about 140 KB" for $p\leq 23$. The
comment holds the exact value in $\mathbb{Z}[\zeta_d]$, which at $p=23$
has up to ten terms and 219 characters, longer than the hundred-digit
value beside it. Written out through `to_text` and `yaml.dump` (what the
server measures), $p\leq 23$ is 237 KB and $p\leq 19$ is 139 KB, so the
range stopped at $19$ with 372 entries, under the 160 KB the skill asks a
table to stay below. `dry_run.py`'s own figure (166 KB at $p\leq 19$) is
the ball's printed form and overstates a table of balls, as the environment
notes already say; the wrapper measured the written form.

What the skill says now: "A comment on every entry is part of the entries
block", with a 166 KB versus 152 KB example; and "aim at half the soft
block limit".

What it should say: the same, and that for a comment carrying an exact
algebraic value the comment's length grows with the parameter as fast as
the value's or faster, so an estimate made from the values alone is wrong
by the comments; measure the block as written, with the comments, at each
candidate range, and choose from that table of numbers rather than from
the entry count.

Evidence: `/tmp/js_dry_out.txt`, 2026-09-03: `p <= 19: 372 entries, longest
value 213 ..., longest comment 157, block 139.4 KB as written`; `p <= 23:
592 entries, ..., longest comment 219, block 237.2 KB as written`.

## An in-page `HREF{#label}` is an entry address, not an anchor; cite a Links entry with `CITE{label}` or not at all

What happened: T142 and T143 wrote the parameter titles as
`HREF{#CL}[Conrey index]`, meaning to jump to the Conrey knowl in Links.
The site reads every `HREF` target of the form `#x` as the address of the
entry whose parameters are `x`, so the link became `?entry=CL`, the server
found no entry called CL, and the page reloaded with a yellow "This table
has no entry CL" warning at the top. `audit_table` resolved the link and
said nothing, because a same-table `#x` is a legal entry address.

What the skill says now: `HREF{Table#params}` addresses an entry, and
`CITE{label}` a Links, References or Formulas entry; nothing about a bare
`#label`.

What it should say: `HREF{#x}` always means "entry x of this table" and
nothing else; a Links or References entry is reached with `CITE{label}`,
which renders as its bracketed number and scrolls to it. If the thing a
title wants to link to is cited one line away in the Definition, the title
needs no link.

Evidence: `agents/critiques/T143.md`, finding 1; `/T143?entry=CL` rendered
in the throwaway, 2026-09-03; `numberdb_app/views.py`, `_reference_href`.

## A `comments` field under a parameter is stored and never shown; put the prose in Comments

What happened: T142 and T143 gave each parameter a `comments` key -- why
$p=5$ is the first prime, why $mn\not\equiv 1$, what the order of
$\chi_p(m,\cdot)$ is. The API accepted it, the document stored it, the
generator's `table.yaml` mirrored it, and no reader ever saw a word of it:
the parameter line on the page is built from `title`, `display` and
`constraints` only, and the field is not read anywhere else. The one
thing the Definition does not explain in a reader's terms, the reason for
a constraint, was in the dark field.

What the skill says now: the parameter keys `type`, `title`, `display`,
`constraints`, `values`, `show-in-parameter-list`; nothing forbidding
others, and the validator lists `comments` among annotations it knows.

What it should say: a parameter has `type`, `title`, `display` and
`constraints`, and an explanation of a constraint is a comment in Comments;
any other key under a parameter is silently kept and silently not shown.
After writing a table, read the rendered page for every sentence you wrote
and find where it landed.

Evidence: `agents/critiques/T143.md`, finding 2; `numberdb_app/views.py`
around line 735; `numberdb_app/validate.py`, `KNOWN_ANNOTATIONS`.

## Sage's `kloosterman_sum` is an exact independent route for classical Kloosterman sums, and its base ring decides the cost

What happened: the Kloosterman-sum table (T144) needed a second computation
sharing no code with the arb sum from the definition. Sage has one:
`DirichletCharacter.kloosterman_sum(a, b)` returns the twisted sum
$\sum_x\chi(x)\zeta^{ax+b\bar x}$ exactly, and for the trivial character it
is the classical $K(a,b;p)$. Which field it lands in depends on the
character's *base ring*: `trivial_character(p)` has base ring $\mathbb{Q}$,
zeta order $2$, and the sum comes back in $\mathbb{Q}(\zeta_{2p})$, degree
$p-1$, in milliseconds for $p=71$; the trivial character taken from
`DirichletGroup(p)` has base ring $\mathbb{Q}(\zeta_{p-1})$ and the same
call works in $\mathbb{Q}(\zeta_{\mathrm{lcm}(p,p-1)})$, degree $1680$ at
$p=71$, which is what made the Gauss-sum transform check take 111 s at that
prime. `kloosterman_sum_numerical(prec, a, b)` is a third route, floating,
for a sanity check.

What the skill says now: "check new values against something independent";
nothing about where Sage keeps its exponential sums.

What it should say: for a character sum, look in `sage.modular.dirichlet`
first -- `gauss_sum`, `jacobi_sum`, `kloosterman_sum` are exact and
independent of any hand-written sum -- and build the character over the
smallest base ring that holds its values, because the answer's field, and
the cost of every operation in it, follows from that ring.

Evidence: `/tmp/kl_probe_out.txt`, 2026-09-03: "parent of exact sum:
Cyclotomic Field of order 10 and degree 4" at $p=5$; "p = 71: balls and
exact sums for all a in 1.3 s" against "Gauss transform for all 70
characters in 111.0 s".

## A type `C` table may store a real value with no imaginary part; a reader of stored digits must accept both spellings

What happened: the read-back check of T144 parsed the `equals` targets in
T35 (Algebraic numbers of degree 2, type `C`) with a splitter expecting
`a + i * b`, as T142 and T143 write every value. T35 writes its real roots
as a bare real, `0.38196601125010515...`, and the check died with "not
enough values to unpack". The same parser had worked on T142, whose real
Gauss sums are written `0 + i * 1.73...` because the generator made them
so.

What the skill says now: type `C` is "written as `0.309... + i * 0.951...`".

What it should say: a complex-typed table may also hold a bare real, and a
script that reads stored complex digits back should accept both forms.
(And a small arb trap met in the same script: a `RealBall` times a Python
`float` raises `TypeError`; write the constant as a ball or a rational,
`R(6) / R(10)**k`.)

Evidence: `/tmp/kl_stored_out.txt`, first run, 2026-09-03; T35's entry
`1,-3,1` -> `1` in `api/table?id=T35`.

## A "table wanted" issue with a title and no body is a decision to record, not a convention to guess

What happened: numberdb-data #13 is the title "Kloosterman sums of
Dirichlet characters" and nothing else. Read literally it asks for the
twisted sums $\sum_x\chi(x)e((ax+b\bar x)/p)$, which are complex for a
nontrivial $\chi$ and would make a type `C` table in which every classical
sum is written with a zero imaginary part and cannot be found by its real
digits. The proposal had argued for the classical (trivial-character) sums
as their own real table; the build followed it, because the definition of
$K(a;p)$ is unambiguous and independently checkable, and wrote the reading
of the issue into a comment that cites it, so a reviewer can disagree in
one place.

What the skill says now: cite the issue in References; nothing about an
issue that does not settle its own scope.

What it should say: when the issue leaves the family's scope open, choose
the reading with the unambiguous definition, say in a comment which reading
was taken and why, and cite the issue there; the other reading, if wanted,
is a second table, not a parameter added later.

Evidence: `gh issue view 13 -R numberdb/numberdb-data --json body` ->
`"body": ""`; T144's comment on the twisted sums, 2026-09-03.

## An identity copied from a source in a special case may hold in general; check the general form before writing the special one

What happened: T144 stated the Legendre-symbol form of the Kloosterman sum
as $K(a^2;p)=\sum_m\left(\frac{m^2-4a^2}{p}\right)e(m/p)$, because that is
how Wikipedia writes it (as $K(a,a;p)$), and the build's check tested
exactly that, so the rigour sentence "checked by brute force at every prime"
was true and covered half the table. The identity is
$K(a,b;p)=\sum_m\left(\frac{m^2-4ab}{p}\right)e(m/p)$ for $p\nmid ab$
(Iwaniec–Kowalski), so it holds for every $a$, square or not; the repair
checked all 616 $(p,a)$ in balls, with the sign of $4a$ reversed as the
control, and rewrote the formula.

What the skill says now: check every identity over the whole range before
writing it down.

What it should say: when a source states an identity in a special case,
try the general parameter before writing the special case down; a formula
scoped narrower than the truth sends a reader to look for a restriction
that is not there. And a check tests the statement as written, so a
narrowed statement makes a narrowed check look complete.

Evidence: `/tmp/repair144_check.py` and its output, 2026-09-03: 616 cases,
308 with $\left(\frac{a}{p}\right)=-1$, no exception; control fails.

## cypari2 computes at 64 bits unless `precision=` is passed in bits; `set_real_precision` only prints

What happened: the outside check of the Dirichlet $L$-values handed each
character to PARI as its Conrey label, `pari.lfun(pari.lfuncreate([pari.znstar(q, 1), n]), s)`,
after `pari.set_real_precision(120)`, and every one of 501 entries
"disagreed" with the arb sum by $10^{-20}$ to $10^{-19}$ -- the printed
PARI value was twenty digits followed by a hundred zeros. From Sage,
`set_real_precision` sets how a result is printed and how a literal is
read; a function's working precision is its `precision=` keyword, in
bits, and the default is 64. With `precision=420` all 501 agree to
$10^{-110}$. The first run of this check, a day earlier, had recorded the
same $10^{-20}$ differences as "PARI failures" without finding the cause.

What the skill says now: "a field was built in digits where Sage counts
bits" for the package's own refusal; nothing about PARI from Sage.

What it should say: when PARI is the independent computation, pass
`precision=<bits>` to the function itself, and treat agreement to exactly
19 digits as the default precision showing, not as a disagreement. A
disagreement that is the same size on every entry is a precision setting.

Evidence: `/tmp/lv_check_out.txt`, 2026-09-03, first run: "largest
|difference| upper bound 2.03e-19", 501 FAIL lines each ending in
`...0000 +/- 1.01e-110`; second run with `precision=PARI_BITS`: "largest
|difference| upper bound 1.41e-110". T145's rigour details quote the second.

## A title with a lone letter in math loses that letter from its slug

What happened: `slug_for('Values of Dirichlet $L$-functions at positive integers')`
answered `Values_of_Dirichlet_-functions_at_positive_integers`: the slug
drops mathematics, as the skill says, and here the mathematics was one
letter of a hyphenated word. T4's title, "Zeros of Dirichlet L-series",
is plain, and the new table's title was made plain before the draft was
created, so its address is `Values_of_Dirichlet_L-functions_at_positive_integers`.

What the skill says now: "mathematics is dropped from" the slug, under
never guessing an address.

What it should say: the same, with the consequence for a title: a symbol
that is part of a word -- `$L$-function`, `$p$-adic`, `$j$-invariant` --
is dropped from the address and leaves `-function` behind. Write such a
letter plain in the Title (the corpus already does: T4, T52) and keep the
math for the Definition; and read `slug_for`, or the creation answer's
`url`, before linking to a table one has just named.

Evidence: `/tmp/lv_drafts.py` output, 2026-09-03, the two `slug for the
new title` lines; the creation answer `url = Values_of_Dirichlet_L-functions_at_positive_integers`.

## A type `C` table may store an exact rational too; a reader of stored values takes three spellings

What happened: the read-back check of T145 rebuilt the closed form
$L(s,\chi)=(-1)^{s-1}\frac{\tau(\chi)}{2}(\frac{2\pi i}{q})^s\frac{B_{s,\bar\chi}}{s!}$
from the stored digits of two other tables, and died on T49's entry
$(3,2,1)$: the generalized Bernoulli numbers, type `C`, store
$B_{1,\chi_{-3}}=-1/3$ as the string `-1/3` beside neighbours written
`-0.600... + i * -0.200...`. The parser had learned the earlier lesson
(a bare real or `a + i * b`) and not this one.

What the skill says now: "A string with no `.` and no `e` is an exact
integer, not an approximation"; and the lesson above that a type `C`
table may hold a bare real.

What it should say: a value with no `.` and no `e` is exact and may be a
rational with a `/`; so a script reading a `C` or `R` table back accepts
an exact integer or rational, a bare decimal, and `a + i * b`, and
`QQ(text)` rather than `ZZ(text)` is the right first attempt.

Evidence: `/tmp/lv_check_out.txt`, 2026-09-03, second run:
`TypeError: unable to convert '-1/3' to an integer`; third run, "40
entries rebuilt from two other tables".

## Print the special-cased entries in the dry run; a name attached in the wrong branch is invisible to every numeric check

What happened: the L-value generator names Catalan's constant on the
entry $L(2,\chi_4(3,\cdot))$ through a small table of names, and the line
that appended the name sat inside the branch for matching parity -- which
that entry does not have, since $\chi_{-4}$ is odd and $s=2$. Every ball
was right, `exactness`, `verify` and the outside checks all pass with or
without the name, and the only thing that showed it was the dry-run
wrapper printing the comments of a chosen list of entries: `(4, 3, 2): ...
odd |` with nothing after. The same list showed `$L(s,1)=\zeta(s)$$=\pi^2/6$`,
two comment fragments joined with their dollars touching, which the
earlier lesson on assembled comments describes.

What the skill says now: check the values against something independent;
nothing about checking the annotations.

What it should say: the dry run should print, for every entry that a
generator treats specially -- a named value, a closed form, an `equals`
link -- the comment and the link as they will be stored, and the builder
should read them, because no check of the numbers can see a comment that
was never attached. Keep the list of such entries in the generator
(`NAMED`, the `equals` table) so the wrapper can print exactly those.

Evidence: `/tmp/lv_dry_out.txt`, 2026-09-03, "sample entries" block, the
`(1, 1, 2)` and `(4, 3, 2)` lines; commit 4a295d4 moved the name out of
the branch.

## Backticks in prose are printed as backticks

What happened: T145's rigour paragraph wrote "PARI's `lfun`", and the
rendered page shows the two backtick characters around the word. The
site renders `$...$`, `CITE{}` and `HREF{}` and nothing else; there is
no Markdown pass. T142's first critique found the same thing three
times in its rigour paragraph, and its repair removed them; after that,
T145 is the only table in the repository with a backtick outside a
`code:` block. A reader takes it for a typo.

What the skill says now: "Use `$...$` for mathematics, `CITE{key}` for
a reference or link, and `HREF{slug}[caption]` for a table here."
Nothing says that these are the only markup and that backticks, `**`
and the rest of Markdown come out as characters.

What it should say: that sentence, with "and nothing else: a backtick
or a `**` in prose is printed as typed. Name a function in words,
'PARI's lfun', 'Sage's exact Gauss sum', as the same paragraph names
everything else."

Evidence: `/tmp/crit145.html`, 2026-09-03, "agrees with PARI's `lfun`
at $120$ digits"; `grep '`' generators/*/table.yaml` outside `code:`
blocks finds only this line; `agents/critiques/T142.md` finding 1.

## Name a linked table by its title, not by a paraphrase of it

What happened: T145's Similar tables links `Zeros_of_Dirichlet_L_functions`
with the caption "Zeros of Dirichlet $L$-functions". The address is
right and the page answers, but the table's title is "Zeros of
Dirichlet L-series". A reader who clicks lands on a page whose title is
not what they clicked, and one who searches the corpus for the caption
they read finds nothing. The slug is not the title with underscores
(the skill says so at "HREF{...} takes the slug"), and a caption
reconstructed from the slug is a guess at the title. `audit_table`
checks that the slug resolves; it does not compare the caption with the
title.

What the skill says now: `HREF{slug}[caption]`, and that the slug is
not the title with underscores. Nothing about the caption.

What it should say: in Similar tables, the caption is the target's
title as the site prints it, copied from `numberdb.table(tid).title` or
the page; in running prose the caption may be a phrase ("the zeros of
$L(s,\chi)$"), and then it should read as a description and not as a
title.

Evidence: `curl` of `https://numberdb.org/Zeros_of_Dirichlet_L_functions`,
2026-09-03: `<title>Zeros of Dirichlet L-series - NumberDB</title>`;
T145 Similar tables row 4; `agents/critiques/T145.md` finding 3.

## PARI's `polsubcyclo(p, k)` is the Gaussian period polynomial itself, and its answer needs `Vecrev()` to become a Sage polynomial

What happened: the table of Gaussian period polynomials (T146) needed a
second exact computation sharing no code with the product over the periods
in Sage's cyclotomic field. PARI's `polsubcyclo(p, k)` gives a polynomial
defining the subfield of degree $k$ of $\mathbb{Q}(\zeta_p)$, and on all
158 rows it returned $\prod_j(x-\eta_j)$ itself, coefficient for
coefficient, not merely a polynomial for the same field -- so it is the
independent route for this family, the way `kloosterman_sum` was for T144.
Two things on the way: `PolynomialRing(ZZ, 'x')(pari.polsubcyclo(p, k))`
died with `PariError: incorrect priority in gtopoly: variable x <= x`
(Sage's conversion calls `Polrev` on a polynomial already in `x`), and the
answer came back as a one-element `t_VEC` rather than a bare `t_POL`, so
`ZZ(c) for c in g.Vecrev()` was handed the whole polynomial. Unwrapping a
length-one vector and building the Sage polynomial from `Vecrev()` of the
`t_POL` works; the generator refuses a vector of any other length.

What the skill says now: check against something independent; the T144
lesson says to look in `sage.modular.dirichlet` for character sums.

What it should say: for a family of polynomials defining abelian fields,
PARI's `polsubcyclo` (and `polcyclo`, `polclass`) is an exact second
computation one call away; and a PARI polynomial reaches Sage's `ZZ[x]`
through its coefficient vector, not through the ring's constructor.

Evidence: `/tmp/gp_probe_out.txt`, 2026-09-03, the two tracebacks and then
`'pari': 158` in the counts; the control `(7,3) vs polsubcyclo(7,2): False`.

## A field discriminant has a sign; a "square times $p^{k-1}$" check fails on exactly the imaginary rows with $k\equiv 2\pmod 4$

What happened: the check that $\operatorname{disc}\Psi_{p,k}$ is
$p^{k-1}$ times a perfect square failed on 39 of 158 rows: every row with
$f$ odd and $k=2, 6, 10$, and no other. The subfield of degree $k$ is
totally imaginary when $f$ is odd, so its discriminant is
$(-1)^{r_2}p^{k-1}$ with $r_2=k/2$, negative when $k\equiv 2\pmod 4$; the
polynomial's discriminant is that times the square of the index of
$\mathbb{Z}[\eta_0]$. With the sign in, all 158 pass, and the index turned
out to be $1$ on 57 rows only, so the tempting sentence "the periods
generate the ring of integers" was never written.

What the skill says now: "A control that vanishes by symmetry is not a
control", with the parity signature of a checker wrong on exactly the odd
or exactly the even orders.

What it should say: the same signature in a new shape: a check that fails
on a clean congruence class of the parameter (here $k\equiv 2\pmod 4$ and
$f$ odd) is the checker missing a sign or a unit, not the table; write the
statement with the sign it has in the theorem before running it.

Evidence: `/tmp/gp_probe_out.txt` first run, the 39 `('disc', p, k, D)`
failures all with negative $D$; `/tmp/gp_probe_out2.txt`, `'disc_square':
158`, `index 1 count 57`.

## A proposal's entry count is a claim to recount before the complete-note quotes it

What happened: the proposal said "$p<200$, $2\leq k\leq 12$: 163 entries".
The generator enumerates 158. The five missing are $(3,2)$, $(5,4)$,
$(7,6)$, $(11,10)$, $(13,12)$: the rows with $k=p-1$, which the same
proposal excludes because they are $\Phi_p$. The count had been made
before the exclusion was decided, and the complete-note would have said
163 had it been copied.

What the skill says now: the complete-note says what is here; nothing
about where its number comes from.

What it should say: the number in the complete-note is the number the dry
run printed, never the proposal's; and the same for any count a comment
quotes (the T139 lesson on "137 of the 249 knots" is the same lesson from
the other side).

Evidence: `BATCH-2026-09-03T1011.md`, proposal 5, "163 entries";
`/tmp/gp_dry_out.txt`, `158 entries computed`.

## An OEIS b-file can be shorter than its link says, and a product of roots is the constant term up to $(-1)^k$

What happened: OEIS A394567's `%H` line offers "Table of n, a(n) for
n = 1..10000", and the file served at `/A394567/b394567.txt` begins
`# A394567 (b-file synthesized from sequence entry)` and holds 54 terms --
the terms of the entry itself, which is what the check compared with.
Enough for the 21 primes $p\equiv 1\pmod 3$ below 200, and not the ten
thousand a later extension of the table might have counted on. And the
proposal had said the constant terms of the cubic rows "are" A394567; the
sequence is the product of the three periods, which is $-\Psi_{p,3}(0)$
for a cubic, and the check is on the negative.

What the skill says now: search OEIS for a polynomial family's
coefficient triangle; a b-file is the strongest independent evidence.

What it should say: read the first line of a b-file before counting on its
length, and a sequence named as a product or sum of roots is a coefficient
up to the sign $(-1)^{\deg}$, which the check states explicitly.

Evidence: `head -2 /tmp/gp_b394567.txt`, 2026-09-03; `'oeis_cubic': 21`
in `/tmp/gp_probe_out2.txt` with `P[0] == -b394567[i]`.

## `NumberField.galois_group(type='pari')` is refused by the Sage behind `sage -python`; call it with no argument

What happened: the T146 repair wanted the Galois group of the field a
period polynomial defines, to check that it is abelian before writing the
word. Older documentation and answers show `K.galois_group(type='pari')`;
on this Sage (Python 3.12 venv) it fails with `TypeError:
NumberField_generic.galois_group() got an unexpected keyword argument
'type'`, and the cached-method wrapper prints a `KeyError` on the
arguments first, which hides the cause. `K.galois_group()` with no
argument returns a group with `is_abelian()` and `order()` and answers in
a second for degree 12. For a relative extension `L = K.extension(f, 'a')`
the same question is `L.automorphisms()`: it lists the $K$-automorphisms,
so the extension is Galois over $K$ when there are `f.degree()` of them,
and abelian when they commute on `L.gen()`.

What the skill says now: nothing about Galois groups.

What it should say: a claim that a polynomial defines an abelian or Galois
extension is one Sage settles in a line, `NumberField(f).galois_group()
.is_abelian()` over $\mathbb{Q}$ and `len(L.automorphisms())` over a base
field; do not pass `type=`, which is gone.

Evidence: `/tmp/repair146_check.py`, 2026-09-03: first run died on the
keyword, the second answered sixteen checks and a control that fails as it
must.

## Kissing numbers come from PARI's `qfminim`, not from `IntegralLattice.short_vectors`

What happened: the lattice batch needed the number of minimal vectors of
each root lattice as the control that a Gram matrix is the lattice it is
claimed to be. `IntegralLattice(CartanMatrix(['E', 8])).minimum()` answers
$2$ at once, but `.short_vectors(2)` raised `IndexError: list index out of
range` on every root lattice tried, and the first run printed `ERR` in
the kissing-number column of every row. `pari(G).qfminim(m, None, 0)`
returns `[count, max, vectors]` with `count` the number of vectors of norm
$\leq m$ counting both signs -- $240$ for $E_8$, $196560$ for the Leech
lattice in 11 s -- and the third component is the vectors themselves,
which the Voronoi-cell computation then takes as its half-spaces.

What the skill says now: nothing about lattices.

What it should say: for a lattice given by a Gram matrix, `minimum()` is
Sage's and the vector count is PARI's `qfminim`; `short_vectors` is not
reliable at the minimum. A kissing number that matches OEIS A001116 or
A002336 is the cheapest proof that the right Gram matrix was read.

Evidence: `/tmp/lat_probe.py` (the `ERR list index out of range` column)
and `/tmp/lat_probe2.py` (`kiss (240, 2)`, `Leech kiss (196560, 4)`),
2026-09-03.

## Sage has no Leech lattice; build it from `GolayCode` in twelve lines

What happened: the lattice batch wanted $\Lambda_{24}$ and $BW_{16}$ as
Gram matrices, and Sage has neither as an object. Both are a
$\mathbb{Z}$-span in Sage: for the Leech lattice, $2c$ for the rows of
`GolayCode(GF(2), extended=True).generator_matrix()`, $4e_1 + 4e_j$,
$8e_j$ and $(-3, 1, \ldots, 1)$, then `span(gens, ZZ).basis_matrix()`,
Gram matrix $BB^{T}/8$: determinant $1$, minimum $4$, $196560$ minimal
vectors. For $BW_{16}$, the rows of `ReedMullerCode(GF(2), 1, 4)`,
$2(e_1 + e_j)$, $4e_j$, Gram matrix $BB^{T}/2$: determinant $256$, minimum
$4$, $4320$ minimal vectors. The whole thing runs in a second (plus the
11 s for counting the Leech vectors).

What the skill says now: nothing.

What it should say: a lattice defined from a code is a `span` over
$\mathbb{Z}$ of the lifted generators, and the determinant, minimum and
kissing number of the result are the check that the construction is the
lattice named -- all three are on the Nebe-Sloane catalogue page for it.

Evidence: `/tmp/lat_probe2.py`, 2026-09-03: `BW16 det 256 min 4 kiss
(4320, 4)`, `Leech det 1 min 4`, `Leech kiss (196560, 4)`.

## OEIS: one entry by id is `search?q=id:A222072&fmt=json`, not `A222072?fmt=json`

What happened: the run fetched twenty-six OEIS entries by
`https://oeis.org/A222072?fmt=json` to read their names and got an empty
answer for every one, which looked like the sequences did not exist.
`https://oeis.org/search?q=id:A222072&fmt=json` returns the entry, with
`name` and `data`, and `search?q=<words>&fmt=json&n=30` returns up to
thirty matches. The 55-digit comparisons in the lattice batch were made
from the `data` field so obtained.

What the skill says now: OEIS is a link target and a place to look for a
coefficient triangle.

What it should say: how to ask it -- the `search` endpoint with `id:` for
one entry and `fmt=json` for something a script can read; a decimal
expansion's `data` field is the digits, comma-separated, without the
decimal point, and the `offset` field says where the point goes.

Evidence: the empty loop over `A222060`-`A222085` and the `id:` fetches
that followed, 2026-09-03.

## PARI's `qfisom` enumerates every vector up to the largest diagonal entry, so a Gram matrix with an $8$ on its diagonal never finishes

What happened: the lattice-density build wanted an isometry between the
Leech lattice built from the Golay code and the catalogue's `GRAM` block
for it, as the check that the transcribed block is the lattice named.
`pari(G1).qfisom(pari(G2))` on the $\Lambda_{16}$ blocks (diagonal $4$,
$4320$ vectors of norm $4$) answers at once; on the Leech blocks it ran
until the run was killed at twenty minutes, because the catalogue's block
has an $8$ on its diagonal and Plesken–Souvignier's algorithm begins by
listing every vector of norm up to the largest diagonal entry -- about
$4\cdot 10^{8}$ for norm $8$ in the Leech lattice. Conway's uniqueness
theorem did the job in a second: an even unimodular lattice of dimension
$24$ with no vectors of norm $2$ is the Leech lattice, so checking "even,
determinant $1$, minimal norm $4$" on each Gram matrix proves both are it.

What the skill says now: nothing about isometry tests.

What it should say: before `qfisom`, LLL-reduce both forms (`qflllgram`) so
the diagonal is as small as the minimum allows, and prefer a
characterisation theorem where one exists -- for the Leech lattice, for
$E_8$ (the even unimodular lattice of dimension $8$), for the root
lattices by their Cartan matrices. An isometry test whose cost you have not
measured on the largest lattice is the loop the T142 note warns about.

Also met on the way: with the lattice built as `span(gens, ZZ)` of
`vector(ZZ, ...)` rows, three later runs sat in a *second* `qfminim` on
the same 24-dimensional Gram matrix until they were killed, each with the
first call having answered in seconds, and the cause was not pinned;
`vector(ZZ, list)` itself raises `ImportError: cannot import name
PolynomialSequence_generic` in a script that has not imported anything
else, because it reaches for Singular through `Sequence`. The version that
passes in four seconds builds the generators as plain lists, takes the
nonzero rows of `matrix(ZZ, gens).echelon_form()` as the basis, calls
`qfminim` once per matrix and deletes its answer (98280 vectors) before
the next. For $\Lambda_{16}$, LLL-reduce both Gram matrices with
`qflllgram` (diagonal $4$ after, $8$ before) and `qfisom` answers at once.

Evidence: `/tmp/lp2_check_out.txt`, 2026-09-05, first run: killed at
`NUMBERDB_TIMEOUT=1200` inside `qfisom`; `/tmp/lp2_codes_out.txt`: the
list-built version, `10 PASS, 0 FAIL` with every step stamped under four
seconds.

## The catalogue's twelve-digit lines carry nine digits sometimes; compare a printed value at the precision it actually has, and read its `GRAM` header

What happened: the Nebe–Sloane catalogue pages print `DET`,
`MINIMAL_NORM`, `KISSING_NUMBER` and, on most pages, `HERMITE_NUMBER` and
`DENSITY` as twelve-significant-digit floats (`.230940107676E+01`). A check
at $10^{-11}$ relative passed eleven of the fourteen Hermite lines and
failed $\Lambda_{13}$, $\Lambda_{20}$ and $\Lambda_{22}$, whose lines are
off in the ninth or tenth digit (two of them end in `600`, a nine-digit
value padded to twelve). The value is a formula in two integers the same
page states, and arb and plain floats agree with each other to fifteen
digits, so the lines are wrong and are recorded in `docs/external-bugs.md`;
the check was loosened to $10^{-8}$, which still proves the right matrix
was read. Also: a page's `GRAM` block starts with a header line, `n 0`
before a lower triangle and `n n` before a full matrix, and the Leech page
wraps its full $24\times 24$ matrix over 48 lines, so a parser has to read
the header and re-chunk the numbers rather than trust the line breaks.

What the skill says now: "check new values against something independent".

What it should say: a source's printed digits are a check only to the
precision the source really has, and a source can print more digits than
it knows; when a line fails by $10^{-9}$ against a value that is exact
arithmetic in the page's own integers, suspect the line, recompute it two
ways, and write it to `docs/external-bugs.md` rather than loosening the
check silently.

Evidence: `/tmp/lp2_check_out.txt`, 2026-09-05, the three `FAIL catalogue
LAMBDAnn HERMITE_NUMBER` lines and the float recomputation beside them
(`rel diff 4.59e-09, 1.77e-10, 2.40e-10`); `/tmp/lp2_src/catalogue.json`.

## `yaml.dump` sorts keys unless told not to, and the order of `Parameters` is the identity of the columns

What happened: the 2026-09-05 build of T147 fixed its Definition by
re-sending the whole document, built as the repository's `table.yaml` plus
the stored `Numbers`, through `yaml.dump(document, allow_unicode=True,
default_flow_style=False, width=1000)`. PyYAML's `sort_keys` defaults to
`True`, so every mapping arrived alphabetical: `Comments` first, formulas
`duals, hermite-constant, laminated, relations, root-lattices`, dimensions
as strings (`1, 10, 11, …, 19, 2, 20`), and `Parameters` as
`expression, family, n` while the `Numbers` block stayed nested
`family, n, expression`. The server stored it as sent and said nothing;
`audit_table` said nothing. On the page the column headers moved one
column right (an empty header over the family, "family" over the
dimension, "n" over `centre/density/hermite`), the `values` displays of
the Symbolic parameters stopped applying because the view looks each
level up under the parameter at that position, and the formulas were
renumbered. The critique, not any check, found it
(`agents/critiques/T147.md`).

What the skill says now: nothing about key order on a whole-document
write; the client's own `_write.py` passes `sort_keys=False`.

What it should say: the order of the `Parameters` mapping is the order of
the levels of `Numbers`, and the order of every mapping is what the page
shows; a document sent by hand must be dumped with `sort_keys=False`
(`yaml.dump`) or `sort_keys=False` (`json.dumps` is already unsorted).
After any whole-document write, look at the header row of the rendered
numbers block, which is where a reordering shows first.

Evidence: T147 revisions 1–3 in author order, revision 4
(`ec53c632…`, 2026-09-05 09:19 UTC) sorted; `/tmp/lp2_write_doc.py`,
`/tmp/crit147_hist.py`, `/tmp/crit147_params.py`.

## A table of "best known" values needs a literature check dated after its source; zbMATH's year filter is enough

What happened: the densest-lattice-packings table takes its records from
the Nebe–Sloane table of February 2012, and the proposal asked the builder
to check "Cohn's survey of records" before writing. That page
(`cohn.mit.edu/sphere-packings`) is gone, and web search is not available
to a run. `curl 'https://zbmath.org/?q=ti%3A"sphere+packings"+%26+ti%3Anew+%26+py%3A2013-2026'`
and three queries like it, read from the `<article>` blocks, found in a
minute what mattered: Chen, Hu, Li, Wang and Wu, *New sphere packings from
the antipode construction* (arXiv:2505.02394), nonlattice packings denser
than the lattice records in dimensions 19, 21, 23 and than the 2012
nonlattice records in 20, 44, 45, 47; and Dutour Sikirić and van Woerden,
*The lattice packing problem in dimension 9 by Voronoi's algorithm*
(arXiv:2508.20719), which proves $\Lambda_9$ optimal among lattices. Neither
changed an entry; both changed what the comments may claim, and a table
saying "a denser packing is not known" in dimension 19 would have been
wrong on the day it was offered.

What the skill says now: "Verify a claim before writing it into a table";
nothing about a claim whose truth has a date.

What it should say: a value defined as "the best known" carries the date of
its source, and the table must say that date and be checked against the
literature after it. zbMATH answers a title-word query with a `py:` year
range through plain `curl`, arXiv abstracts answer too, and a PDF from
arXiv reads with `pdftotext`; that is a literature check a contributor can
do from a laptop without a search engine. Write the newer result into the
comment beside the older one rather than replacing it, since the older
packing is still the one the cited table names.

Evidence: `/tmp/dl_zb/rec3.html`, `/tmp/dl_zb/rec4.html`, `/tmp/dl_arxiv_antipode.html`,
`/tmp/dl_arxiv_dim9.html`, 2026-09-05; the `NONLATTICE` and
`OPTIMAL_LATTICE` tables of `generators/densest-lattice-packings/generate.py`.

## A printed decimal has a precision and a rounding rule, and a catalogue GRAM block may be printed as floats

What happened: three sources gave the same centre densities to a few
digits and each rounds differently. The catalogue's density page prints
five decimal places (`0.03608` for $0.0360844$), so a value below $0.1$ has
four significant digits and a check at five fails; Cohn's Table 1 says its
numbers are "rounded down" and they are; the 2025 antipode paper prints
`0.50049 . . .`, which reads as truncation, and six of its seven values are
rounded to nearest (the true value $0.5004897$ is below the printed one).
A check written as "the value lies in [printed, printed + ulp)" failed six
times on right values. Separately, the catalogue's `GRAM` block of
`KAPPA11` is written as `.400000000000E+01` where `KAPPA13`'s is `4`, and
`int()` on it raised.

What the skill says now: compare a printed value at the precision it
actually has (lesson above); read the `GRAM` header.

What it should say: before comparing, settle three things about a printed
number: how many places it has (not digits), whether it is rounded to
nearest or down, and whether an ellipsis after it means truncation -- and
if the source does not say, test at half a unit either way and report which
rule fit. A catalogue block's entries are floats or integers page by page;
parse them as floats and require integrality rather than calling `int()`.

Evidence: `/tmp/dl_check_out.txt`, 2026-09-05: the six `FAIL n=..: antipode
delta ... within one unit` lines followed by `ValueError: invalid literal
for int() with base 10: '.400000000000E+01'`; the local recomputation with
`diff/ulp` between $-0.36$ and $+0.37$ for all seven.

## Count a lattice's minimal vectors with PARI's `qfrep`, which stores none of them; `qfminim` on 261120 vectors is a memory problem

What happened: the check that a catalogue GRAM block is the lattice it is
named after compares the number of minimal vectors with the page's
KISSING_NUMBER line. `pari(G).qfminim(None, None, 0)` returns every vector
and worked for the Leech lattice (196560 vectors, 24 coordinates) and for
$\Lambda_{25}$ and $\Lambda_{26}$; on Quebbemann's $Q_{32}$ (261120 vectors
of 32 coordinates) the process was killed. `qfrep(G, b)` returns half the
number of vectors of each norm $1,\ldots,b$ and keeps no vector: LLL-reduce
first (`qflllgram`), then `qfrep(Gr, 6)` gave $[0,0,0,0,0,130560]$ for
$Q_{32}$ in three seconds and $[0,\ldots,0,119799]$ for $KP_{36}$ (norm 8,
239598 vectors) in twenty-three, which is the minimal norm and the kissing
number in one call and the proof that nothing shorter exists.

What the skill says now: the lattice lesson above says kissing numbers come
from `qfminim`.

What it should say: `qfminim` when the vectors themselves are wanted (the
Voronoi cell), `qfrep` when only their number is, and always `qfrep` above
a hundred thousand vectors or thirty dimensions. `qfrep` counts vectors of
norm up to $b$ and so also proves the minimal norm; both need the form
LLL-reduced first or the enumeration is slow.

Evidence: `/tmp/dl_check_out2.txt` (exit 137 after `Q31 done`),
`/tmp/dl_check_out4.txt` (`Q32: 261120 minimal vectors` at 12 s, `KP36:
239598 minimal vectors` at 34 s), 2026-09-05.

## A symbol a linked table already uses means what that table says it means

What happened: T148 wrote $\gamma_n$ for the Hermite number of the record
lattice in dimension $n$ and then called it "the best lower bound known for
Hermite's constant". T147, which 44 of its entries link, writes $\gamma(L)$
for a lattice's Hermite number and $\gamma_n=\max_L\gamma(L)$ for Hermite's
constant, which is what $\gamma_n$ means to most readers. A reader who
follows a link and comes back finds the same letter naming two things. The
critique caught it; the repair changed T148 to $\gamma(L)$ and kept
$\gamma_n$ for the constant.

What the skill says now: read the address of every table you link and link
it once per section; nothing about its notation.

What it should say: when a table links another for the same quantity, use
that table's symbol for it, and if a symbol is standard for something else
($\gamma_n$, $\zeta$, $\Delta$) say in the conventions comment which meaning
is in force. Read the linked table's Definition for its symbols before
writing the Formulas section, not after.

Evidence: `agents/critiques/T148.md` finding 6, `T148-repaired.md` item 6,
T147's Definition read through the API, 2026-09-05.

## A control must be checked to fail before it counts, and neighbouring lattices share invariants

What happened: the Hermite-constants build used, as a control that must
fail, "$\gamma_8$ from $\delta_7$": the centre density of $E_7$ fed into
$4\delta^{2/8}$ should not give $\gamma_8=2$. It did, because $E_7$ and
$E_8$ both have centre density $\frac{1}{16}$, so the control was an
identity dressed as a mismatch. The run's `must_fail` wrapper reported it
as a FAIL of the control itself, which is the only reason it was noticed;
$\delta_6=\frac{\sqrt 3}{24}$ replaced it and failed as it should. The same
family has $\gamma(A_1)=\gamma(\mathbb{Z})=1$, since $A_1=\sqrt 2\,\mathbb{Z}$,
which made "the attaining lattice has the strictly largest Hermite number
in its dimension" false in dimension 1 for a good reason.

What the skill says now: "A measurement needs a control that returns a
known answer"; nothing about a control that returns the right answer by
coincidence.

What it should say: a control's answer is a claim too. Print the control's
verdict beside the real checks and count a control that passes as a
failure of the run, so that a coincidence -- two lattices with the same
invariant, a value equal to its neighbour -- is reported rather than
silently agreeing. When a family has similar members ($A_1$ and $\mathbb{Z}$,
$D_3$ and $A_3$, $E_7$ and $E_8$ in centre density), write the uniqueness
checks with the ties named.

Evidence: `/tmp/hc_check_out3.txt`, 2026-09-05: `FAIL control must fail:
gamma_8 from delta_7`; `/tmp/hc_check_out4.txt`: `PASS control must fail:
gamma_8 from delta_6` and `PASS delta_7 = delta_8 = 1/16 in T148`.

## An inequality used as a check has equality cases; a strict comparison reports a sharp bound as an error

What happened: the Hermite-constants build checked Minkowski's bound
$\gamma_n\leq 4V_n^{-2/n}$ and Blichfeldt's bound on every entry with a
strict `<` on ball endpoints, and two right values failed: Minkowski's bound
is an equality at $n=1$ ($4V_1^{-2}=1=\gamma_1$), and Blichfeldt's bound
$\frac{2}{\pi}\Gamma(2+\frac n2)^{2/n}$ coincides with Minkowski's
$\frac{4}{\pi}\Gamma(1+\frac n2)^{2/n}$ at $n=2$ and lies above it at
$n=1$, so "Blichfeldt's is the stronger bound" is true only from $n=3$.
Mordell's inequality $\gamma_n^{n-2}\leq\gamma_{n-1}^{n-1}$ is an equality
at $n=4$ and $n=8$, which the check expected and which became a sentence
in the table.

What the skill says now: "Check every identity before you write it down";
nothing about inequalities.

What it should say: check a bound with `<=` and, separately, where it is
strict and where it is an equality; the equality cases are facts worth a
clause in the Formulas section ("an equality for $n=1$"), and a strict
check that fails on one of them is the check being wrong, not the value.
With balls, "$a\leq b$" is `a.upper() <= b.upper()` only when the two
enclose the same number; write the equality case as `overlaps` and the
strict case as `a.upper() < b.lower()`.

Evidence: `/tmp/hc_check_out2.txt`, 2026-09-05: `FAIL n=1: Minkowski's
bound`, `FAIL n=2: Blichfeldt's bound is below Minkowski's`;
`/tmp/hc_check_out4.txt`: 280 PASS with the cases split.

## An OEIS digit search matches the digit string, not the value; read the offset and scale

What happened: the search `oeis.org/search?q=1.15470053837925152901829756`
for $\gamma_2=2/\sqrt 3$ answered A020832, "decimal expansion of
$1/\sqrt{75}$", whose data is the same digit string at offset $0$, i.e.
$0.11547\ldots=\gamma_2/10$. There is no OEIS entry for $2/\sqrt 3$ itself;
$1/\sqrt{75}=2/(10\sqrt 3)$ is the one there is, and it served as the
digit check once the factor $10$ was written into the comparison. The
same search for $8^{1/5}$ found A011093 under its own name.

What the skill says now: OEIS is a link target and a source of coefficient
triangles; nothing about searching it by digits.

What it should say: OEIS answers a decimal typed into its search box by
matching the digit string, ignoring the decimal point, so the hit may be a
power of ten times the constant under a different name. Read the entry's
name and offset, put the factor into the check, and say in the rigour
details which entry and which factor were used ("A020832, ten times
$\gamma_2$"), so a reader checking the digits is not sent to a constant
that looks wrong by a decimal place.

Evidence: `/tmp/hc_oeis_2over3.json`, 2026-09-05: `A020832 ... offset 0,3`,
data `1,1,5,4,7,0,0,5,...`; `/tmp/hc_check_out4.txt`: `PASS n=2: gamma_2
agrees with OEIS A020832 (Decimal expansion of 1/sqrt(75)) x 10, 99 terms`.

## `audit_table` refuses a table link in the Definition; the first-mention rule stops at that section

What happened: the skill says to link the first mention of a thing the
corpus holds, and the T149 Definition linked "Hermite number" to the table
of the classical lattices, which defines it. `audit_table` answered
"Definition links to another table; a cross-reference belongs in Similar
tables or a comment", and the link was moved out; the conventions comment
already carried it, as did Similar tables. T148's Definition, written
without a link, had passed the same audit.

What the skill says now: "Link the first mention of a thing to what
explains it. A table if the corpus holds one; otherwise a reference the
table already declares", under "Where each thing goes", with no exception
for the Definition; the section table says the Definition holds "one or
two sentences saying what the object is" and not "caveats, history,
relations".

What it should say: in the Definition, cite (`CITE{Wiki}`) but do not link
a table: a `HREF` there is a relation, and relations live in Comments and
Similar tables, which is what `audit_table` enforces. The first-mention
rule applies to the sections after it.

Evidence: `/tmp/hc_audit_out.txt` and `/tmp/hc_audit_out2.txt`,
2026-09-05: the finding, then "Nothing to report" after the edit
(revision `4263db5f…` of T149).

## `IntegralLattice(G).minimum()` is a PARI `Gen`; divided by a Sage root it prints a decimal, not the closed form

What happened: T149's Programs snippet ended
`IntegralLattice(G).minimum() / G.det()^(1/n)   # 2/3^(1/6) = gamma_6`,
and the critique noticed that the build's run of it printed
`1.66536635531121`. It is not a `sage -python` artefact: with the full
`sage.all` namespace and the preparser, exactly as a Sage session runs it,
the line still prints the decimal, because `minimum()` returns a PARI `Gen`
(it is `qfminim`'s answer) and a `Gen` divided by `3^(1/6)` is a PARI real.
`2/3^(1/6)` typed on its own gives the symbolic `2/3*3^(5/6)`. The comment
led a reader to expect a closed form the line never prints.

What the skill says now: run every Programs snippet before writing it down.

What it should say: run it, and check that what it prints is what its
comment says it prints. A PARI `Gen` from `qfminim`, `minimum()` or `.pari()`
does not become symbolic when combined with a Sage root; wrap it in `ZZ()`
or `QQ()` first, or make the line print an exact rational instead, as
T149 now does: `ZZ(IntegralLattice(G).minimum())^n / G.det()   # 64/3 = gamma_6^6`.

Evidence: `/tmp/rep149_check.py` section 3 and `/tmp/rep149_check2.py`
section 3b, 2026-09-05: result `1.66536635531121` of type `Gen`; the
`ZZ(...)^n / G.det()` form gives `64/3` in the rational field.

## An entry comment renders `HREF` and `CITE` like the prose, so a value held by two tables can link the second from its comment

What happened: T149's $\gamma_2$ and $\gamma_4$ are rows of the classical
lattices table and of the table of algebraic numbers of degree 2. An entry
carries one `equals`, spent on the classical lattices; the Similar-tables
row said the degree-2 table "holds" both and did not say where. An entry
comment goes through the same `render_text` as a Comments paragraph, so
`; the same number is in the HREF{Algebraic_numbers_of_degree_2#3,0,-4,2}[table of algebraic numbers of degree 2]`
in the comment renders as a `?entry=` link, as T146's comments already do.

Checking the anchor needs no Django when the target is published: the page
route reads `?entry=<anchor>`, and the answer carries
`id="<anchor>" class="table-block table-block-focused"` on the entry it
found, with the number beside it, so
`curl -s 'https://numberdb.org/Algebraic_numbers_of_degree_2?entry=3,0,-4,2'`
and a grep for `table-block-focused` says whether the row exists and which
number it holds. The degree-2 anchor is `a2,a1,a0,n` for the $n$-th root of
$a_2x^2+a_1x+a_0$ in increasing order.

What the skill says now: an entry links one other entry through `equals`.

What it should say: when a value is in a second table too, the comment may
link that row with an `HREF`, and a published table's anchor can be checked
with `?entry=` through curl before it is written.

Evidence: `/tmp/t35_3,0,-4,2.html` and `/tmp/t35_1,0,-2,2.html`
(2026-09-05), `/tmp/rep149_audit_after.txt`: the rendered T149 carries
`Algebraic_numbers_of_degree_2?entry=3,0,-4,2` and `?entry=1,0,-2,2`.

## Certify a covering radius by an exact closest-vector enumeration, not by raising the vector bound until $4R^2\leq B$

What happened: the covering table (T150) proves $R^2$ of a lattice from its
Voronoi cell, cut as a rational `Polyhedron` from the lattice vectors of norm
at most $B$. The first certificate raised $B$ until $4R_B^2\leq B$, which is
sound (every Voronoi-relevant vector has norm $\leq 4R^2$) and hopeless from
dimension 7: $\mathbb{Z}^7$ has $R^2=7/4$, so the bound needs every vector
of norm $\leq 7$, 8052 of them, and the run sat 367 s in that one cell
before it was killed. The polytope cut by the vectors of norm $\leq 2\mu$
alone already has the right deepest vertex in every case met, and that
vertex $x=y/d$ with $|x|^2=p/q$ is proven a genuine hole by one `qfminim`
on the $(n+1)$-dimensional integral form
$Q(v,k)=q\,(dv-ky)^{T}G(dv-ky)+k^2d^2p$ with bound $2d^2p-1$: a vector with
$k\neq 0$ in the answer is a lattice point nearer to $x$ than $R_B$, and
none means $d(x,L)=R_B\leq R\leq R_B$. Every lattice of dimension 7 and 8
took a second or two; $E_8$ took 129 s, all of it in enumerating the 19440
vertices of its cell.

What the skill says now: nothing about lattices.

What it should say: a certificate that needs *all* vectors up to a bound
grows with the bound's power of the dimension; one that names a witness and
refuses a counterexample by enumeration does not. Run the control first --
$(1/2,0,0)$ in $A_3$ offered as a hole at $R^2=1$ must be refused, and was.

Evidence: `/tmp/cv_check_out.txt` (`PASS Voronoi Z_7 ... 367 s`, then
`Terminated`) against `/tmp/cv2_check_out.txt` (`Z_7 ... 0 s`, `E_8 ...
129 s`), 2026-09-05.

## A six-decimal table in a paper can carry a misprint that the next paper copies; when one row disagrees beyond rounding and the rest agree, check that row from its closed form

What happened: $\Theta(A_n^{*})$ was compared with Table 1 of Schürmann and
Vallentin (2006). Eleven rows agreed to all six decimals and $n=3$ did not:
the table prints $1.463505$ and $5\sqrt{5}\,\pi/24=1.4635031\ldots$ Table 2
of Dutour Sikirić, Schürmann and Vallentin (2008) prints the same
$1.463505$. The value was settled by the Voronoi cell of the catalogue's
own Gram matrix ($R^2=5/16$ at $\mu=3/4$) and by $\Theta=(R/\rho)^3\Delta$
against the stored packing density; the misprint is in
`docs/external-bugs.md`, and the rigour details say which row the tables
get wrong rather than reporting eleven of twelve.

What the skill says now: "if your recomputation disagrees with a stored
value, suspect your recomputation first" -- right, and this is the other
case: one row of a published table, off by $2\cdot 10^{-6}$ at six decimals,
with three independent computations against it.

What it should say: a published table is a check, not an oracle; agreement
on every other row is what earns the right to call the odd one a misprint,
and the closed form is what decides it.

Evidence: `/tmp/cv2_check_out.txt` (`FAIL SV Table: Theta(A_3^*) =
1.463505`, every other SV row `PASS`) and `/tmp/cv2_dsv_out.txt`, 2026-09-05.

## "Best known" comments need the latest table, and the paper that has it may not be the one the proposal named; two 2008 results changed nineteen comments

What happened: the proposal and the 2006 Schürmann–Vallentin table said a
thinner lattice covering than $A_n^{*}$ was known in dimensions 6 to 9, 11
and 13 to 15. The 2008 Duke paper of Dutour Sikirić, Schürmann and Vallentin
(found through its arXiv abstract, `math/0601084`) has a Table 2 of the least
dense lattice coverings known in every dimension to 24: thinner ones in 9 to
15, 17 and 19 to 21 as well, $\Lambda_{22}^{*}$ and $\Lambda_{23}^{*}$ in 22
and 23, and $A_n^{*}$ itself only in 16 and 18. Every one of its 24 values
was checked against the table's $\Theta(A_n^{*})$ before a comment said
"thinner is known", and the two rows where $A_n^{*}$ stands say "the thinnest
listed by" that paper, which stays true whatever is found later.

What the skill says now: verify a claim before writing it into a table.

What it should say: a comment of the form "the best known is" or "a better
one is known" is a claim about a date; cite the table it comes from, check
every row of that table against yours, and phrase the rows where yours is
the record as "the thinnest listed by X", not "the thinnest known".

Evidence: `/tmp/cv2_dsv.txt` lines 1295–1308 (the table), `/tmp/cv2_dsv_out.txt`
(29 PASS), 2026-09-05.

## `RealNumber.str(9)` prints in base 9: the first positional argument of `str` is the base, not the number of digits

What happened: two check scripts printed a ball's midpoint with
`.mid().str(9)` and `.mid().str(12)` to show a few digits beside a PASS line,
and printed `7.4527763...` for $7.51$ and `2.15a92389b2b3...` for $2.11$:
the output is in base 9 and base 12. The comparisons themselves were made
on balls and were right; only the human-readable column was gibberish, and
a reader would have reported a disagreement that does not exist.

What the skill says now: that `RealBall` has no `str` and the midpoint's
must be used.

What it should say: `mid().str(digits=k)`, with the keyword; `str(k)` is
base $k$.

Evidence: `/tmp/cv2_dsv_out.txt` first run (`7.465518 < 7.4527763...` marked
PASS), `/tmp/cv2_check_out.txt` (`2.15a92389b2b3...`), 2026-09-05.

## An exact table's integer interval is a plain string, and `verify()` cannot tell a broken serialisation from a right one

What happened: the kissing-number table (T151) stores `[40, 44]` for a
value known only to lie between two integers, the shape T6 uses for
$R(5,5)$. The client has no value for that: `to_text` on a `RealInterval`
with endpoints 40 and 44 writes the decimal digits the endpoints agree on,
not `[40, 44]`, and a plain `str` is the only return `to_text` passes
through untouched. `check.exactness` reported that string as "unexpected
type str", so the first fill returned it as a subclass of `str` carrying
`lower` and `upper`. `to_text` passed it through, and then the client's
YAML writer serialised the subclass as a Python object: eighteen entries
were stored as `{'args': ['[40, 44]'], 'state': {'lower': ..., 'upper':
...}}`, rendered as two sub-entries each, and left out of the search
index. `verify(sample=None)` reported 24/24 matched, because it compares
the generator's serialisation with the stored one and both were wrong the
same way. `audit_table` said 18 values were not in the index, and the
stored table read back through `numberdb.table(tid)` showed the mappings.

What the skill says now: a string is "taken verbatim"; nothing about
integer intervals for exact types, and nothing about `str` subclasses.

What it should say: for a table of type `Z` (or `Q`) whose entry is an
integer known to lie in an interval, return the plain string `[a, b]`,
`type(x) is str`, and nothing wrapped around it. And read the table back
through the API after a fill and look at the shape of the values: `verify()`
answers "does the generator still produce what is stored", never "is what
is stored a number". `check.exactness` now accepts the `[a, b]` string of
nonzero width and refuses a subclass, so the dry run no longer pushes a
run into disguising the value.

Evidence: 2026-09-06, T151 revisions 2 and 3; `/tmp/kn_stored_out2.txt`
(`n=5: number is a mapping: {'args': ['[40, 44]'], ...}`), the audit's "24
distinct values are written but only 6 are in the search index", and the
repair `PublishOutcome T151: 0 added, 18 updated, 6 unchanged`.

## A table of literature bounds must be read from its maintained source on the day it is built

What happened: the batch proposing the kissing numbers was written on
2026-09-03 and quoted "the Wikipedia table as of the build date". Three
days later three dimensions had moved: 604 in dimension 11 (June 2026),
841 in 12 (June 2026) and 11948 in 19 (March 2026), all preprints, and
the Nebe-Sloane "highest kissing numbers" page, which the batch and OEIS
name as a source, is now a one-line pointer to Henry Cohn's table. Cohn's
page and Wikipedia agreed in every dimension to 24, and each paper's arXiv
abstract states the number it is cited for, which is what settled the
attribution of every endpoint.

What the skill says now: verify against something independent; cite what
you declared. Nothing about values that are records rather than
computations.

What it should say: for an entry that is a record (a best bound, a densest
known packing), two maintained sources that agree on the build date are
the independent check, the date goes in Comments and in `complete-note`,
and the entry comment names the paper for each endpoint; an interval
stays true when a bound improves, so a record table of intervals goes out
of date rather than wrong, and the comment should say so. Fetch the arXiv
abstract page (`arxiv.org/abs/<id>`) for each cited preprint: the number
claimed is in the abstract, and reading it takes a second.

Evidence: 2026-09-06, `/tmp/kn_sources_check.py`: 83 checks, both tables
parsed, nine abstracts, OEIS A257479 and A001116.

## An integer interval entry is shown with a "not findable" mark

What happened: on T151's page every `[a, b]` entry carries a dagger linking
to `/help#search-precision`, "This number will not ..." -- the site's mark
for a value too wide to be matched by digits. The six exact entries have
none. So a reader holding $40$ does not reach the table by typing it; the
table is found by its title, and the comments carry the numbers a reader
might hold ($40$ is the kissing number of $D_5$).

What the skill says now: an unsearchable *type* is "shown and cited rather
than found"; nothing about a searchable type holding an interval too wide
to match.

What it should say: an interval of integers is shown, not found by its
digits; put the endpoints and what attains them in the entry comment, and
expect the table to be reached by its name.

Evidence: 2026-09-06, the rendered T151 page in `/tmp/kn_audit_out3.txt`,
`class="not-findable-mark"` on `[40, 44]`.

## A decimal interval search finds an exact rational entry, so a `Q` table is findable by somebody holding digits

What happened: proposing a table of the exact two-dimensional critical
exponents (type `Q`: $5/36$, $43/18$, $91/48$) raised the question whether a
reader holding $0.1389$ would ever reach it. Tested on the corpus:
`numberdb.search_real_interval('0.16666', '0.16667')` returned $1/6$ from
T13 (Bernoulli numbers), T94 and T130; `search_rational(1, 6)` returned the
same four results. The search result is a `list` subclass with `.total`,
`.tables`, `.tags`, `.messages` and `.unreadable`; it has no `.numbers`
(`r.numbers` raises `AttributeError`), and `search_real_interval` refuses a
single string ("give two endpoints, or one real interval").

What the skill says now: `search_text` returns an object with a `.tables`
list; nothing about searching by value from the client.

What it should say: a `Q` table answers a search by decimals, so a family
of distinctive rationals is findable and worth a table; and the value
searches (`search_integer`, `search_rational`, `search_real_interval(lo,
hi)`, `search_real_ball`) return a list of `Result(value, table=...)` with
`.total` beside it, so `len(r)` and iteration are the way to read them.

Evidence: 2026-09-06, `/tmp/probe_search2.py` -- "rational 1/6 len 4
total 4", "interval ('0.16666', '0.16667') len 4", and `TypeError` on
`search_real_interval('0.16666')`.

## OEIS search by digits wants a comma-separated digit string

What happened: `search?q=15030480824753&fmt=text` returned nothing for the
hard-square entropy constant, and the same for a dozen other constants
that OEIS holds. `search?q=1,5,0,3,0,4,8,0,8,2,4&fmt=text` returned A085850
at once. A string longer than the entry's data field also fails, so eleven
digits is a good length; and a search by digits for a constant of which
one has the wrong tenth digit finds nothing rather than a near miss.

What the skill says now: OEIS by id is `search?q=id:A222072&fmt=json`
(existing lesson); nothing about searching by digits.

What it should say: to find a constant in OEIS by its digits, search
`d,d,d,d,d,d,d,d,d,d,d` with commas, about eleven digits, and read the
`%N` line; a name search (`search?q=spanning+tree+constant&fmt=text`)
is the fallback when the digits in hand are few or doubtful.

Evidence: 2026-09-06, `/tmp/oeis_lookup.sh` before and after the change to
its query line; eleven of twenty-one constants found on the second run
against zero on the first.

## `source_names_it` confirms a name on MathWorld and never a value; some publishers' `doi.org` pages name nothing

What happened: every MathWorld page tried (`PercolationThreshold`,
`IsingModel`, `HardSquareEntropyConstant`, ...) passed the name check and
contained not one decimal, because MathWorld renders formulas as images; a
value cannot be quoted from it. The IOP page behind Baxter 1980's doi
(10.1088/0305-4470/13/3/007) answered `urllib` with a shell that mentions
none of "hard hexagons exact solution", while `doi.org` for an Elsevier
(JCTB 1996) and an AMS (Math. Comp. 1999) paper passed, and every arXiv
abstract passed and quoted its headline number ($K_c = 0.221654626(5)$,
$\mu = 4.684039931(27)$).

What the skill says now: cite Wikipedia, MathWorld, DLMF, OEIS or a paper.

What it should say: MathWorld is a source for a *name*; for a *value*
cite the OEIS entry, the Wikipedia table with its per-entry references,
or the arXiv abstract, which is where a value can be read back. A `doi.org`
link may or may not pass the screen depending on the publisher; when it
fails, the arXiv abstract of the same paper usually passes.

Evidence: 2026-09-06, `/tmp/sources_check.py` (26 sources, one failure)
and `/tmp/mw_*.txt` (no decimals in any).

## GitHub's issue search rate-limits `already_asked` after ten names in one run

What happened: `screen.already_asked` returned "could not ask GitHub
(HTTPError)" from the eleventh name on -- the unauthenticated search API
allows ten requests a minute -- and the first ten had returned nothing,
which reads like "nobody asked". The whole `table wanted` label, open (82)
and closed (44), is two `curl` calls to
`/repos/numberdb/numberdb-data/issues?labels=table%20wanted&state=...&per_page=100`
and is the complete answer.

What the skill says now: read the open issues with the label.

What it should say: fetch the label's open and closed lists once and grep
them for every name; `already_asked` is for a single name, and more than
ten in a minute are refused.

Evidence: 2026-09-06, `/tmp/screen_run.py` output (HTTPError from the
name "Spanning tree" on) and `/tmp/issues1.json`, `/tmp/issues_closed.json`.

## A `measured` row is a plain string `centre +/- radius`, and it must say how many digits it claims

What happened: the percolation-threshold table (T152) transcribes 55
published estimates, each with the paper's stated uncertainty. The corpus
writes such a value as `0.7478008 +/- 2e-7` (the fine-structure constant,
T10, is the precedent), but `Generator.format` is one setting for the whole
table, and the same table holds eleven exact values written as 100-digit
decimals. `to_text` passes a string through verbatim, so a `measured` row is
returned as the string built from the paper's own digits, and the exact rows
stay balls. Two things followed. `_check_precision` counts the digits a
written value claims -- `digits_of('0.7478008 +/- 2e-7')` is 7 -- against
the generator's `digits` of 100 and refuses the entry, so each such row
returns `{'number': text, 'digits': digits_of(text)}`, with `digits_of`
imported from `numberdb._compare`. And `check.exactness` reported the string
as "unexpected type str", exactly as it once did for `[40, 44]`, so it now
accepts the ball spelling too (plain `str`, positive radius) rather than
sending a run looking for a disguise.

What the skill says now: a string is "taken verbatim"; `measured` "is not
computed at all"; nothing about how a measured value is written or how its
digits are counted.

What it should say: a measured value is written as `centre +/- radius` with
the source's uncertainty as the radius, returned as a plain string, and the
entry declares `'digits': digits_of(text)`; `check.exactness` accepts that
string. A generator that also has exact rows keeps `format = 'decimal'` and
returns balls for them.

Evidence: 2026-09-06, `/tmp/pc_dry_out.txt` (`ENTRY square,2,site =
0.592746050788 +/- 6e-12 (str, claims 11 digits)`), the fill's `66 added`,
and the stored check `PASS 241, FAIL 0`.

## When published determinations disagree beyond their errors, store the interval that holds them all, and say which

What happened: the site percolation threshold of the square lattice has four
recent determinations, $0.59274605079210(2)$ (Jacobsen 2015),
$0.592746050786(3)$ (Mertens 2022), $0.5927460507896(1)$ and
$0.59274605079016(1)$ (a 2024 comment and its reply), which disagree in the
twelfth decimal by more than their stated errors. The proposal had said the
first two agree. Storing the newest, or the most precise, would have put a
claim in the table that the literature does not support. The entry is
$0.592746050788\pm 6\cdot 10^{-12}$, the interval containing all four with
their error bars, and the comment lists the four and says they disagree;
this is the convention T10 uses for the fine-structure constant, whose
interval is chosen to hold every measurement with its uncertainty.

What the skill says now: "when two computations disagree, neither is right
until you know why" -- for computations of one's own.

What it should say: for a transcribed value, when the sources disagree
beyond their errors, the entry is the enclosure of all of them, the comment
names each with its value, and the rigour details say the interval was
chosen here; a table is not the place to adjudicate a dispute in the
literature.

Evidence: 2026-09-06, Wikipedia's *Percolation threshold* table (square row),
`/tmp/pc_src/pdf_1507.03027.txt` line 784 and `/tmp/pc_src/pdf_2109.12102.txt`
lines 898-956 (Mertens' own comparison with Jacobsen, "deviates ... by 2
errorbars"), zbMATH for the 2024 comment and reply.

## The paper's stated error is not always the radius to store; read the maintained table beside it

What happened: Suding and Ziff 1999 print $0.579498(2)$, $0.550806(2)$ and
$0.550213(2)$ in their Table I; the Wikipedia table, which one of the
authors maintains, lists all three as $(3)$. The same paper's values for
the lattices since measured to nine digits by Jacobsen lie two to three of
its standard errors from the later values ($0.621819(2)$ against
$0.62181207(7)$, $0.747806(3)$ against $0.7478008(2)$), so the paper's
errors were optimistic, and $(2)$ would have overclaimed. The table stores
$(3)$ and the entry comment says the paper prints $(2)$.

What the skill says now: "verify against something independent"; the
batch's convention was "the paper's stated error as the radius".

What it should say: take the radius from the paper unless a maintained
source lists a larger one or later values show the paper's error was too
small; then take the larger, and let the comment say what the paper prints.
A source's error bars can be checked against its own values for the rows
that have since been superseded.

Evidence: 2026-09-06, `/tmp/pc_src/pdf_cond-mat_9811416.txt` lines 786-808
and the Archimedean table of `/tmp/pc_src/wiki_percolation.txt`.

## A row derived from a measured row inherits its radius; compute the centre in exact decimal arithmetic from the printed digits

What happened: the eight Laves bond thresholds are $1-p_c$ of the dual
Archimedean lattice, whose value is a transcribed estimate with an error.
Wikipedia lists them rounded to six decimals, from older estimates. The
generator computes `Decimal('1') - Decimal(centre)` from the source's
printed digits and keeps the radius, so `1 - 0.4141378565917(1)` is stored
as `0.5858621434083 +/- 1e-13`, with a comment saying which dual and which
paper. Python floats would have written `0.5858621434083001`.

What the skill says now: do not divide Python ints; nothing about
subtracting decimals.

What it should say: a value derived from a printed decimal is computed with
`decimal.Decimal` (or `QQ`) from the printed string, never from a float, and
carries the source's radius; the comment names the relation and the source.

Evidence: 2026-09-06, `generators/percolation-thresholds/generate.py`,
`Threshold.__init__`, and the duality checks in `/tmp/pc_check_out3.txt`.

## A count in the prose must be counted from the rows, not copied from the proposal

What happened: the percolation table's comment said "Eleven of the
thresholds are known exactly" and its rigour details said "Eleven entries
are exact" and "The other 55 entries were not computed". The rows held nine
exact entries (five $\frac12$, four closed forms at 100 digits) and 57
estimates. The eleven was the number of Archimedean lattices in the
proposal, carried into the prose by the same hand that wrote the generator's
docstring and commit message, and every sentence around it then listed the
nine correctly. Nothing in `audit_table` compares a number in the prose
with the rows, so the table was offered for review saying two different
things about itself.

What the skill says now: nothing about counts stated in prose.

What it should say: when a comment or `rigour details` states how many
entries are of a kind, have the generator count them and either print the
count for the prose or assert it against the document before publishing;
a number that was typed rather than counted is the one that will be wrong.

Evidence: 2026-09-06, T152 revision `1946036c…` against its 66 rows;
`agents/critiques/T152.md` finding 1; repaired in revision `b44fce18…`.

## Rigorous integration is there, under `ComplexBallField.integral`; `RealBallField` has neither `integral` nor `catalan`

What happened: the entropy-constants table needed two one-variable integrals
(a Kasteleyn integral for dimers on the triangular lattice, the Laplacian
integral for spanning trees on $(4,8^2)$) and Catalan's constant. With the
named imports the skill prescribes, `RealBallField(prec)` has no `integral`
and no `catalan`; `ComplexBallField(prec).integral(f, a, b)` exists and is
arb's rigorous integrator, taking `f(z, analytic)` where `z` is a complex
ball and the `analytic` flag must be passed on to every `.sqrt()` and
`.log()` so that a branch point on the path is reported rather than crossed.
Its real part is the enclosure. Catalan's constant and $L(2,\chi_{-3})$ came
from the Hurwitz zeta function, which `RealBall.zeta(a)` does provide:
$G=(\zeta(2,\tfrac14)-\zeta(2,\tfrac34))/16$ and
$L(2,\chi_{-3})=(\zeta(2,\tfrac13)-\zeta(2,\tfrac23))/9$, checked against
OEIS A006752 and the corpus's T145 to 100 digits.

What the skill says now: that `.log()`, `.inverse()`, determinants and
`SymmetricFunctions` are missing under named imports; nothing about
integration or the constants.

What it should say: in the list of what the named imports do not bring, add
"`RealBallField.integral` and `RealBallField.catalan`; use
`ComplexBallField(prec).integral(f, a, b).real()`, passing the `analytic`
flag through to every `sqrt` and `log`, and a Dirichlet $L$-value from
`RealBall.zeta(a)`, the Hurwitz zeta function". A double integral is not
available at all; integrate one variable in closed form first
($\int_{-\pi}^{\pi}\ln(A+B\cos v)\,dv=2\pi\ln\frac{A+\sqrt{A^2-B^2}}{2}$
does it for every Kasteleyn and Laplacian integrand met here), and run the
same reduction on a case with a known answer as the control.

Evidence: `/tmp/ec_preflight_out.txt` (`AttributeError: ... no attribute
'catalan'`, `RBF.integral: False  CBF.integral: True`), then every integral
PASS against OEIS and the paper, 2026-09-06.

## When a computed value disagrees with a paper, a second method that shares nothing decides it, and the control must fail the same way the target could

What happened: the paper's own integral for the spanning-tree constant of
the simple cubic lattice, evaluated by nested tanh-sinh quadrature at two
precisions, gave $1.67338930\ldots$ against the paper's $1.6741481(1)$; the
two precisions agreed to 30 digits, which bounds the working-precision error
and nothing else. The control run beside it (the square lattice by the same
nested quadrature, known to be $4G/\pi$) returned $-\infty$, because the
integrand's logarithm is singular at a corner and the inner quadrature's
nodes at high precision came close enough to evaluate it at zero -- so the
control said nothing about the target, whose $\operatorname{arccosh}$ is
finite there. What settled it was a third computation sharing no code and
no method: the closed-walk series $\ln 6-\sum W_{2m}/(2m\cdot36^m)$ from an
OEIS recurrence, summed to $1.6\cdot10^6$ terms and extrapolated on its
$M^{-3/2}$ tail, which agreed with the quadrature to 22 digits. The paper is
wrong (`docs/external-bugs.md`).

What the skill says now: "when two computations disagree, neither is right
until you know why", and that a control must return a known answer.

What it should say: add that a control must be singular in the same way as
the target, or it tests a different method; and that when the disagreement
is with a published number, the second computation should be a different
formula (a series where the first was an integral), because two evaluations
of the same integral agree about the integral and not about the paper.

Evidence: `/tmp/ec_preflight_out2.txt` (control square: -inf), `/tmp/ec_walks.py`
(extrapolated 1.67338930297019673228348), 2026-09-06.

## A value transcribed with the digits its source states is returned as a plain decimal string, and its logarithm as a ball from that interval

What happened: Baxter states 43 decimals of the hard-square constant and
believes them all; there is no separate uncertainty to write as a radius, so
the entry is the plain decimal, the skill's first spelling of a real, which
denotes the interval one unit of the last place wide. The entropy $\ln\kappa$
of that row was computed as arb's logarithm of the ball with that radius, and
the client wrote the 41 decimals the result supports. Where the source says
its last digits are doubtful (Baxter's honeycomb value, 38 decimals with
"the last two or three" in doubt), the string is cut before them. Each such
entry declares its digits with `{'number': ..., 'digits': n}`, and the count
is read off the client's own writer, `digits_of(to_text(number, digits))`,
rather than typed.

What the skill says now: the four spellings, and that a string is taken
verbatim; nothing about deriving one entry from a transcribed other.

What it should say: a row derived from a transcribed value (its logarithm,
its square, one minus it) is computed on the interval the transcription
denotes, in ball arithmetic, so that its written digits follow from the
source's rather than from the working precision; and the number of digits an
entry declares is taken from `to_text`, not counted by hand.

Evidence: the dry run of T153 (`/tmp/ec_dry_out2.txt`): hard-core square
kappa 44 digits, entropy 41; honeycomb 36 and 34. 2026-09-06.

## `yaml.dump` sorts every mapping unless told `sort_keys=False`, and the site stores and shows the order it is given

What happened: T153's fourth revision was written by loading the document,
editing two fields and sending `yaml.dump(document)` to `POST /api/table/<n>`.
PyYAML sorts mapping keys by default, so the parameters came back as
`expression, lattice, model` while the numbers stayed nested
model → lattice → expression: the header of the Numbers section named the
columns in the wrong order, the first row on the page was the honeycomb dimer
entropy instead of the golden ratio, the ten formulas were numbered
alphabetically so that formula (1) used a symbol defined in formula (10), and
the conventions comment came before the comment that introduces the models it
speaks of. Nothing in the values was wrong, and no check complained; a reader
saw it first. The same dump had already alphabetised T147's five formulas.

What the skill says now: how to write a document and that the read endpoint
serves the keys in the stored order; nothing about a round trip through PyYAML.

What it should say: a document that goes through `yaml.safe_load` and
`yaml.dump` on the way to the API must be dumped with `sort_keys=False`
(the `numberdb` package does this itself); after any whole-document write,
read it back and compare the order of `Parameters`, of the formulas and of
the first row of `Numbers` with what was sent, not only the mappings, since
two documents equal as mappings render as two different pages.

Evidence: `/tmp/ec_write_doc.py` (the sorting dump, revision `a2506f1a…`),
`/tmp/rep153_write.py` (the repair, `sort_keys=False`, read back in order),
2026-09-06.

## `publish()` compares values, not comments: a comment-only repair is reported as unchanged and nothing is sent

What happened: two entry comments of the Ising-couplings table had to be
corrected after the fill. The generator's `COMMENT` table was fixed and
`publish()` run again; it answered `46 unchanged` and the head revision did
not move, because the client decides what to send by comparing the numbers
with the stored ones, and an annotation rides along only with a value that
changes. The comments were rewritten by sending the whole document with the
stored `Numbers` rebuilt and the comments replaced, pinned to the head
revision with `X-Base-Revision`, which is the third time this run has done
that by hand (`/tmp/ic_write.py`, after `/tmp/rep153_write.py`).

What the skill says now: `publish()` writes, `verify()` compares, and an
entry may carry a `comment`; nothing about what makes an entry count as
changed.

What it should say: that `publish()` sends an entry when its value differs
from the stored one, so a repair that touches only a comment, `digits` or
`equals` is a document edit and not a fill; and either the package should
offer that edit, or the skill should show the document write pinned to the
head revision.

Evidence: `/tmp/ic_update_out.txt` (`0 updated, 46 unchanged`, head
6acc1085 unchanged), `/tmp/ic_write_out.txt` (revision ae9e2699, read back
in order), 2026-09-06.

## A raw string keeps the backslash of an escaped apostrophe, and every check passed while the page showed it

What happened: `r'... Onsager\'s solution ...'` in the generator's comment
table is the eleven characters `Onsager\'s` with the backslash, since a raw
string does not process the escape. The dry run, `check.exactness`, the
fill, `verify()` and `audit_table --links` all passed; the rendered page
showed `Onsager\'s` and `Jacobsen\'s`, seen only because the audit script
prints the text around a few needles. `check.prose` now refuses a comment
with a backslash before a quote, and one that says "below" or "above",
and the dry run calls it (tests in `numberdb_app/test_agents.py`).

What the skill says now: that entry comments are shown as a line under the
value, and how to write one; nothing about how they are checked.

What it should say: a comment is prose and gets the checks prose gets:
read the entries as the page will show them once, and let the dry run
refuse a backslash before a quote. A comment with an apostrophe goes in a
double-quoted string.

Evidence: `/tmp/ic_audit_out.txt` (`Onsager\'s` in the rendered body),
`/tmp/ic_audit_out3.txt` after the repair, 2026-09-06.

## Proving a root is the only one: a sign change proves existence, and the naive ball scan for uniqueness fails on the piece next to the root

What happened: each planar Ising coupling is the root in $(0,1)$ of a
polynomial $P$, enclosed by a sign change of $P$ across $m\pm10^{-105}$.
To prove it is the only root there, the first version evaluated $P$ on 200
balls covering $[0,m-w]$ and $[m+w,1]$ and required none to contain zero;
the piece adjacent to the enclosure always does, since $P$ is within
$|P'|\cdot 10^{-105}$ of zero at its end and a ball over a piece of width
$0.002$ cannot resolve that. What works: on a margin of half-width
$2^{-10}$ around $m$ require $P'$ not to contain zero, so $P$ is monotone
there and the sign change is one root; outside the margin cover $[0,1]$
with pieces split adaptively wherever the ball contains zero, down to a
width $2^{-40}$ below which the doubt is treated as a root and refused. A
control with a second root, $(1-2v)(1-4v)$ with $\frac12$ offered as the
root, is refused by the scan.

What the skill says now: to check the claim the digits make by a sign
change across the written enclosure; nothing about uniqueness.

What it should say: a sign change proves a root inside the enclosure and
nothing about roots outside it; where the definition says "the root in
$(0,1)$", prove uniqueness separately, by monotonicity on a margin and a
scan outside it, and keep the margin, since a scan that touches the
enclosure cannot pass.

Evidence: `/tmp/ic_preflight_out.txt` (first run, `square: P(v) may
vanish again on [0.41214..., 0.41421...]`), the second run clean with the
two-root control refused, 2026-09-06.

## Compare enclosures by containment, not by radius: arb's radius is an over-estimate

What happened: the reciprocal $k_BT_c/J$ of a published $K_c\pm r$ is
written as `centre +/- radius` computed in decimal arithmetic, with the
radius rounded up to two digits. A preflight test compared that string
with arb's `1/ball` by asking the written radius to be at least arb's,
and failed on one of four rows (`0.000096` written, arb `0.000096008`),
although the written interval contains the exact one: arb's radius carries
the rounding of every operation and is larger than the true half-width.

What the skill says now: that a wide enclosure agrees with everything and
that both sides of a comparison must be finite; nothing about comparing
two enclosures of the same thing.

What it should say: two enclosures of one value are compared by asking
whether the one claimed contains the exact interval, computed from exact
endpoints, and never by comparing radii, which measure the arithmetic and
not the value.

Evidence: `/tmp/ic_preflight_out.txt` (`FAIL reciprocal text contains
1/ball on fcc`), `/tmp/ic_preflight_out2.txt` (containment test, PASS),
2026-09-06.

## A published numerical estimate is `heuristic`, not `measured`

What happened: T154 stores four Ising couplings of cubic lattices as
`centre +/- radius`, transcribed from Monte Carlo and series papers, and
the build labelled the table `rigour: measured` because nothing here had
computed them. The critique read the site's definition of `measured`, "not
computed at all, the value comes from experiment", and the table's own
rigour details, which open "labelled by its weakest entries", and pointed
out that `measured` is outside the ordering and so cannot be the weakest
of anything. T153, the sibling built the same day, had labelled its
transcribed rows `heuristic`.

What the skill says now: the table of levels, with `measured` as "not
computed at all — an experimental value. Not on the scale."

What it should say: a value taken from a paper that computed it, with an
uncertainty its authors chose, is one computation and a guard chosen by
judgement, somebody else's: `heuristic`. `measured` is for a value that
came from an instrument. A table mixing proven enclosures with transcribed
estimates is labelled by the estimates, and the rigour details say which
rows are which.

Evidence: `agents/critiques/T154.md` finding 3, `numberdb_app/validate.py`
and `docs/design/rigour.md` on `measured`; T154 revision `31966f61…`,
2026-09-06.

## A stored interval wider than 1e-5 of its value is not found by number

What happened: T154's body-centred cubic coupling was stored as
`0.1573725 +/- 1e-6`, the uncertainty Butera and Comi print, while the
row's comment said Lundow and Campbell quote `0.1573725(5)`. The site
marks a value whose relative width `(high - low)/max(|low|, |high|)`
exceeds `NUMBERDB_MAX_RELATIVE_WIDTH`, 1e-5, with a dagger and leaves it
out of search by number; at radius 1e-6 the width is 1.3e-5 and both the
coupling and its reciprocal were daggered, so a reader arriving with
0.1573725 found nothing. At radius 5e-7 the width is 6.4e-6 and both rows
answer. The two papers were read here: Butera and Comi's Table II does
print (10), and Lundow and Campbell quote (5) citing Butera and Comi and
two Monte Carlo studies, so the sharper value has a source and the row now
stores it and says what the primary table prints.

What the skill says now: that values answer search by number, and nothing
about a width above which they do not.

What it should say: a value written as `centre +/- radius` answers search
by number only if `2 radius / centre` is at most 1e-5; when two published
uncertainties differ by a factor that crosses that line, store the one
with the sharper source and say in the comment what the other prints. The
reciprocal of a wide interval is wide too, so a daggered value daggers its
derived rows.

Evidence: `numberdb_app/models.py` `findable_by_number`, the rendered
page before and after (`/tmp/rep154_audit_before.txt`, four daggers;
`/tmp/rep154_audit_after.txt`), arXiv:hep-lat/0112049 Table II and
arXiv:1710.03574 section on the BCC lattice, 2026-09-06.

## Under the named imports a rational divided by a Python int raises, not rounds

What happened: the generator of T155 wrote its Coulomb-gas couplings as
`QQ(3) / 4`. Under `import numberdb.sage` and `from sage.rings.rational_field
import QQ`, with no `sage.all`, the expression raised
`AttributeError: module 'sage.rings' has no attribute 'real_mpfr'` from
inside the coercion model: `Rational.__truediv__` with an `int` on the right
asks the coercion model for an action, which calls `QQ._an_element_()`,
which builds `Rational((1, 2))` and reaches for `sage.rings.real_mpfr`, a
module that only `sage.all` imports. `QQ(3) / QQ(4)` and every other
`QQ / QQ` division work; so do `2 * g`, `g - 1` and `1 <= g <= 2` with `g`
rational, since those take the fast paths.

What the skill says now: "write every division between Sage rationals,
`QQ(a) / QQ(b)`", for the different reason that a Python int divided by a
Python int is a float.

What it should say: the same sentence, with the second reason beside the
first: under the named imports a Sage rational divided by a Python int does
not give a rational and does not give a float either -- it raises from the
coercion model, because the module it needs is one only `sage.all` loads.
The one rule covers both: every operand of `/` is a Sage rational.

Evidence: the first dry run of `generators/critical-exponents-2d/generate.py`
under SageMath on 2026-09-06, the traceback ending in
`sage/rings/rational_field.py, line 1124, in _an_element_: return
Rational((1, 2))` and `AttributeError: module 'sage.rings' has no attribute
'real_mpfr'`; the second run, with `QQ(3) / QQ(4)`, computed all 34 entries.

## A draft is readable through the API by its owner, and a corpus walk without the key does not see it

What happened: the batch that proposed T155 walked the corpus anonymously
and reported "T152 onward absent", and the critique of T154 found the draft's
page answering Not Found even with the owner's key in a header. Both are
true of the pages. But `numberdb.table('T152')` with the owner's key in
`NUMBERDB_API_KEY` returned the draft's whole document, entries included, so
the build of T155 could read its three sibling drafts, their titles, tags and
entry counts, without Django. `search_text` does not return drafts.

What the skill says now: "`/drafts` lists what is being made right now and
is invisible from outside, so a table can be half-built and unfindable while
you start it again."

What it should say: add that the owner of a draft reads it through the API
as any table, `numberdb.table(tid)` with the owner's key configured, so a
run that holds the key can check its own earlier drafts by number before
starting a table again; what it cannot do is find them by search, which
answers with published tables only.

Evidence: `/tmp/ce_corpus.py`, 2026-09-06: `T152 | Site and bond percolation
thresholds of lattices | ... | entries 24`, `T153 ... entries 4`, `T154 ...
entries 23`, all three `published=False` in Django the same hour;
`search_text('percolation')` returned 0 hits.

## A citation remembered by author and subject names the right authors and the wrong paper

What happened: the critique of T155 asked for $\delta=15$ of the Ising
model to be cited to Camia, Garban and Newman, "Planar Ising magnetization
field II", Annals of Probability 44 (2016), arXiv:1307.3926, and said a
person should check it. The arXiv export API gave 1307.3926's abstract, which
proves tail and density bounds on the limiting magnetisation and not the
exponent, and the paper's own reference list named the theorem the critique
meant: "The Ising magnetization exponent on $\mathbb{Z}^2$ is $1/15$",
arXiv:1205.6612, Probability Theory and Related Fields 160 (2014), 175–187,
whose Theorem 1.1 is $\langle\sigma_0\rangle_{\beta_c,h}\asymp h^{1/15}$.
The journal the critique named belongs to paper I of the series.

What the skill says now: cite what the table declares, and put a reference
beside the value it supports.

What it should say: a reference recalled from memory is a hypothesis about
which paper proves the claim, not only about its volume and year; before it
goes in, read the abstract of the paper named, and if the theorem is not in
it, read that paper's reference list, which is where the right one was found
here. The arXiv export API and Crossref settle title, journal, volume and
pages in one call each.

Evidence: `/tmp/cgn1307.txt` line 1032 (`[CGN12b] … The Ising magnetization
exponent on Z2 is 1/15. preprint, arXiv:1205.6612`), `/tmp/cgn1205.txt`
line 70 (Theorem 1.1), Crossref DOI 10.1007/s00440-013-0526-8, 2026-09-06.

## A minimiser's uniqueness can be a sentence of calculus; scan only when it is not

What happened: T156 stores $c_k=\min_{\lambda>0}\lambda/\mathbb{P}(\mathrm{Po}(\lambda)\geq k-1)$
as `proven`, which needs the minimum to be the one found. The lesson above
on the Ising couplings proves a root unique by a monotone margin and an
adaptive ball scan. Here none of that was needed: with $T$ the tail and
$g=T-\lambda T'$ the numerator of $f'$, $g(0)=0$, $g\to1$, and
$g'=e^{-\lambda}\lambda^{k-2}(\lambda-k+2)/(k-2)!$ changes sign once, so
$g$ has exactly one zero and $f$ falls and then rises. The generator only
brackets that zero by a sign change of $g$; the proof is in the docstring
and the rigour details, and there is no scan to fail on the piece next to
the root.

What the skill says now: to check the claim the digits make by a sign
change across the enclosure; the lesson above adds a scan for uniqueness.

What it should say: before writing a uniqueness scan, differentiate once
more: when the derivative of the function whose zero is sought has a closed
form with an obvious single sign change, uniqueness is a sentence, the
scan is unnecessary, and the rigour details can state the argument instead
of describing a computation.

Evidence: `generators/k-core-thresholds/generate.py`, docstring and
`minimiser`; the dry run and the mpmath comparison of 2026-09-06, ten rows
agreeing to the last written digit.

## A proposal's "where a reader meets it" can name the wrong constant; check the application before writing it into a comment

What happened: proposal 6 said the 3-core threshold $3.3509$ "is the number
every simulation of random 3-XORSAT or cuckoo hashing meets, the 2-core
threshold of a random hypergraph being the same computation". It is not:
those problems meet the 2-core of a random 3-uniform hypergraph, whose
threshold by Cain and Wormald's $h_{d,k}$ is $c_{3,2}=2.4554$, that is
$m/n=0.8185$, and the graph's $c_3$ appears in neither. Written into a
comment as proposed, the table would have told a reader holding $0.818$ to
look for $3.35$.

What the skill says now: "verify a claim before writing it into a table,
including one somebody suggested", about identities and tags.

What it should say: the same for an application. A sentence saying which
problem a constant is met in is a claim about that problem; find the
formula the problem actually uses and evaluate it before the sentence goes
in. Where the proposal's application turns out to use a relative of the
constant, the table can say so, which is a better comment than the wrong
attribution.

Evidence: Cain and Wormald, Encores on cores, page 8, $h_{d,k}(\mu)=\mu/(e^{-\mu}f_{k-1}(\mu))^{d-1}$
with $m\sim cn/d$; `/tmp/kcore_plan.py` and the mpmath check of 2026-09-06
giving $2.45540748228413$ for $d=3$, $k=2$.

## When a publisher's page names nothing, the Semantic Scholar API carries the abstract

What happened: the check of $c_3\approx3.35$ against Pittel, Spencer and
Wormald needed their paper, and the Elsevier page behind
`doi.org/10.1006/jctb.1996.0036` answers `curl` with a JavaScript shell
that names nothing, as the batch had already found for IOP.
`https://api.semanticscholar.org/graph/v1/paper/DOI:10.1006/jctb.1996.0036?fields=title,abstract,year`
returned the abstract in one request, with the formula, $c_3\approx3.35$
and the $0.27n$ size of the newborn 3-core, its Greek letters replaced by
question marks but its digits intact. Crossref, from the same shell,
confirmed the volume and pages of all five references.

What the skill says now: cite papers; the lesson on `source_names_it` says
some publishers' pages name nothing.

What it should say: for a paper whose page names nothing, two public APIs
answer without a key: Crossref for the bibliographic record and Semantic
Scholar for the abstract, which is often enough to confirm a headline
value. Read a decimal from it with the same care as from a scan, since the
text is machine-extracted.

Evidence: 2026-09-06, the Semantic Scholar reply saved in the T156 run's
transcript; `generators/k-core-thresholds/table.yaml` cites the paper.

## "Of order $n$" is read as "on all $n$ vertices" by a graph theorist

What happened: T156's definition said that above the threshold the random
graph has "a $k$-core of order $n$", the random-graph idiom for
$\Theta(n)$, and its own comment used "order" two paragraphs later for the
exact number of vertices, $\mathbb{P}(\mathrm{Po}(\mu)\geq k)\,n$. The
critique read the definition with the page's own meaning and got a core on
every vertex. The repair says "a $k$-core on a positive fraction of the
vertices", which is what Pittel, Spencer and Wormald's theorem states and
what Łuczak's "no non-empty $k$-core with fewer than $\delta n$ vertices"
states. In the same comment the 2007 coauthor of Janson had acquired the
stroke of the 1991 author: Tomasz Łuczak and Malwina J. Luczak are two
people, and the bib entries had them right while the prose did not.

What the skill says now: the definition must let two people build the same
table; name the symbol, not its position.

What it should say: in prose, growth idioms ("of order $n$", "of size
$n$", "linear") name a rate, and the word "order" already means the number
of vertices in graph theory; write the fraction or "a positive fraction of
the vertices". And a name in the prose must match its own bib entry
character for character, diacritics included, because two people with
names one stroke apart are cited together in this field more than once.

Evidence: `agents/critiques/T156.md` findings 1 and 2; Janson and Luczak,
arXiv:math/0508453, Theorem 1.1 and Lemma 5.1; Crossref's record of
`10.1016/0012-365X(91)90162-U`; revision `fefa7dd9…` of T156.

## A secondary table's rows come from different generations; trace each row to its paper

What happened: Wikipedia's *Connective constant* table says its values
"are taken from the 1998 Jensen–Guttmann paper and a more recent paper by
Jacobsen, Scullard and Guttmann". Traced row by row on 2026-09-06: the
kagome value $2.56062$ is the 1998 number, and Jensen's 2004 paper on
lower bounds (arXiv:cond-mat/0409381) gives $2.560576765(10)$; the
Manhattan row prints $1.733535(3)$ where the paper it comes from
(Bennett-Wood, Cardy, Enting, Guttmann and Owczarek 1998,
arXiv:cond-mat/9805146) prints $\pm 0.000002$; the L-lattice row
$1.5657(15)$ comes from neither named paper and no source for it could be
found. The 2016 paper contributes the square row alone.

What the skill says now: read the maintained source on the day the table
is built, and cite the paper beside the value.

What it should say: a maintained table's sentence naming its sources is a
claim about the table as a whole, not about each row. Trace every row to
a paper before writing its uncertainty, take the paper's uncertainty over
the table's, and where a row cannot be traced, cite the table for that
row and say in the entry that it names no source.

Evidence: `/tmp/saw_jensen2004.txt` lines 277–281, `/tmp/saw_bwceo.txt`
line 87, the Wikipedia source read the same day; T157's kagome, Manhattan
and L-lattice comments.

## A digit string retyped by hand is the one input a value check cannot trust

What happened: the check of T157's honeycomb constant against OEIS
A179260 reported a disagreement at the 46th digit. The generator, mpmath
and the OEIS entry all agreed; the string in the check script had one
digit inserted while it was retyped from the entry's three data lines.
The temptation is to loosen the check; the fault was in its input.

What the skill says now: check the closed forms against OEIS to every
digit the entry lists.

What it should say: never retype a digit string. Paste the OEIS data
lines as served (`fmt=text`, the `%S`, `%T`, `%U` lines) and join them in
the script, so that the string under test is the served one. When a check
of a value against a source fails, compare the two strings position by
position before touching either the value or the check.

Evidence: `/tmp/cc_checks.py` and its two runs of 2026-09-06.

## A RealBall does not compare with a Python float

What happened: `1.84 < value < 1.85` with `value` a `RealBall` raised
`TypeError: unsupported operand parent(s)` in `sage -python`, while the
same guard with integers, `0 < value < 1`, had worked in the percolation
generator. A float has no coercion into a real ball field; an integer
does.

What the skill says now: nothing about comparing balls.

What it should say: guard a ball with integers, `184 < 100 * value < 185`,
or with a ball built from a rational; a Python float on either side of a
comparison with a ball is refused.

Evidence: the first run of `/tmp/cc_dry.py` under SageMath, 2026-09-06.

## Two readable routes to a headline value when the publisher's page names nothing

What happened: Clisby's 2022 growth constants for the fcc and bcc
lattices are behind an IOP page whose open-access PDF answers `curl` with
an HTML shell, and the paper has no arXiv version. Crossref's record
(`api.crossref.org/works/<doi>`) carries the abstract as JATS with MathML,
which stripped to its digits reads
$\mu_{\mathrm{fcc}}=10.03705785\pm0.00000014$; Semantic Scholar's record
carries the same abstract as plain text with both values. The two agree
digit for digit, which is the check a machine-extracted abstract needs.

What the skill says now (lesson of 2026-09-06 above): Semantic Scholar
carries an abstract a publisher's page hides.

What it should say: Crossref does too, for IOP at least, and where both
answer, read the value from both and compare, since each is extracted by
a machine. Semantic Scholar rate-limits after a few calls; Crossref did
not.

Evidence: the two replies for DOI 10.1088/1751-8121/aca189, 2026-09-06.

## The arXiv export API's author search is not a listing

What happened: `search_query=au:Clisby_N` sorted by date returned four
hard-sphere papers from 2003–2005 and none of Clisby's self-avoiding-walk
papers, and `au:Clisby_N AND au:Slade_G` returned nothing, while
`id_list=1302.2106` and title-phrase searches
(`ti:"improved lower bounds" AND ti:connective`) answered at once. A
search by author that comes back short is not evidence that a paper is
not on arXiv.

What the skill says now: the arXiv export API answers title, journal
reference and abstract for anything with an arXiv version.

What it should say: query it by identifier or by a phrase from the title;
an author query can miss most of an author's papers and says nothing when
it does.

Evidence: the searches of 2026-09-06 in the T157 build transcript.

## A URL's file name is not evidence of what it serves

What happened: Wikipedia cites Jensen and Guttmann 1998 with the URL
`ms.unimelb.edu.au/~tonyg/articles/polygons.pdf`; the Wayback Machine's
copy is a 4.4 MB PDF, and its text begins with the preface of a 2009 book
on polygons, polyominoes and polycubes. The paper itself was not found
anywhere readable, and its $(4,8^2)$ value is cited as quoted by two later
papers that print it.

What it should say: after `pdftotext`, read the first lines for the title
and authors before searching the text for a value; a value found in the
wrong document would have been attributed to the right paper.

Evidence: `/tmp/saw_jg1998.txt` lines 1–10, 2026-09-06.

## `sources` under Data properties is read as the provenance of the whole table

What happened: T157 was built from nine papers, with Wikipedia's table read
as the checklist, and its `Data properties` said `sources: [CITE{Wiki}]`
because that is the one source the build started from. The page prints
that field as "Sources of data: [16]", above the rows, and the critique
read it as the table being a copy of Wikipedia's, which then disagrees with
the kagome row on purpose. The field is a list, and the page prints it in
the order given; the repair listed the ten references the rows cite for
their values, in row order, keeping Wikipedia for the one row that rests on
it. `audit_table` has no rule for this and said nothing.

What the skill says now: `Data properties` holds `type`, `rigour`, how the
digits were obtained, and `repeats`; nothing about `sources`.

What it should say: `sources` names where the values came from, and a reader
sees it before any row. List every reference some row cites for its value,
in the order of the rows, and a survey or encyclopaedia only for the rows
that rest on it; a bound, a conjecture or an earlier enumeration cited in a
row's comment is not a source of the value and stays out.

Evidence: T157 revisions `9bc0bf7e…` and `cef47b4d…`, 2026-09-06;
`agents/critiques/T157.md` finding 1 and `T157-repaired.md`.

## OEIS may hold a number-field constant under an equation rather than a name

What happened: screening the batch of cubic-field tables, the regulator of
the cubic field of discriminant $-23$, $0.28119957432296184651\ldots$, was
searched in OEIS by its digits (`2,8,1,1,9,9,5,7,4,3,2,2,9,6`) and hit
**A202539**, "Decimal expansion of the number $x$ satisfying
$e^{2x}-e^{-x}=1$". Nothing in that name says regulator, unit or cubic
field; substituting $y=e^x$ gives $y^3-y-1=0$, so $x=\log\rho$ for the
plastic number $\rho$, which is the fundamental unit of that field, and
the entry is the regulator to 34 digits. The Weeks manifold volume
**A126774** is likewise $3\cdot 23^{3/2}\zeta_K(2)/(4\pi^4)$ for the same
field, and the OEIS digits agreed with PARI's $\zeta_K(2)$ to every listed
digit. Neither would have been found by any name.

What the skill says now: search OEIS by the digits of a small member; a
name search finds nothing.

What it should say: the same, plus: when the digit search hits an entry
whose name is an equation or an unrelated construction, solve it for the
family's object before dismissing the hit -- a regulator is the logarithm
of a unit and a unit is the root of its minimal polynomial, so "the $x$
with $e^{2x}-e^{-x}=1$" *is* a regulator once $e^x$ is substituted. The
same goes for a value that appears as somebody else's volume, period or
probability.

Evidence: `curl 'https://oeis.org/search?q=2,8,1,1,9,9,5,7,4,3,2,2,9,6&fmt=text'`,
2026-09-06, first hit A202539; `/tmp/nf_preflight.py` output, `bnf.reg`
for `x^3 - x - 1` = `0.281199574322961846512050764067878299792...`;
`/tmp/nf_preflight2.py`: `Weeks: 3 * 23^(3/2) zeta_K(2) / (4 Pi^4) =
0.942707362776927720921299603092211647590...` against A126774's
`9,4,2,7,0,7,3,6,2,7,7,6,9,2,7,7,2,0,9,2,1,2,9,9,6,0,3,0,9,2,2,1,1,6`.

## The first argument of an interval's `str` is the base

What happened: a root isolated with `f.roots(ring=RealIntervalField(400))`
was printed with `r.str(30)` to show thirty digits, and the output was
`1.9m7bgaos8a2cneck038hl0nn39b79roljj9th8400gmtis7citpr7qb994...?`. That
is the plastic number in base 30: `RealIntervalFieldElement.str(base=10,
style=None, ...)` takes the base first, and there is no digit-count
argument. The lesson above that `RealBall` has no `str` at all is the
same trap from the other side.

What the skill says now: print a ball's midpoint and radius separately;
nothing about intervals.

What it should say: to print an interval, use `r.str(style='brackets')`
or convert the endpoints with `RealField(n)(r.lower())`; a positional
integer is the base, and a string of letters after the point is not a
corrupted value.

Evidence: `/tmp/nf_preflight_out.txt`, 2026-09-06, the line `real roots of
x^3-x-1 (RIF): ['1.9m7bgaos8a2c...']`.

## An OEIS b-file with multiplicity is the completeness check for a field enumeration

What happened: the cubic fields with $|D|\leq 3000$ were enumerated by
brute force -- monic cubics with $|a_2|\leq 1$, $|a_1|,|a_0|\leq 60$,
`polisirreducible`, `nfdisc`, `polredabs`, collected by discriminant --
with no theorem that the box is large enough. The b-files of A023679 and
A006832 list a discriminant once *per field*: $972$ twice, $1228$ three
times, and so on. Comparing the count per discriminant with the b-file
(407 discriminants and 419 fields negative, 96 and 96 positive) made the
box's completeness a checked fact rather than a hope, and would have
caught a missed twin field as loudly as a missed discriminant. Sage's
`enumerate_totallyreal_fields_prim(3, B)` agreed on the totally real
side; the complex side has no Sage enumerator and only the b-file.

What the skill says now: check the count of a finite family against the
OEIS sequence that counts it (the knot lesson).

What it should say: for a family indexed by something with multiplicity
(fields by discriminant, forms by level), compare per index and with
multiplicity, not the total; and treat a brute-force box as complete only
after that comparison, which the generator should repeat every run.

Evidence: `/tmp/nf_preflight2_out.txt`, 2026-09-06: `complex distinct
|D|<=3000: 407 with multiplicity: 419`, `real distinct D<=3000: 96 with
multiplicity: 96`; `b023679.txt`, `b006832.txt` counted the same way.

## `lfunrootres` gives the residue; `lfun` at a negative integer gives a rational only with a bound

What happened: the residue of $\zeta_K$ at $1$ came from PARI in one line,
`lfunrootres(lfuncreate(pol))[1][1][2]`, and agreed to 60 digits with the
class number formula from `bnfinit` on eleven cubic fields -- two
computations sharing no code, which is the check T128 and T131 wanted.
`lfun(lfuncreate(pol), -1)` printed $-0.047619\ldots$ for the field of
discriminant $49$ and `bestappr(..., 10^6)` gave $-1/21$; the earlier
lesson says a bound is needed for `bestappr` to mean anything, and here
the bound has a name: Serre's theorem that the denominator of
$\zeta_K(1-2m)$ for totally real $K$ divides $w_{2m}(K)$ (to be read from
Serre 1971 or Coates 1977 for the exact statement before it is used). The
denominators seen today ($21$ for conductor $7$, $9$ for conductor $9$,
$1$ and $3$ for the non-abelian fields; $390=2\cdot3\cdot5\cdot13$ at
$s=-3$ for conductor $13$) are consistent with it.

What the skill says now: run a program before writing it; `bestappr`
needs a denominator bound.

What it should say: the same, plus the two PARI calls by name, and that a
rational recognised by `bestappr` is exact only when the bound is a
theorem the table cites.

Evidence: `/tmp/nf_preflight_out.txt` and `/tmp/nf_preflight2_out.txt`,
2026-09-06, the `lfunrootres` and `formula` lines, and `D=49 ...
zeta(-1)=... ~ -1/21 zeta(-3)~79/210`.

## A cypari2 method call computes at PARI's default precision, whatever `set_real_precision` says

What happened: the check for the cubic regulators (T158) compared each
value with PARI's own `bnf.reg` after `pari.set_real_precision(70)`, and
all 515 rows failed a 60-digit comparison at once -- the "all of them fail"
signature that says the checker. `g.bnfinit(1)` on a `Gen` runs at cypari2's
default working precision (PARI's 38 digits, `realbitprecision` 128)
regardless of `set_real_precision`, which sets the precision of the
interpreter and of printing; the printed regulator showed 40 correct digits
and then noise. The string form, `pari('bnfinit(%s, 1).reg' % f)`, honours
the setting and agreed to 60 digits on every row, as `lfunrootres` called
the same way had from the start.

What the skill says now: nothing about cypari2's two ways of calling PARI.

What it should say: in a check, call PARI through a string when the
precision matters, or pass `precision=` to the method; a value printed at
70 digits from a method call carries the default 38. And read a uniform
failure as the checker's before the table's.

Evidence: `/tmp/cf_check_out.txt`, 2026-09-06, first run with the method
form: 515 FAIL lines all `bnf.reg agrees to 60 digits`; second run with the
string form, `PASS 5230, FAIL 0`.

## `Polynomial.is_irreducible()` over $\mathbb{Z}[x]$ reaches for Singular under named imports

What happened: the Hunter-box enumeration of cubic fields tested each
`x^3 + a2 x^2 + a1 x + a0` with `f.is_irreducible()` in
`PolynomialRing(ZZ, 'x')` and died with `ImportError: cannot import name
PolynomialSequence_generic` from `sage.libs.singular.function`, through
NTL's factorisation and `Sequence`. The same call on the degree-12
polynomial of the connective constants, in `PolynomialRing(QQ, 'x')`, had
worked the day before. `pari(f).polisirreducible()` does the job for
either ring and shares nothing with the rest of the enumeration.

What the skill says now: "expect the machinery to be missing", with power
series, determinants and symmetric functions as the examples.

What it should say: add irreducibility over $\mathbb{Z}[x]$ to that list,
and name PARI's `polisirreducible` (and `nfdisc`, `polredabs`, `polgalois`)
as the route for number-field work: cypari2 is loaded by `numberdb.sage`
and answers in microseconds.

Evidence: the second probe run of 2026-09-06, `/tmp/cf_probe_out.txt`,
traceback ending in `sage/libs/singular/function.pyx`.

## Hunter's theorem makes a box of polynomials a complete enumeration of cubic fields; the OEIS b-files with multiplicity are its check

What happened: the proposal enumerated cubic fields with $|D|\leq 3000$ from
a box with no theorem behind it and asked that the b-files be the proof.
Hunter's theorem (Cohen, Thm 6.4.2) says every cubic field of discriminant
$D$ is generated by an algebraic integer of trace $0$ or $1$ with
$T_2\leq \frac13+\frac{2}{\sqrt3}(|D|/3)^{1/2}$, so its minimal polynomial
has $|a_1|\leq 18$ and $|a_0|\leq 43$ for $|D|\leq 3000$: 6438 polynomials,
tried in three seconds with `nfdisc` and `polredabs`, giving 407 negative
discriminants with 419 fields and 96 positive ones with 96, exactly the terms
of A023679 and A006832 up to 3000 counted with multiplicity, and for the
totally real ones the same fields as `enumerate_totallyreal_fields_prim`.
The constant in the bound is Hermite's $\gamma_2=2/\sqrt3$, which the corpus
holds.

What the skill says now: check against something independent; the earlier
lesson on OEIS holding the exact object under a real number.

What it should say: for a family indexed by number fields, an enumeration
needs a theorem that makes it complete (Hunter's, or Sage's totally-real
enumerator, which is Hunter's method) and an outside count that says it was
applied right; a b-file that lists a repeated discriminant once per field
gives the count with multiplicity, which catches a missed twin as well as a
missed field.

Evidence: `/tmp/cf_probe_out.txt` and `/tmp/cf_check_out.txt`, 2026-09-06.

## The unit that exceeds 1 is also the one that evaluates without cancellation

What happened: `bnfinit` returned, for the field of discriminant $-2991$,
the unit $-533048a^2-98122a+5164841$, whose real embedding is about
$3\cdot10^{-14}$: seven-digit coordinates summing to almost nothing, and the
ball for its logarithm at 400 bits had radius $6\cdot10^{-100}$ where every
other field had $10^{-116}$ or better. Its inverse, the representative with
real embedding above $1$ that the table shows anyway (T131's convention),
has thirteen-digit coordinates, a value of $3.5\cdot10^{13}$ and no
cancellation: radius $6\cdot10^{-138}$ at the same precision. In the totally
real case one of the three embeddings of a unit is always small and the
guard has to carry it; the worst entry there (D = 1772) still supports 133
digits at 461 bits.

What the skill says now: "state the guard as a constant with the measurement
behind it".

What it should say: when a value is the logarithm of an algebraic number
given by coordinates, pick the conjugate or inverse whose embedding is large
before evaluating, and expect the loss to show up as one ball far wider than
its neighbours; the dry run should print the worst radius and where it is,
which is how this was seen.

Evidence: `/tmp/cf_probe_out.txt` (`D=-2991 ... rad 6.31e-100`) against
`/tmp/cf_dry_out.txt` (`-2991,1 ... rad 5.96e-138`), 2026-09-06.

## The LMFDB's index among fields of one discriminant is data, not a rule; read it off the page

What happened: the proposal indexed cubic fields sharing a discriminant by
the lexicographic order of their `polredabs` coefficient vectors and hoped
the LMFDB's label index was the same. It is for $-972$, $-1228$ and $-1836$
and is not for $-1356$, $-2075$, $-2188$ and $-2891$ (at $-2891$ the LMFDB's
first field is the lexicographic third). The knowl `nf.label` says only
that the index counts from 1. The table keeps its own rule, states it, and
carries the label as read from each of the seventeen pages.

What the skill says now: never guess a name the database resolves; nothing
about somebody else's index.

What it should say: a label from another database is a fact about that
database; where the table needs one, read it from the page and say so, and
define the table's own index by something a reader can recompute.

Evidence: `/tmp/cf_src/lmfdb_3.1.*.html`, 2026-09-06, the defining
polynomials against `LMFDB_INDEX` in the generator.

## `lfunrootres` is an outside check on $h_KR_K$, and its residue is a Laurent coefficient

What happened: PARI's `lfunrootres(lfuncreate(f))` computes the residue of
$\zeta_K$ at $s=1$ from the functional equation and the Dirichlet
coefficients, sharing nothing with `bnfinit`; through the class number
formula it checked $h_KR_K$ on all 515 fields to 60 digits in a minute. The
answer is `[[[1, r]], [[1, R]], w]` where `r` is a Laurent series
`c*x^-1 + O(x^0)`, so the residue is `polcoef(r, -1)`, not `r` itself.

What it should say: for a table of regulators, class numbers or residues of
number fields, `lfunrootres` is the independent computation, and the string
form of the call gives it the precision asked for.

Evidence: `/tmp/cf_probe_out.txt` (the raw answer) and `/tmp/cf_check_out.txt`.

## A field's name is a property of the field, not of its reduced polynomial

What happened: T158 named a row $\mathbb{Q}(\sqrt[3]{m})$ when its reduced
polynomial was $x^3-m$, and five of the thirteen pure cubic fields with
$|D|\leq 3000$ went unnamed, because polredabs returns $x^3-x^2-3x-3$ for
$\mathbb{Q}(\sqrt[3]{10})$ and the like ($m=10,17,19,28,44$). The critique
proposed the rule "for $m\equiv\pm1\pmod 9$ the ring of integers is larger
than $\mathbb{Z}[\sqrt[3]{m}]$ and polredabs returns something else"; the
first half is true and the second is not, since $m=26\equiv-1\pmod 9$ has
index $3$ and polredabs still returns $x^3-26$. The repair recognises the
field instead: for $D=-3f^2$ it runs `nfisisom(x^3-m, f)` over cube-free
$m$ from $2$ up and names the first hit, which is also how the thirteen were
counted (every cube-free $m<1000$ with `nfdisc(x^3-m)` in range, deduplicated
by isomorphism).

What the skill says now: nothing about naming entries; the build prompt says
to use an entry comment "for a name a reader would recognise".

What it should say: when a name depends on the field and not on the
polynomial, test for the field (`nfisisom`, `is_isomorphic`) rather than
pattern-match the polynomial the reduction happened to return, and count the
named family independently so an unnamed member shows up as a count that
does not match. A rule read off the cases at hand ("these have
$m\equiv\pm1$") is a hypothesis to test on every member, not a sentence to
write.

Evidence: `/tmp/rep158_audit_before.txt` (the thirteen with $m$, index and
polredabs) and `/tmp/rep158_named.py` against the repaired generator,
2026-09-06.

## A number in the prose is data too: read it from the table, not from memory

What happened: the document of T159 gave, as the worked example of
$\kappa_K=|L(1,\chi)|^2$ at $D=49$, "$L(1,\chi)=0.5219\ldots+0.1700\ldots i$",
written from memory while the table's own check script was reading the true
value, $0.5377\ldots-0.1052\ldots i$, out of T145. The modulus squared of the
invented pair happens to be $0.301$, close enough to $0.3002$ that nothing in
the value checks could have noticed; it was caught only because the T145
entry was printed beside the document on the way to creating the draft.

What the skill says now: "Verify a claim before writing it into a table";
the batch's own lesson that polynomials from memory are wrong.

What it should say: every digit in the prose -- an example value, a
"$0.5255\ldots$", a bound -- is read from a stored entry or a computation in
the same run, never typed from memory, and the pre-creation lint of the
document should pull every decimal out of the prose and find it in the
table, in a linked table or in the check output; four digits are enough to
look right and wrong at once.

Evidence: `generators/dedekind-zeta-residues-cubic-fields/table.yaml` at
commit 2b93296 against its first draft; `/tmp/cr_src/T145.json` entry
`7/2/1`, 2026-09-06.

## PARI's `lfun` at an exact pole returns the polar part; Sage's `zeta_function().taylor_series` refuses it

What happened: `lfun(lfuncreate(x^3 - x^2 + 1), 1)`, at the pole of
$\zeta_K$, does not raise: it returns the Laurent polar part
`0.3684093207...*x^-1 + O(x^0)`, so the residue is `polcoef(..., -1)`,
as it is for `lfunrootres`. Sage's `K.zeta_function()` wraps the same PARI
object but `taylor_series(1, n)` fails with "series has negative
valuation", and the wrapper exposes nothing for a residue. The class number
formula from `bnfinit`, `2*Pi*bnf.no*bnf.reg/sqrt(abs(bnf.disc))`, is the
one-line program that prints the residue at the working precision; in Sage
`(2*pi*K.class_number()*K.regulator(proof=True)/sqrt(23)).n()` does the
same at 53 bits, and without `.n()` it stays a symbolic
`0.0244521368976489*sqrt(23)*pi`.

What the skill says now: nothing about residues or poles.

What it should say: for a residue of a Dedekind zeta function, PARI's `lfun`
at the pole and `lfunrootres` both answer with a Laurent series and the
residue is its $x^{-1}$ coefficient; Sage's zeta-function wrapper cannot be
asked for it, so the Programs section should offer `bnfinit`'s class number
formula, which a reader can run at any precision.

Evidence: `/tmp/cr_dry_out.txt` ("programs" block) and `/tmp/cr_probe2.py`,
2026-09-06.

## Two outside checks a residue table has for free: the LMFDB field page, and a digamma sum for the cyclic fields

What happened: every LMFDB number field page carries the residue to eleven
digits under "Analytic class number formula" (`\approx 0.36840932072` for
`3.1.23.1`), which the regulator build had not noticed; 21 of the 23 pages
cached for T158 gave a residue in range, and all 21 matched. For a cyclic
cubic field $\kappa_K=|L(1,\chi)|^2$ with $\chi$ cubic of conductor
$\sqrt D$, and $L(1,\chi)=-\frac1q\sum_a\chi(a)\psi(a/q)$ is a finite sum of
digamma values that arb evaluates as a ball -- the T128 method with
$\chi(a)=\omega^{\operatorname{ind}_g(a)}$ for a primitive root $g$ -- so
the seven cyclic rows have a proven computation sharing nothing with
`bnfinit` or `lfun`, and the four of conductor at most $29$ also have
T145's stored $L(1,\chi)$ for both cubic characters. `lfunrootres` remains
the only outside computation for the 508 non-cyclic rows.

What the skill says now: "Check new values against something independent."

What it should say: for a table of residues, class numbers or regulators of
number fields, the LMFDB field page states the residue (eleven digits) and
the regulator (twelve), read off the page; and where the field is abelian
the value is a product of Dirichlet $L$-values that the digamma sum proves
in ball arithmetic and that the corpus may already hold.

Evidence: `/tmp/cr_src/lmfdb_residues.json` parsed from `/tmp/cf_src/lmfdb_3.*.html`;
`/tmp/cr_stored_check_out.txt` (`LMFDB residues compared: 21`, `T145
comparisons: 8`, `PASS 5746, FAIL 0`), 2026-09-06.

## "The digits written are those the ball supports" is false whenever the ball supports more than `digits`

What happened: T159's rigour details said "The digits written are those
the ball supports (the worst entry, $D=1772$, supports 133)", and every
one of its 515 values is written to exactly 100 significant digits. The
client's `_decimal_text` writes the significant digits the ball's
endpoints agree on, capped at the generator's `digits`; a ball that
supports 133 is written to 100. The sentence described the cap's absence,
and a reader who went to $D=1772$ for the shortest value found it the same
length as every other. T158, built from the same template, says the same
thing and has the same 100-digit rows. Rebuilding all 515 T159 balls with
the generator's code and counting by the client's rule with the cap lifted
took 20 s in Sage: minimum 133 (three rows), maximum 138, and the 100
written digits of every ball equal to the stored value.

What the skill says now: that `publish` refuses a table whose values pin
down fewer digits than were asked for; nothing about how to describe the
written length in the rigour details.

What it should say: a proven table's rigour details should state the
written length and that the balls support more -- "each value is written to
$N$ significant digits, fewer than any ball supports (the worst supports
$M$)" -- and never that the written digits *are* what the ball supports,
since the client caps them at `digits`. $M$ is measured by counting the
significant digits on which the ball's endpoints agree, the client's own
rule; when the count ties, the row with the largest relative radius is the
one to name.

Evidence: `/tmp/rep159_balls_out.txt` (`min supported 133 at D = 1229`,
`WORST [(133, 1229, 1, 6.3e-136), (133, 1772, 1, 2.8e-134), (133, 2804, 1,
2.3e-134), …]`, `written == stored on all rows: True`), T159 revision
`cea741f5…`, 2026-09-06.

## `enumerate_totallyreal_fields_prim` lists primitive fields only, and a minimum can be imprimitive

What happened: the minimal-discriminant build (T160) used Sage's enumeration
of totally real fields as the independent check that nothing smaller exists.
`enumerate_totallyreal_fields_prim(6, 300125)` returned `[]`, which read as
"the value is wrong" until the field was looked at: the totally real sextic
of least discriminant, $300125=5^3\cdot7^4$, is the cyclic field of
conductor $35$, the compositum of $\mathbb{Q}(\sqrt5)$ and
$\mathbb{Q}(\zeta_7)^+$, and so has proper subfields. The `_prim` routine
lists fields with no proper subfield; `enumerate_totallyreal_fields_all`
(in `sage.rings.number_field.totallyreal_rel`) returned the field at once.
The quartic minimum $725$, a $D_4$ field with $\mathbb{Q}(\sqrt5)$ inside,
came out of `_prim` all the same, so the omission is not visible in degree 4.

What the skill says now: nothing about enumerating fields.

What it should say: a "nothing smaller exists" check by enumeration must
enumerate everything, and Sage's totally real enumeration comes in two
routines of which only `_all` does; a record is as likely to be attained by
an imprimitive field as not. And an empty answer from an enumeration is a
claim to be checked against the value's own structure (here: factor the
discriminant) before it is believed.

Evidence: `/tmp/md_probe_out.txt` (`n=6 bound=300125: 0 fields`) against
`/tmp/md_probe2_out.txt` (`n=6 bound=300125: 1 fields [[300125, x^6 - x^5
- 7*x^4 + 2*x^3 + 7*x^2 - 2*x - 1]]`), 2026-09-06.

## PARI's `isfundamental(1)` is true

What happened: the generator's check that no fundamental discriminant of the
right sign is smaller than $5$ scanned $t$ from $-4$ to $4$ and stopped at
$t=1$: PARI counts $1$, the discriminant of $\mathbb{Q}$, as fundamental. A
scan for quadratic fields has to skip it.

What it should say: in a scan over fundamental discriminants, exclude $1$
explicitly; `isfundamental` does not.

Evidence: `/tmp/md_dry_out.txt`, first run: `ArithmeticError: (2,0): 1 is a
fundamental discriminant smaller than 5`, 2026-09-06.

## A coefficient list typed from a displayed polynomial gets its terms swapped; nfdisc catches it, a reader does not

What happened: the septic $x^7-x^6+x^5-x^3+x^2-x-1$ was copied from OEIS
A343690's example line into a coefficient list by hand, and two middle
coefficients changed places ($-x^3$ and the missing $x^4$ term). PARI's
`nfdisc` of the list gave $-2560967$ with one real root, where the row said
$612233$ with three, so the check failed before anything was written. Every
other polynomial in the table was parsed out of a source's text or returned
by a computation, and none was wrong. The same run's first version of the
nonic for signature $(9,0)$ dropped a zero coefficient and came out of
degree $8$; the degree check caught that one.

What the skill says now: "polynomials from memory are wrong" (the batch's
lesson).

What it should say: a polynomial typed from a display is a polynomial from
memory with extra steps. Parse the source's text into coefficients
programmatically, or at least recompute its discriminant, degree and
signature before using it, and let a disagreement stop the run.

Evidence: `/tmp/md_probe_out.txt`, the `(7,2) ... FAIL` line, and the
`(9,0) is not monic of degree 9` traceback in `/tmp/md_dry_out.txt`,
2026-09-06.

## `NumberField(f)` under named imports fails inside `is_irreducible`; pass `check=False` once the polynomial is known irreducible

What happened: testing the document's Sage snippet in `sage -python` with
named imports, `NumberField(x^5 - x^3 - x^2 + x + 1)` died in
`polynomial.is_irreducible()` with `ImportError: cannot import name
PolynomialSequence_generic` (the factorisation reaches for Singular, as the
T158 lesson on `is_irreducible` says). `NumberField(f, check=False)` after
PARI's `polisirreducible` has said yes runs, and the snippet's claims
(`1609 (1, 2)`) were confirmed that way. In a full Sage session the snippet
runs as written.

What it should say: when a generator or a check needs a `NumberField` under
named imports, prove irreducibility with PARI and construct with
`check=False`; and say so in the report, because the substitution is the
environment's, not the program's.

Evidence: `/tmp/md_programs.py`, first and second runs, 2026-09-06.

## PARI `prodeulerrat` starts at its third argument

What happened: the Hardy-Littlewood singular-series generator needed Euler
product tails over primes beginning at $3$, $5$, $7$ and larger starts. The
PARI call `prodeulerrat(F, 5)` looked at first like it should start at
$5$, but it changes the exponent parameter $s$ instead. The start prime is
the third argument: `prodeulerrat(F, 1, 5)`. The control
`prodeulerrat(1-p^-2, 1, 2)=6/\pi^2` and
`prodeulerrat(1-p^-2, 1, 3)\cdot 3/4=6/\pi^2` fixed the convention before
the table was written.

What the skill says now: nothing about `prodeulerrat`.

What it should say: when using PARI's `prodeulerrat(F, {s=1}, {a=2})`, the
second argument is the exponent parameter and the third argument is the first
prime in the product. Run a known zeta-product control, such as
`prodeulerrat(1-p^-2, 1, 2)=6/\pi^2`, before using it as an independent
Euler-product engine.

Evidence: `/tmp/probe_hl_pari.py` and `/tmp/hl_identity_checks.py`,
2026-09-08; PARI's stable documentation lists the signature as
`prodeulerrat(F, {s = 1}, {a = 2})`.

## An OEIS prime-tuple product may be only the generic tail

What happened: the proposal's quintuplet value was based on multiplying OEIS
A269843 by $10$, but A269843 is the generic tail
`\prod_{p\geq7}(1-5/p)/(1-1/p)^5`, not the full Hardy-Littlewood singular
series. The finite local factor for the quintuplet offsets
$(0,2,6,8,12)$ and $(0,4,6,10,12)$ is $50625/2048$, so the full value is
$10.131794949996079843988427184867\ldots$, not
$4.09874885088236\ldots$. The same distinction occurs for triplet and
quadruplet entries: A065418 and A065419 are tail products, while A271886 and
A061642 include the usual finite factors.

What the skill says now: "Settle the convention" and "When two computations
disagree, neither is right until you know why."

What it should say: for Hardy-Littlewood and other local-factor Euler
products, read the OEIS formula, not just the name. An OEIS entry may record
the generic tail with small-prime factors stripped off; compare its stated
product range and local multiplier against the table's normalization before
using its decimal as an outside check.

Evidence: OEIS A269843, A065418, A065419, A271886 and A061642, and
`/tmp/hl_identity_checks.py`, 2026-09-08.

## A source's decimal places are not the same as NumberDB significant digits

What happened: the Mertens constants in arithmetic progressions were checked
against Languasco and Zaccagnini's published matrices, whose computation page
describes them as $100$-digit data. Comparing $100$ NumberDB significant
digits failed for entries near zero, including $M(8,5)$, while recomputing the
same accelerated formulas at higher precision did not move our value. The
authors' GP scripts hardcode the classical Meissel-Mertens constant to $100$
places after the decimal point, and their own matrix identities are consistent
at that scale. The table was therefore written at $95$ significant digits,
where every entry matched the matrices and every listed identity checked.

What the skill says now: it says to verify against something outside the
family and to check every identity, but it does not distinguish a source's
decimal-place promise from NumberDB's significant-digit entries.

What it should say: when an external source advertises decimal digits, check
whether that means places after the decimal point or significant figures. For
small values, a $100$-decimal-place source may not support $100$ significant
digits; either reduce the table precision or find an independent source with
extra places.

Evidence: `/tmp/mertens_full_check.py`, `/tmp/mertens_m_constant_probe.py`,
and draft `T164`, 2026-09-08.

## An arXiv identifier with a leading zero must be quoted in YAML

What happened: the repository copy of T164's document,
`generators/mertens-progressions/table.yaml`, carries `arxiv: 0906.2132`
and `arxiv: 0712.1665` unquoted. `yaml.safe_load` reads both as floats,
906.2132 and 712.1665, and a document built from that file would link to
the wrong arXiv abstracts. The stored draft has them quoted and renders
correctly, so the fault is latent, but every pre-2015 arXiv identifier
from January to September has a leading zero and the same thing happens to
each of them.

What the skill says now: nothing about quoting in the `References` block.

What it should say: in a YAML document, write `arxiv: '0906.2132'` with
quotes; an identifier that starts with a zero is a number to YAML and loses
it. The same applies to a `doi` or any key whose value looks numeric.

Evidence: `python3 -c "import yaml; print(yaml.safe_load(open(
'generators/mertens-progressions/table.yaml'))['References']['LZ2010']['arxiv'])"`
prints `906.2132`; the stored T164 document prints `'0906.2132'`,
2026-09-09.

## `source_names_it` cannot see a name with a diacritic

What happened: screening "Henon map Lyapunov exponents" against Sprott's
*Common Chaotic Systems* page, which tabulates the Hénon map's exponents,
reported that the source does not mention "henon". The page writes
"Hénon"; the screen lowercases the name, keeps `[a-z][a-z']+` runs, and
looks for the plain string. Spelt "Hénon map" in the query, the name would
have been split into "h" and "non" and matched almost anything.

What the skill says now: nothing about accents; the proposal prompt says to
run `source_names_it` on every source.

What it should say: strip diacritics from both the name and the page
(`unicodedata.normalize('NFKD', s)` and drop the combining marks) before
comparing, or screen the unaccented synonym and say in the proposal that
that is what was done. A "does not mention" on a name with an accent is
not evidence until one of those has been tried.

Evidence: 2026-09-09, `screen.source_names_it('Henon map Lyapunov exponents',
'https://sprott.physics.wisc.edu/chaos/comchaos.htm')` -> "does not
mention henon"; the page text contains "Hénon map ... Lyapunov exponents
(base-e): l = 0.41922, -1.62319".

## OEIS's JSON interface throttles a burst of `id:` queries and answers with HTML

What happened: about thirty `search?q=id:A...&fmt=json` requests in one
minute; from the twentieth or so every answer was a page that
`json.load` refused ("Expecting value: line 1 column 1"), which reads like
a bug in the query. The entry pages `https://oeis.org/A087492` answered
throughout, and the JSON interface answered again a few minutes later.

What the skill says now: the lesson "OEIS: one entry by id is
`search?q=id:A222072&fmt=json`" gives the query and nothing about rate.

What it should say: space the JSON queries out, or read the entry page
(the name is in the title and the digits in the EXAMPLE line, both
parseable with a regular expression); and treat a non-JSON answer as a
throttle, not as a wrong id.

Evidence: 2026-09-09, fifteen queries in a loop: the first fifteen fine, the
next batch of eight all `JSONDecodeError`; `https://oeis.org/A087493` read
"Decimal expansion of Khinchin mean K_{-3}" and its example line at the
same minute.

## The endpoints of a periodic window come from continuation in the multiplier, and the onset of a harmonic is singular

What happened: the onset (saddle-node) and the first period-doubling of a
periodic window of the logistic map are roots of resultants whose degree
runs to hundreds (A118454: 22, 40, 114, 12, 480, ... for the first window
of period 5, 6, 7, 8, 9), which Sage will not factor at period 9 on a
small machine. From the superstable parameter -- a root of the univariate
polynomial $f_r^p(1/2)-1/2$, cheap to factor exactly up to $p=8$ -- Newton's
method on $(f^p(x)-x,\ (f^p)'(x)-\mu)$ in the unknowns $(x, r)$, with $\mu$
moved from $0$ to $+1$ in a dozen steps, lands on the onset, and moved to
$-1$ on the doubling, at 400 bits in a fraction of a second per window. All
nineteen windows of period $\leq 7$ reproduced A086178, A086179, A118452,
A118453 and A118746 to every printed digit.

At $\mu=+1$ the system is singular for a word that is the period-doubling
(harmonic) of a shorter word: the $2p$-cycle there is born by doubling, not
by a saddle-node, the Jacobian is rank one, and Newton reports no
convergence while sitting on the right number, which is the parent's
doubling point.

What the skill says now: nothing on periodic orbits or bifurcation points.

What it should say: when a table holds bifurcation values, compute the
exact case (superstable parameters) by factoring and get the rest by
continuation in the multiplier from it, checking each against the exact
neighbour; expect and state the singular case for harmonics; and bracket
each root by a sign change in ball arithmetic before writing `proven`.

Evidence: `/tmp/logistic_probe2.py` on 2026-09-09: "RLLRLC p=6 onset
3.841499007543507846310702 ... WARNING: no convergence at mu = 1", against
A086179 = 3.8414990075435078463107027.

## Polynomial `.factor()` is another named-import trap

What happened: the entropy check for T169 built the integer characteristic
polynomial of each Markov transition matrix and then tried to factor it with
only named Sage imports loaded:

    import numberdb.sage as numberdb
    from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

The first call to `pol.factor()` failed while resolving Sage's polynomial
sequence machinery:

    ImportError: cannot import name PolynomialSequence_generic

Importing `sage.all` made the same two test polynomials factor, but the
generator cannot do that if it is to follow the skill and run on modular
passagemath. The retained generator therefore computes the characteristic
polynomial by the Faddeev-LeVerrier recurrence, finds the Perron root by
bisection, and keeps the already-computed Perron-root polynomials as text for
entry comments rather than factoring inside `value()`.

What the skill says now: with named imports, some Sage machinery can be
missing; it names power-series `.log()` and `.inverse()`, matrix determinants,
and `SymmetricFunctions(...).expand()`.

What it should say: add polynomial factorisation to that list. If a generator
needs a factor only to explain a value, factor it offline and store the
polynomial being cited; if the value itself needs the factor, write the small
integer-polynomial arithmetic needed for that table rather than importing
`sage.all`.

Evidence: `/tmp/logistic_windows_probe.py`, T169 build, 2026-09-09; the
traceback ends in `sage.libs.singular.function` importing
`PolynomialSequence_generic`. `/tmp/factor_probe.py` showed the same
polynomials factor after `from sage.all import PolynomialRing, ZZ`.

## Do not write the nested `/api/table` `Numbers` view back as a revision

What happened: after filling draft T168, a prose-only edit fetched
`/api/table?id=T168`, copied the returned `Numbers` section into the corrected
YAML, and wrote the whole document back through `/api/table/T168`. The public
client still verified all 48 values, but `agents/table-build/check.py`'s
`stored("T168")` read zero values: the head revision now held `Numbers` as a
nested mapping by parameter, while the stored-value check reads the flat
entry-list shape written by the generator. Rewriting the same document with
`Numbers` converted back to flat records repaired the check.

What the skill says now: it says to run `stored(tid)` after filling, and to
write through the API, but it does not say that the API's served `Numbers`
view is not the flat revision format the stored-value check expects.

What it should say: after a table has entries, a whole-document API edit must
preserve or reconstruct the flat `Numbers` list. Do not blindly copy the
nested `Numbers` object returned by `/api/table`; flatten it to records with
`params` and `number` before writing the document back, then rerun
`stored(tid)`.

Evidence: T168 on 2026-09-09; `/tmp/update_t168_metadata.py` first copied the
nested view, then repaired it by normalising 48 flat records; `verify()`
reported 48/48 in both states, while `stored("T168")` reported zero before the
repair and 48 after it.

## An asterisk inside `$...$` renders as a multiplication sign

What happened: the T169 draft writes each entropy row's polynomial into
the comment as Sage printed it, `x^4 - 2*x^3 + x^2 - 2*x + 1`, inside
`$...$`. `str()` of a Sage polynomial (and of a PARI or sympy one) puts a
`*` between coefficient and variable; MathJax renders `*` in math as the
operator $\ast$, so the reader sees $2\ast x^3$. Seven of 34 rows had it,
the ones with a coefficient other than $\pm1$; the 27 with unit
coefficients looked fine, which is why a spot check of the first few rows
passed. Nothing in `audit_table` or the API objects.

What the skill says now: nothing about how to get a polynomial into a
comment.

What it should say: use `latex(p)` (Sage) or `sp.latex(p)` (sympy) for a
polynomial that goes inside `$...$`, or strip the `*` with
`str(p).replace('*', '')` for a plain polynomial; never paste `str(p)`
into mathematics. Check the rows whose coefficients are not $\pm1$, since
those are the only ones that show it.

Evidence: T169 head c596c51d, rows `RLLLRC`, `RLLRRRC`, `RLLRLRRC`,
`RLLRRRLC`, `RLLLRRLC`, `RLLLLRRC`, `RLLLLLRC` (entropy), 2026-09-09;
`agents/critiques/T169.md` finding 3.

## An `HREF{...}` inside `$...$` breaks the formula on the page

What happened: T170's formula (5) reads `$e^\beta=HREF{E}[$e$]^{\beta}$
... with $\pi=HREF{Pi}[$\pi$]$`. The server renders `HREF` as an `<a>`
element, and MathJax does not let mathematics span an element (its
`includeHtmlTags` default is `br`, `wbr` and comments). The `$` pairs
re-form around the link, so the page shows a literal `$e^\beta=`, the
closed form of $L$ as raw TeX, and ", and" typeset as mathematics. The
YAML looks fine and `audit_table` says nothing, because every `HREF`
resolves.

What the skill says now: `HREF{slug}[text]` links a table; nothing about
where it may sit.

What it should say: `HREF` and `CITE` go in prose, never between `$` and
`$`. To link a constant that appears in a formula, write the formula and
then a clause after it: "..., where $\pi$ is HREF{Pi}[$\pi$]." The
Similar tables section usually carries the link already.

Evidence: T170 head 4ee3f1b0, formula `formula-levy-lochs`, 2026-09-09;
the rendered HTML in `/tmp/T170_render.html` line with `href="E"`;
`agents/critiques/T170.md` finding 1.

## `mpmath.nsum` returns wrong digits on a $\log k/k^2$ tail, silently

What happened: T170's Python program computes $K_0$ as
`mp.e ** mp.nsum(lambda k: mp.log(k) * prob(k), [1, mp.inf])` at
`mp.dps = 80`. Run as printed it gives $2.68502882972\ldots$ for
$2.68545200106\ldots$: wrong from the fourth digit, 80 digits printed, no
warning. The neighbouring $K_{-1}$ line, whose summand decays like
$k^{-3}$, is right to all 80 digits, and the same shape for $p=\pm\frac12$
is wrong in the second digit. `nsum`'s default extrapolation (Richardson,
then Shanks) assumes a tail it can model; a logarithm times a power is not
one. `method='euler-maclaurin'` gets 44 digits in twenty seconds; the zeta
series of Bailey, Borwein and Crandall gets 80 in a third of a second.

What the skill says now: a program on the page should reproduce a row;
nothing about `nsum`.

What it should say: run every program you put on the page and compare its
output with the row, digit for digit, before offering the table; a program
that prints a plausible wrong number is worse than none. Do not trust
`nsum` on a sum whose terms carry a logarithm or a fractional power unless
you have checked it against a tail bound or a second method.

Evidence: T170 head 4ee3f1b0, program `program-python`, mpmath 1.3 on
2026-09-09; the difference from the stored row is $4.2\times10^{-4}$;
`agents/critiques/T170.md` finding 3.

## An ambiguous object name can pass source search and still point at the wrong article

What happened: the Lyapunov-exponent table needed the continued-fraction
Gauss map $x\mapsto 1/x-\lfloor1/x\rfloor$. The obvious Wikipedia URL,
`https://en.wikipedia.org/wiki/Gauss_map`, is the Gauss map of a surface in
differential geometry, not the interval map for continued fractions. The
correct source was the "Dynamical systems" section of the simple continued
fraction article, which states the map used by the table.

What the skill says now: search the database and sources for the family and
cite what you declared; nothing says to disambiguate a source page whose title
matches a different object with the same name.

What it should say: when the table uses a short name shared by more than one
standard object, open the source and check that its defining formula,
normalisation and domain match the table before adding the link. If the source
is a section of a broader article, cite that section and write the formula in
the table definition or parameter value so the link cannot silently drift to a
namesake.

Evidence: 2026-09-09, opening Wikipedia's `Gauss_map` page gave the
differential-geometric map; the table cites
`https://en.wikipedia.org/wiki/Simple_continued_fraction#Dynamical_systems`
for the continued-fraction Gauss map.

## `RealBall.polylog(s)` is nan at $x=1$ and beyond; the complex ball gives $\zeta(s)$ and the principal branch

What happened: enumerating $\mathrm{Li}_s(x)$ over rationals in $[-1,1]$,
`RBF(1).polylog(2)` returned `nan` although $\mathrm{Li}_2(1)=\zeta(2)$ is
finite, and `RBF(3/2).polylog(2)` did too. `CBF(1).polylog(2).real()`
returned a ball overlapping `RBF(2).zeta()` at 118 digits, and
`CBF(2).polylog(2)` returned $\pi^2/4-i\pi\ln2$, the principal branch.
`RBF(-3).polylog(2)` is fine: the real function is only undefined on the
branch cut $x>1$, and arb's real ball treats the branch point $x=1$ as part
of it.

What the skill says now: "arb implements a great deal", with the real ball
field in mind; the Legendre-$Q$ lesson above says to try the complex ball
when the real one lacks a method.

What it should say: the same when the real ball *has* the method and
answers nan at an endpoint of its domain: evaluate on the complex ball,
check `imag().contains_zero()`, take `.real()`. For a polylogarithm, $x=1$
is such a point and $x>1$ is not real at all.

Evidence: `/tmp/probe1.py` and `/tmp/probe2.py`, 2026-09-09: `Li2(1) = nan`,
`CBF Li2(1) = [1.6449340668482264... ]  zeta2= [1.6449340668482264...]`,
`CBF Li2(2) = [2.4674011002723396... - 2.1775860903036021*I]`.

## `ComplexBallField.integral` is nan on an endpoint singularity; arb has the complete Beta function directly

What happened: to check $B(a,b)$ independently of the Gamma quotient, the
probe integrated $t^{a-1}(1-t)^{b-1}$ over $[0,1]$ with
`CBF.integral(f, 0, 1)` and got `nan` for $a=b=1/3$: the integrand is
unbounded at both endpoints and arb's integrator, which needs the integrand
analytic and bounded on each subinterval it encloses, reports that rather
than a wide ball. Meanwhile `RealBall.beta(a, z=1)` exists and is the lower
incomplete Beta function, which with the default `z` is the complete one:
`RBF(1/3).beta(RBF(1/3))` overlapped the Gamma quotient at 118 digits, a
second arb code path with no integral in it.

What the skill says now: the Legendre-$Q$ lesson names `integral` as the
rigorous integrator and says to pass `analytic` on; nothing about
singular endpoints, and the list of what arb implements has no `beta`.

What it should say: `integral` returns nan, not an enclosure, when the
integrand is singular at an endpoint, so it is not the check for a Beta or
Gamma-type integral; substitute the singularity away or use the identity
instead. And add `beta` to the list: `RealBall.beta(b)` is $B(a,b)$ and
`RealBall.beta(b, z)` is $B_z(a,b)$.

Evidence: `/tmp/probe1.py`, 2026-09-09: `int check B(1/3,1/3): nan`;
`/tmp/probe2.py`: `RBF(1/3).beta(1/3) = [5.29991625085634987194106849894531610...`
against `B(1/3,1/3)= [5.2999162508563498719410684989453161077...` from
three `gamma` calls.

## arb's ${}_2F_1$ returns nan in the logarithmic case when $c-a-b=0$ only up to a ball

What happened: `CBF(x).hypergeometric([CBF(1/3), CBF(2/3)], [CBF(1)])` is
`nan` for every $x\geq4/5$ tried, at 400 bits and at 1200, and so is
$(1/6,5/6)$; $(1/2,1/2)$ and $(1/4,3/4)$ evaluate at $x=99/100$ without
trouble. All four have $c=a+b$, the case in which the transformation to
$1-x$ degenerates and arb switches to a limit formula. arb decides whether
$c-a-b$ is an integer by an exact test on the balls, and $1/3$ and $1/6$
are not exact in binary while $1/2$ and $1/4$ are; passing $b=1-a$ as a
ball does not make the sum exact either, so for the inexact parameters
arb takes the generic path and its bound blows up near $1$. mpmath's
`hyp2f1` and PARI's `hypergeom` give $1.5632682129720699\ldots$ at
$x=9/10$ for $(1/3,2/3)$; so does the connection series DLMF 15.8.10,
$F(a,b;a+b;x)=\frac{\Gamma(a+b)}{\Gamma(a)\Gamma(b)}\sum_{k\ge0}
\frac{(a)_k(b)_k}{(k!)^2}[2\psi(k+1)-\psi(a+k)-\psi(b+k)-\ln(1-x)](1-x)^k$,
summed by hand in balls with `psi` (400 terms, no tail bound, agreeing to
mpmath's 40 digits for all four parameter pairs and to arb's 118 for the
two arb answers); and the Borweins' cubic AGM does for $(1/3,2/3)$.

What the skill says now: "arb implements a great deal (... `agm`, ...)";
nothing about the hypergeometric function, and nothing about arb's exact
tests on parameters.

What it should say: arb's special-case detection is exact, so a parameter
that is a non-dyadic rational is never "an integer apart" from another,
and a ${}_2F_1$ with $c-a-b\in\mathbb Z$ can come back nan near $x=1$ for
parameters like $1/3$ and work for $1/2$. The remedy is the connection
formula written out in balls, with its tail bounded, or an identity
(AGM, quadratic transformation) that avoids the degenerate point.

Evidence: `/tmp/probe3.py` and `/tmp/probe5.py`, 2026-09-09: the table
`4/5 ['ok', 'nan', 'ok', 'nan'] sig3 at 1200 bits: nan`;
`connection series sig 6 at 9/10: [1.3396472448926916436465777892380765268925...`
against `mpmath 1.339647244892691643646577789238076526893`.

## Do not round-trip `numberdb.table()`'s nested `Numbers` through a full-document edit

What happened: after T175 was filled by its generator, a prose-only repair
read the draft with `numberdb.table('T175')`, replaced the prose from the
repository `table.yaml`, and copied `current['Numbers']` into the document
sent to `/api/table/T175`. The API read had returned `Numbers` in nested
form, keyed by `s` and then `t`; the full-document write accepted that, and
`generator.verify(sample=None)` still reported 538/538 matched. But
`agents/table-build/check.py`'s `stored('T175')` reads the record-list form,
so the stored-value identity check saw zero entries until the numbers were
flattened back to records with `params: {s, t}`.

What the skill says now: "Check the identities again on the values read back
out of the database" and names `stored(tid)`, but nothing says that an API
table read may not be safe to copy back as the `Numbers` section of a
full-document write.

What it should say: after a generator has filled a table, do not preserve
entries for a full-document prose edit by copying `numberdb.table(tid)['Numbers']`
straight into the outgoing document. Use the entries endpoint for entries, or
normalise the returned nested `Numbers` to the record-list form before a
whole-document write. Then run `stored(tid)` before trusting identity checks
on stored values.

Evidence: T175 revision `c6b94ed13a4c1895c5063b9204bf78de634bf6184c3f297f0c738de3004c478c`
had nested `Numbers`; `/tmp/clausen_stored_checks.py` printed `stored
entries: 0` on 2026-09-09. Revision
`0268499f30aa5c92cca226c29135a0bbea0443c0033ed2d9efd9cd525accb1c4`
flattened the same 538 entries, after which `stored('T175')` saw all 538 and
the Hurwitz, zeta and beta checks passed.

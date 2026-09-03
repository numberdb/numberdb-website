# Stage four: act on a critique, or say why you did not

Stage three read a table and wrote `agents/critiques/<TID>.md`. You have that
report. Your job is to make the table right where the report is right, and to
leave it alone where the report is wrong.

**The report is a set of proposals, not a set of instructions.** It was
written by an agent reading a page, without running anything, possibly hours
ago. On the ten critiques written so far, acting on them needed judgement four
separate times, in four different ways. Each of those is a rule below.

## Before you change anything

**Re-read the live document.** `GET /api/table?id=<TID>` and the rendered page
at `https://numberdb.org/<TID>`, now. Two findings in the first batch had
already been fixed by the time anybody acted on them: T133's whole list, and
T132's "sixteen entry comments say it identifies nothing", which were gone.
A repair that re-breaks a fixed thing, or that edits around text which is no
longer there, is worse than no repair. If a finding no longer applies, say so
and move on.

**Check the claim, do not transcribe it.** A finding that asserts a fact about
the mathematics is a hypothesis until you have checked it:

* T127's proposed comment gave an asymptotic for how close the zeros sit to
  half-integers. It was derived from scratch before it went in, and the
  derivation is what made it safe to write: the terms cancel in pairs at the
  midpoint and the remainder is the unpaired tail.
* T132's proposed sentence about the degrees of nodes and weights was checked
  in Sage for every rule in the table, and then *narrowed*, because it rests
  on an irreducibility that is checked and not proved. What went in says "for
  the rules here".
* T134's program fix was run before it was written down, and the output
  compared against the numbers printed beside it.
* T135's replacement invoked Schur's theorem; irreducibility was confirmed for
  every $n$ the table holds before the citation was added.

`agents/sage.sh` runs a file under Sage. Use it. A claim you could have
checked and did not is the one that will be wrong.

**Narrow a claim rather than dropping it.** When a proposed sentence is true
for the entries here but not in general, scope it to the entries here. That
is more useful than silence and more honest than the general statement.

## When you write

**Everything the build prompt forbids applies to you.** Read
`agents/table-build/PROMPT.md`. You are writing prose into a table, and the
repairs are exactly where the faults reappear: a repair for T135 was drafted
with "the two polynomials **below**" in it -- the positional pointer the
prompt bans and `audit_table` now refuses -- and it was caught only by reading
the draft back before sending.

**Watch the seams.** Moving a sentence leaves the sentence after it holding a
pronoun with nothing to refer to. Moving the definition of $E_{n+1}$ out of a
comment in T136 left "Its roots are real" behind, and the first attempt at the
repair produced "The roots of $E_{n+1}$ its roots are real". Read the whole
paragraph you changed, not the line.

**Print the change before you send it.** Then read it as prose.

## How to write it

Through the API, as yourself, with the key you were given. Never
`commit_table`, never a shell on the server: those walk past the permission
checks, the rate limits and the validation, and they record a channel that is
not the one you used.

The document you `GET` can be written back as it came: the read endpoint
serves the keys in the order the table stores them. If a write is refused with
`This edit changes the table parameters`, stop and report it -- something has
reordered the document and that is a fault worth a person's attention, not
something to work around.

**Your edits wait for a person.** An operated account's edits are never
published as reviewed, so what you write lands in the review queue whatever
you do. That is the safety net; it is not permission to be careless, because
a reviewer reading twenty confident edits will click through them.

**You may not publish, and you may not review.** Not your own work, not
anything else's.

## Afterwards

**Run `manage.py audit_table <TID>`** on what you produced, and read what it
says. If you introduced a finding, fix it before you finish.

**Write `agents/critiques/<TID>-repaired.md`**: one line per finding in the
original report, saying which of

* *done* -- what you changed, and what you checked before changing it
* *already fixed* -- it was not there any more
* *declined* -- why the finding is wrong, or why the change would cost more
  than it gains
* *left for a person* -- it needs a decision that is not yours

and nothing else. A reviewer reads that file beside the critique to see what
happened, so make the two line up finding for finding.

**Say when you changed nothing.** A report whose findings were all already
fixed, or all wrong, is a good outcome and a short file. Do not manufacture an
edit to justify the run.

# Design: users editing content on the website

Status: proposed
Supersedes: the GitHub round trip documented in `help.html`
(preview on site → copy YAML → paste into GitHub → commit → an editor reviews)

## Summary

Move the store of record from the `numberdb-data` git repository into the
database, and let people create and edit tables on numberdb.org.

Every edit is a **complete table snapshot**, committed with a parent and a
base, and **published immediately** in the manner of Wikipedia. Review happens
after the fact and does not gate visibility. It gates one thing only: whether
a value is allowed into **search by number**.

That single asymmetry is what makes immediate publication safe here. A reader
who lands on a page can see that it is unreviewed and judge accordingly. A
person typing a number into the search bar cannot: a wrong fortieth digit
looks exactly like a right one, and the whole purpose of the site is that
finding a number there means something.

The data repository does not disappear. It becomes a generated export, so the
corpus stays citable, forkable and downloadable, and so nothing about this is
irreversible.

## What is actually there today

Worth stating precisely, because more of this exists than it first appears.

**The corpus is uniform.** All 109 tables carry the same fourteen top-level
keys in the same order, then either `Numbers` (99 tables) or `Data` (10, all
polynomial tables via `INPUT{polynomials.yaml}`). Entries nest one to three
levels, one level per parameter, over roughly 50000 leaf values. That
uniformity is the reason a form-based interface is plausible at all.

**Half the editor already exists.** `views.preview` accepts YAML in a
textarea, validates it, and renders the table exactly as it will appear,
including error messages for malformed YAML. It is stateless and anonymous:
what is missing is identity, persistence, history and review, not rendering.

**The database already holds the source.** `TableData` stores `raw_yaml` (the
original `table.yaml`), `full_yaml` (normalised, `INPUT{}` resolved) and
`json`. The editable text is already in Postgres; today nothing may write it.

**Identity is already stable.** `id.yaml` carries a permanent `T`-number
("Automatically created file. Do NOT edit"), and `/T7` and `/Pi` both resolve,
with `#<params_id>` anchoring a single entry. This is the same arrangement as
an OEIS A-number, and it is the right foundation.

**Mail has never worked.** Production runs
`django.core.mail.backends.console.EmailBackend`: every verification message
is printed into the container log and delivered to nobody. `anymail` is in
`INSTALLED_APPS` with no configuration block and no provider key on the
server. `ACCOUNT_EMAIL_REQUIRED` is `False` and `ACCOUNT_EMAIL_VERIFICATION`
is `'optional'`. All three must change before accounts can own content.

**Cross-references degrade gracefully.** `HREF{}` is a plain string
substitution into an anchor (`views.py:288`); there are 125 internal
references across 22 targets. A reference to a table that does not exist
renders as a dead link rather than an error, which is what makes partial
acceptance of a bulk proposal tolerable.

## Identity and trust

Three tiers, deliberately not two:

| Tier | How | May do |
|---|---|---|
| Account | email (verified), Google, GitHub | edit; edits publish immediately, marked unreviewed |
| Verified identity | ORCID, later MediaWiki | as above, plus higher submission limits and a visible marker |
| Board | granted by Benjamin, who may delegate | mark revisions reviewed; own edits are reviewed on save |

**ORCID confers identity, not standing.** An ORCID iD is free and
self-registered, with no institutional check, so treating it as automatic
trust would be a very thin gate on exactly the failure that matters: a wrong
digit entering the index unreviewed. It is worth having because it is a
persistent, publicly staked identity that a throwaway account is not. It makes
someone *eligible*; it does not make them trusted.

Board membership starts as one person and is delegable. Nothing in the model
depends on the board being large; it depends on the review pointer described
below, which degrades honestly when nobody has looked at something yet.

### Earning trust

Trust is granted by a board member, or automatically after **N reviewed edits**
that have not been reverted, where N defaults to 5 and is read from settings so
it can be tuned without a rebuild (the pattern `NUMBERDB_MAX_RELATIVE_WIDTH`
already uses).

Measured against the contributors the project actually has, auto-promotion will
rarely fire: of the four contributors to date, two made 3 and 1 table commits
respectively, and would never reach any threshold worth having. Manual grant is
therefore the mechanism that matters now; auto-promotion is a valve for a
busier future, not the main path.

Three conditions beyond the count, all cheap and all guarding against the way
edit-count gates are usually defeated:

- the qualifying edits must be **reviewed and not reverted**;
- they must span **at least two tables**, so five typo fixes to one page do not
  qualify;
- the account must be **at least a few days old**, which is what stops a burst
  of trivial edits from converting straight into trust.

At least one qualifying edit should have **touched a numeric value**. Trust
grants auto-review, and auto-review puts digits into the search index without
anyone checking them; edits to comments are no evidence at all about that.

Trust is revocable, and revoking it should return that author's
self-reviewed commits to unreviewed.

**Identities must be merged before counts mean anything.** The current corpus
already shows one person as two contributors (243 and 39 commits under two git
identities). A per-identity edit count silently splits in that situation.


## The commit model

Borrowed from git, because the semantics are already understood by everyone
who will work on this, and because "what did this table look like last March"
must have an answer.

A **commit** is a complete snapshot of one table (the metadata document and
its entries), together with:

- `parent`: the commit it was applied to. Normally `HEAD` at the time.
- `base`: the commit the author actually edited from.
- `author`, `time`, `message`, and, when applicable, the tool that produced it.

`parent` and `base` differ exactly when someone else committed while an edit
was being written, and that difference is what makes a stale write detectable
instead of a silent clobber.

Snapshots are stored content-addressed and deduplicated; diffs are computed
for display rather than stored. The largest `numbers.yaml` in the corpus is
98 KB, so even hundreds of revisions per table costs nothing worth optimising.

### Merging

History is linear whenever one person is editing, which is nearly always. When
two people edit concurrently, the second commit is merged against the first,
and **the merge is itself a commit** with two parents.

The merge is **structural**, over the parsed tree, not textual over lines.
This matters more than it sounds: line-based merging of YAML conflicts on
reflowed text, reordered keys and changed indentation, none of which are
changes to the data. Merging the tree instead gives:

- edits to different entries (`n=5` and `n=17`): disjoint keys, merged
  automatically, deterministically;
- edits to the same entry, or to the same metadata field: a real conflict,
  presented side by side for a human to resolve;
- no conflict ever caused by formatting.

So the unit of record is the whole table, as decided, and concurrent edits to
different entries still cost nobody anything.

## Review, and what it gates

Every commit is **live on save**. There is no draft state and no queue holding
content back from readers.

Each table carries a `reviewed_at_commit` pointer. Everything between that
pointer and `HEAD` is unreviewed. A board member moves the pointer forward; a
board member's own commit moves it forward on save.

**The set of unreviewed values is the diff** between `reviewed_at_commit` and
`HEAD`. This is precise rather than table-wide: correcting one comment does
not cast doubt on 10000 untouched entries.

Those values are:

- **shown**, on the table page as usual;
- **marked**, with the existing dagger-and-tooltip mechanism, which already
  exists for numbers too imprecise to identify anything and already links to
  an explanation in the help page;
- **excluded from search by number**, until reviewed.

Text and metadata search are not gated. Finding a table by its title is not a
claim about the correctness of its digits.

A table that has never been reviewed has no pointer, so all of it is
unreviewed. That is the honest default, and it gives review an obvious
purpose: an entry is not findable by value until someone has confirmed it.

### Why this is safe without a queue

The Wikipedia bet is that immediate publication plus easy reversion beats
gatekeeping, because vandalism is obvious and cheap to undo. That bet fails
for numeric data, where an error is invisible. Gating the index rather than
the page keeps the bet intact where it works and declines it where it does
not.

Supporting machinery, none of it novel: one-click revert (which is itself a
commit), notification to the board on any edit to a watched table, and rate
limits per account.

## Editing surfaces

The source view stays permanently, and forms are added beside it. They are two
views of **one document**, never two documents, and the user may switch at any
point without loss.

Three surfaces, because the content is genuinely of three kinds:

1. **Prose carrying LaTeX and macros** (`Definition`, `Comments`, `Formulas`,
   `reliability`): a source pane with live preview beside it, rather than true
   WYSIWYG. The renderer already exists, and WYSIWYG for LaTeX tends to fight
   the author.
2. **Structured metadata** (`Parameters`, `Data properties`, `Display
   properties`, `Tags`, `References`, `Links`): ordinary forms, with choices
   populated from the vocabulary actually in use: 7 parameter types, 8 data
   types, the three states of `complete`, repeatable rows for references.
3. **The entries**: a spreadsheet-like grid of parameter columns, value and
   comment, accepting paste from a spreadsheet or a Sage session. Nearly all
   the volume lives here (10828 entries, 9288 comments), and for a database of
   numbers the natural direct-manipulation editor is a grid rather than a
   document editor. It maps exactly onto per-entry structural merge.

**Forms must round-trip what they do not understand.** If editing a title
through a form silently drops `layout: nested lists`, `group parameters`, or a
`Set`-typed parameter because no widget exists for it, the UI has destroyed
data while appearing safe. Unknown keys are preserved verbatim, and shown
read-only with a pointer to the source view.


## Bulk and machine-authored proposals

Same queue, same commit model. A bulk submission of N tables is **N
independent commits sharing a label**; the label exists for triage and
attribution, not as an atomic unit. Accepting a subset is therefore the
ordinary operation rather than a special case.

Two consequences worth designing for:

**Dangling references are tolerable but should be surfaced.** Accepting a
commit that references a table not yet accepted yields a dead link, not an
error. Warn the reviewer; do not block.

**Review effort is the real constraint.** Two hundred generated tables take
minutes to produce and days to review honestly. Effort spent on making triage
cheap (grouping similar proposals, compact diffs, one decision covering a
uniform batch) is worth more than effort spent on the generation side. A cap
on outstanding proposals per account keeps one enthusiastic run from creating
a year of backlog.

**Machine-written commits are attributed as such**, naming the tool or model
and the person who submitted them. Reviewers triage differently when they know
something was generated, and readers are entitled to know. This is why
Wikipedia flags bot edits.

## Making the corpus machine-writable

Designed early rather than late: if a program can only drive the site by
pretending to be a browser, the interface is wrong.

1. **A published JSON Schema** for the table document, generated from one
   definition shared by the forms, the validator and the API. A model writes
   far better YAML against a schema it can fetch than against prose and 109
   examples.
2. **A validate endpoint**: post a candidate, receive errors, warnings and
   the rendered result, writing nothing. This is `views.preview` with a JSON
   response, and it lets a generator close its own loop.
3. **Addressable, idempotent writes**, keyed by `T`-number and parameter
   tuple, so "add the fortieth coefficient" is well defined and safely
   retryable.
4. **Everything lands as a commit**, subject to the same publication and
   review rules as a human edit. No privileged path.
5. **Volume controls**: per-account rate limits and a bulk object a reviewer
   can accept or reject wholesale.

The client package is the natural home for the write side: it already handles
authentication, batching and the wire format, and `numberdb.propose(...)`
beside `numberdb.search(...)` is coherent. An MCP server on top of a good HTTP
API is a small wrapper; an MCP server *instead of* one is a trap.

## Schema normalisation, first

Small, and it removes a special case from every form, importer and validator
written afterwards.

**`complete` already has a vocabulary; two entries escape it.** Read with
`yaml.BaseLoader`, which is what every reader in this codebase uses, the
corpus says:

| value | tables |
|---|---|
| `no` | 73 |
| absent | 23 |
| `yes` | 6 |
| `unknown` | 5 |
| `yes, assuming GRH` | 1 |
| `unknown (presumably not)` | 1 |

An earlier draft of this document reported 73 booleans, having surveyed the
files with `yaml.safe_load`. That was measuring the loader rather than the
data: YAML 1.1 turns `yes` and `no` into booleans, and no file has ever
contained `True` or `False`. The codebase is not affected, because every reader
uses `BaseLoader` and sees the strings, but it is a good illustration of why
the survey and the code should agree about how a file is read.

So the field is already three-valued. What is missing is somewhere to put the
qualifier, which two tables append into the value itself and no dropdown can
represent. The proposal is therefore small: keep `yes | no | unknown`, and add
an optional `complete-note` carrying `assuming GRH` or `presumably not`.

**One concept, one spelling.** `arXiv` (14) and `arxiv` (4); `MR` (7) and
`mr` (2); `Numbers` (99) and `Data` (10). The renderer now matches reference
keys case-insensitively, which is the tolerance a contributor typing into a
form will need anyway, so this is tidiness rather than a bug.

**Prefer zbMATH to MathSciNet in new references.** Both are supported and an
`MR` number is real information worth keeping, but zbMATH Open serves its
records to anybody, while an anonymous MathSciNet request returns a JavaScript
shell and a subscription behind it. Checked rather than assumed, in August
2026. A form should offer `zbl` first and `doi` above both, since a DOI needs
no index at all.

**Leave `reliability` alone.** It is genuinely free prose with citations,
sometimes several sentences, and it is mathematical hedging rather than
metadata.

**Say generated-or-curated explicitly.** It is currently conveyed only by
whether a `generate.sage` happens to sit in the folder.

## Generator scripts

The 82 `generate.sage` files produced values that were then copied into the
YAML by hand. So the YAML is already the truth and the scripts are
*provenance*, not a pipeline: there is no regeneration step for hand edits to
collide with.

Keep them as attached artifacts, displayed, citable and downloadable, but
never executed by the server. Running a contributor's Sage on submission is a far
larger exposure than evaluating a search expression, and the sandbox was not
built for it.

## Mail

Required before any of this works, and independent of the rest.

Use Mailgun through Anymail, which is already installed. An earlier draft of
this document recommended Resend on the grounds of simpler setup and a free
tier; that was written without knowing that numberdb.org's sending domain was
already verified at Mailgun. Since domain verification and sending reputation
are the actual work, and both are already done, switching would cost real
effort and money to gain almost nothing. The provider is selected by whichever
API key is present, so the decision stays reversible.

The provider is not the hard part. Deliverability for a new sending domain is,
which is the whole reason to stay where the domain is already verified. Send
from a subdomain such as `mail.numberdb.org` rather than the apex, so that a
deliverability problem never threatens the reputation of the domain the site
itself is served from.

Three things had to be wrong at once for mail to be as dead as it was, and all
three were: `anymail` installed with no configuration block, an explicit
console `EMAIL_BACKEND` in the server environment that would have overridden
any key, and `EMAIL_MG_API_KEY` documented in `env/.env.prod.example` but read
by no code at all. Setting the key is now the entire configuration, and a
system check reports it when mail goes nowhere.

## URLs

`T`-numbers become canonical. Slugs remain, semi-stable, and redirect to the
canonical URL; renaming a table is therefore allowed and costs a redirect.
Emit the canonical link in pages and in API responses from the start, so
citations made from today point at something permanent.

## Discussions

One thread per table, in the manner of a Wikipedia talk page, and one per tag.

Per entry was considered and rejected as the starting point. It would suit a
corpus whose entries already carry `comment`, `proof` and `equals`, and it is
the thing OEIS lacks, but it multiplies the number of objects that can be
watched, notified and moderated by roughly ten thousand, for conversations that
are usually about the table anyway. An entry-specific point is made in the
table's thread, and the entry is already addressable: every one has a permanent
anchor of the form `/T7#<params_id>`, so a comment can link precisely to the
value it is about without the discussion itself having to live there.

Referring to a single entry has to be effortless, or the distinction collapses
into "discussions are about tables". Each row in the table should offer its own
link, and the comment box should turn a pasted `#<params_id>` into the value it
names, so a thread reads as a conversation about numbers rather than about
anchors.

Tags get threads because a tag is where a question of scope belongs. "Should
this table be tagged transcendental" has no natural home on any single table.

Nothing here forecloses per-entry threads later: a thread already has to record
what it is attached to, and adding a second kind of anchor is a migration
rather than a redesign.

## The export is what closes the loop

Until it exists there are two places to change the same table, and the site is
running with the second one disabled by hand rather than by design:

* editing through GitHub is no longer offered. The link reads "source on
  github" and is for reading, citing and forking.
* `delete_all_tables()` refuses to run once any table has been edited here,
  because `Table` cascades to `TableRevision` and a full rebuild would delete
  every site edit and its history without a word, then rebuild rows from the
  repository so that the result looked entirely normal.

Both are stopgaps. The database is the store of record, so the repository has
to become a **generated export**: a job that writes each table's head revision
back out as YAML and commits it. That restores the repository's purpose (a
citable, forkable, downloadable corpus) without it being a second place to
write, and it retires the guard, which currently prevents a rebuild that will
one day be wanted.

Creating a new table still goes through the repository, so the import path
cannot simply be removed; it needs to become "import tables that do not exist
here yet" rather than "delete everything and rebuild".

## Risks

**Immediate publication with a small board.** With one reviewer, the
unreviewed set grows without bound, and the numeric search index quietly stops
covering new material. Mitigation: the marking makes this visible rather than
silent, and it is the honest state of affairs. It is also the strongest
argument for delegating early.

**Structural merge is subtle.** It must be tested hard, especially around
deletions and reordering, because a merge that silently drops an entry is
worse than a conflict.

**One-way export can drift.** If the git mirror is ever edited directly, the
two diverge with no reconciliation path. The export should be plainly marked
as generated, and the data repository's write access restricted accordingly.

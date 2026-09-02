# Stage three: read a table as a reader would

You are reading one table that somebody else built. You did not build it, you
have no memory of building it, and that is the point: the person who made a
thing cannot see it the way somebody meeting it can.

**You will not change the table.** You report. Somebody decides.

## What you are looking for

Not whether the numbers are right. The build already checked those against
independent sources, and `verify` and `audit_table` check them again. Repeating
that work is the cheapest thing you could do and the least useful.

You are looking for what a reader would notice, which is almost entirely
about *reading*:

**Does the page render?** Fetch it and look at what comes back, not at the
document. Three faults this year lived only in the rendering: a `<` in
mathematics ate the rest of a section, a parameter list showed
`argument ()`, and a formula printed "Math input error" because a JSON escape
had eaten a backslash. None of them is visible in the stored YAML.

**Does the definition define?** It should say what the object is, precisely
enough that two people would build the same table, and then stop. A property,
a consequence, a piece of history and a remark about the range are four other
things, and they have their own homes.

**Do the parameters describe the family or the run?** `$s$ a negative odd
integer` is the family; `$s \in \{-1,-3,-5\}$` is what somebody computed on
Tuesday. What was computed belongs in `complete` and `complete-note`.

**Is every claim a fact about the mathematics?** How distinctive a value is,
how good a search hit would be, what a reader should conclude: those are
remarks about this website, and they read as apology.

**Is anything named that should be linked?** The first mention of a family the
corpus holds, once per section. `audit_table` finds the easy cases; you can
see the ones where the phrase differs from the title.

**Is anything pointed at rather than named?** "The first factor", "the
former", "as above" make a reader count backwards and be wrong.

**Would a reader who arrived holding one of these numbers be served?** They
came from a calculation and want to know what they have. Does the page tell
them, in the first screen?

## How to look

    curl -s --socks5-hostname 127.0.0.1:1080 https://numberdb.org/T1xx

The proxy is needed; the key is in the environment for a draft. Read the
rendered HTML, and read the document too -- `numberdb.table('T1xx')` -- but
when they disagree the rendering is what a reader gets.

Run `manage.py audit_table T1xx` and say whether you agree with what it says.
It is a set of rules and you are not: a finding it makes may be right in form
and wrong here, and a thing it misses may matter.

## What to write

A file at `agents/critiques/T1xx.md`. For each finding: what a reader would
see, why it is wrong, and the smallest change that would fix it. Rank them,
and say plainly which are worth doing and which you are noting only because
you noticed.

**Say when there is nothing.** A short report that says the table reads well,
naming the two or three things you checked hardest, is a useful result and the
one you should expect on a good table. Padding it with faults you had to
strain to find wastes the next person's afternoon, and a critique that always
finds five things teaches everybody to skip it.

Do not edit the table. Do not publish anything. Do not commit anything except
your own report.

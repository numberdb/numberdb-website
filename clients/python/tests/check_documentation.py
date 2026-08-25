"""Run every example in the documentation, and say which ones lie.

    python tests/check_documentation.py README.md [more.md ...]
    sage -python tests/check_documentation.py README.md        # sage: blocks too

Nobody had ever run these. A maintainer of another project ran three of them
and found a bug in ours, which is the cheapest possible demonstration that a
documented example is a claim and a claim needs executing.

Two dialects appear in the same files. `>>> ` blocks are plain Python and are
checked with `doctest`, which compares the output as well -- so an example that
still runs but no longer returns what it says is caught too. `sage: ` blocks
are the Sage dialect: they are rewritten to `>>> ` and run the same way, after
Sage's preparser has had them, so `1/3` is a rational and `x^2` is a power.

Examples that reach the live site need the network, so this runs where the
network is. Where a count would change as the database grows, write the example
so it does not depend on one.
"""

import doctest
import os
import re
import sys

#Python puts the *script's* directory on the path, not the working directory,
#so running this as `sage -python tests/check_documentation.py` from the
#package root left `import numberdb` failing in every single example -- 55 of
#55, which is what a broken harness looks like next to broken documentation.
sys.path.insert(0, os.getcwd())


def sage_preparse(source):
    """Sage's preparser, where there is one."""
    try:
        from sage.repl.preparse import preparse
    except ImportError:
        return None
    return preparse(source)


def examples_from(path):
    """`(dialect, doctest text)` for each fenced block that holds examples."""
    with open(path, encoding='utf8') as handle:
        text = handle.read()

    blocks = []
    for block in re.findall(r'```(?:\w+)?\n(.*?)```', text, re.S):
        if re.search(r'^sage: ', block, re.M):
            blocks.append(('sage', block))
        elif re.search(r'^>>> ', block, re.M):
            blocks.append(('python', block))
    return blocks


def as_doctest(dialect, block):
    """One block as something `doctest` will run."""
    if dialect == 'python':
        return block
    #`sage: ` and its continuation `....: ` become the Python prompts, and the
    #body goes through the preparser so the Sage dialect means what it says.
    lines = []
    for line in block.splitlines():
        if line.startswith('sage: '):
            code = line[len('sage: '):]
            prepared = sage_preparse(code)
            if prepared is None:
                return None
            lines.append('>>> ' + prepared.rstrip('\n'))
        elif line.startswith('....: '):
            prepared = sage_preparse(line[len('....: '):])
            lines.append('... ' + (prepared or line[len('....: '):]).rstrip('\n'))
        else:
            lines.append(line)
    return '\n'.join(lines) + '\n'


def run(paths):
    have_sage = sage_preparse('1') is not None
    globals_for_examples = {}
    if have_sage:
        try:
            exec('from sage.all import *', globals_for_examples)
        except ImportError:
            #A modular install without the aggregate module: give the examples
            #the names they actually use, and let the rest skip.
            #Including the names the preparser *generates*, not only the
            #ones the examples are written with: `2` becomes `Integer(2)` and
            #`3.1415` becomes `RealNumber('3.1415')`, so a namespace without
            #those fails on every rewritten line with a NameError that has
            #nothing to do with the example.
            import sage.rings.integer  # noqa: F401  (initialises Sage first)

            for module, names in (
                    ('sage.rings.integer', ('Integer',)),
                    ('sage.rings.real_mpfr', ('RR',)),
                    ('sage.rings.real_mpfi', ('RIF', 'RealIntervalField')),
                    ('sage.rings.cif', ('CIF',)),
                    ('sage.rings.rational_field', ('QQ',)),
                    ('sage.rings.integer_ring', ('ZZ',)),
                    ('sage.rings.padics.factory', ('Qp', 'Zp')),
                    ('sage.rings.polynomial.polynomial_ring_constructor',
                     ('PolynomialRing',))):
                try:
                    imported = __import__(module, fromlist=list(names))
                    for name in names:
                        globals_for_examples[name] = getattr(imported, name)
                except (ImportError, AttributeError):
                    pass

            #Sage binds `RealNumber` to the default real *field*, not to the
            #element class of that name -- the preparser writes
            #`RealNumber('3.1415')` and means `RealField(53)('3.1415')`.
            #Binding the class instead gives "Cannot convert str to
            #RealField_class" on every decimal in the documentation.
            try:
                from sage.rings.real_mpfr import RealField

                globals_for_examples.setdefault('RealNumber', RealField(53))
            except ImportError:
                pass

    total = failed = skipped = 0
    namespaces = {}
    runner = doctest.DocTestRunner(
        optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)
    parser = doctest.DocTestParser()

    for path in paths:
        #A fresh namespace per file as well as per dialect. Two documents are
        #two readings, and carrying state between them let one page's
        #`configure(api_key='...')` reject every request on the next.
        namespaces = {}
        for index, (dialect, block) in enumerate(examples_from(path)):
            if dialect == 'sage' and not have_sage:
                skipped += 1
                continue
            text = as_doctest(dialect, block)
            if text is None:
                skipped += 1
                continue
            name = '%s block %d (%s)' % (path, index + 1, dialect)
            #One namespace per dialect, not per file. The examples build on
            #each other, so a fresh dict per block loses the import at the top
            #of the page -- but the Sage section opens with
            #`import numberdb.sage as numberdb`, and sharing one namespace
            #across both carried that rebinding into the plain-Python blocks
            #below it, which then failed for a reason no reader would ever
            #meet. A reader is in one dialect or the other.
            namespace = namespaces.setdefault(
                dialect, dict(globals_for_examples))
            test = parser.get_doctest(text, namespace, name, path, 0)
            if not test.examples:
                continue
            total += len(test.examples)
            #Collected rather than written straight out: doctest's report goes
            #to whatever `out` is, and a lambda around sys.stdout.write lost it
            #entirely -- the counts were right and the reasons invisible, which
            #is the least useful way for a checker to fail.
            report = []
            outcome = runner.run(test, out=report.append, clear_globs=False)
            #`get_doctest` copies the namespace it is handed, so an import in
            #the first block is invisible to the second unless the names are
            #carried back. Without this every block after the first fails with
            #NameError, which looks exactly like broken documentation.
            namespace.update(test.globs)
            failed += outcome.failed
            if outcome.failed:
                print(''.join(report))

    print('\n%d examples, %d failed, %d blocks skipped (no Sage for them)'
          % (total, failed, skipped))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(run(sys.argv[1:] or ['README.md']))

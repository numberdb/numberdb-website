"""Does the code stored beside a table still produce the numbers in it?

    NUMBERDB_SAMPLE=10 agents/sage.sh agents/verify-generator.py \
        generators/<name>/generate.py [its data modules]

The provenance claim a table makes is that its attached generator computed its
entries. Nothing checked it. `_attach` used to swallow its own failures, so
three tables held numbers produced by code that was not on the site, and the
only way to tell was to run the code and compare.

`verify` does exactly that: it recomputes and compares against what is stored,
and writes nothing. A sample by default, because an exhaustive pass over a
thousand entries at a hundred digits is minutes per table and there are more
than a hundred tables; set NUMBERDB_SAMPLE=0 for all of them.

Prints one line, so a sweep of the corpus is greppable.
"""
import importlib.util
import os
import sys
import time

import numberdb


def beside_me():
    here = os.path.dirname(os.path.abspath(__file__))
    others = [n for n in sorted(os.listdir(here))
              if n.endswith(".py") and n != os.path.basename(__file__)]
    if "generate.py" in others:
        return os.path.join(here, "generate.py")
    if len(others) != 1:
        raise SystemExit("expected a generate.py beside %s; found %s"
                         % (__file__, others))
    return os.path.join(here, others[0])


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else beside_me()
    os.chdir(os.path.dirname(os.path.abspath(path)))

    spec = importlib.util.spec_from_file_location("generator_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    kinds = [v for v in vars(module).values()
             if isinstance(v, type) and issubclass(v, numberdb.Generator)
             and v is not numberdb.Generator]
    if len(kinds) != 1:
        print("RESULT ? %s no single generator class" % path)
        raise SystemExit(2)

    generator = kinds[0]()
    sample = os.environ.get("NUMBERDB_SAMPLE", "10")
    sample = None if sample in ("0", "all", "") else int(sample)

    started = time.time()
    try:
        report = generator.verify(sample=sample)
    except Exception as problem:
        print("RESULT ERROR %s %s: %s"
              % (getattr(generator, "table", "?"),
                 type(problem).__name__, str(problem)[:160]))
        raise SystemExit(1)

    print("RESULT %s %s %s (%.0fs)"
          % ("OK" if report.ok else "MISMATCH",
             getattr(generator, "table", "?"), report, time.time() - started))
    raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    main()

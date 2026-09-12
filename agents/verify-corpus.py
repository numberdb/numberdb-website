"""Run every generator against its own table, in one process.

    NUMBERDB_SAMPLE=10 NUMBERDB_SAGE_MEMORY=700m \
        agents/sage.sh agents/verify-corpus.py

The provenance claim is that the code attached to a table computed the numbers
in it. Nothing checked that until `_attach` was found swallowing its own
failures, and three tables turned out to hold numbers made by code that was
not on the site.

One container for the corpus rather than one per table: a sampled verify takes
about a second and starting Sage takes the best part of a minute, so the
obvious loop spends two hours importing Sage and two minutes checking numbers.

The generators are read from /app/generators in the image, which is the
deployed tree -- the same files the tables carry, now that a deploy prunes
what git removed.

Writes nothing. `verify` recomputes and compares.
"""
import gc
import importlib.util
import os
import sys
import time
import traceback

import numberdb

ROOT = os.environ.get("NUMBERDB_GENERATORS", "/app/generators")
SAMPLE = os.environ.get("NUMBERDB_SAMPLE", "10")
SAMPLE = None if SAMPLE in ("0", "all", "") else int(SAMPLE)
ONLY = [n for n in (os.environ.get("NUMBERDB_ONLY") or "").split(",") if n]


def key_from_stdin():
    """The key, so 128 reads are not 128 anonymous ones.

    The first sweep checked 60 tables and was then rate-limited for the other
    68 -- reading a table is a request like any other, and anonymous requests
    are throttled. Nothing about the numbers was wrong; the reader simply ran
    out of allowance.
    """
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def load(path, name):
    spec = importlib.util.spec_from_file_location("gen_%s" % name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    key_from_stdin()
    dirs = sorted(d for d in os.listdir(ROOT)
                  if os.path.exists(os.path.join(ROOT, d, "generate.py")))
    if ONLY:
        dirs = [d for d in dirs if d in ONLY]
    print("checking %d generators, sample=%s" % (len(dirs), SAMPLE), flush=True)

    ok = mismatch = error = 0
    started = time.time()
    for name in dirs:
        path = os.path.join(ROOT, name, "generate.py")
        here = os.path.dirname(path)
        #A generator reads its data module from beside itself and attaches
        #files by relative path, so it has to run from its own directory.
        os.chdir(here)
        if here not in sys.path:
            sys.path.insert(0, here)
        began = time.time()
        #What was imported before this generator, so its own modules can be
        #taken out afterwards. Two generators keep a data module of the same
        #name -- `genus2-real-periods-q/curve_data.py` and
        #`genus2-special-l-values-q/curve_data.py` -- and once one is in
        #`sys.modules` the other's import silently returns it. That looked
        #exactly like a broken generator: `ImportError: cannot import name
        #'CLASS_DATA' from 'curve_data'`, naming the *other* directory's file,
        #on a generator whose own file defines it.
        before_modules = set(sys.modules)
        try:
            module = load(path, name.replace("-", "_"))
            kinds = [v for v in vars(module).values()
                     if isinstance(v, type) and issubclass(v, numberdb.Generator)
                     and v is not numberdb.Generator]
            if len(kinds) != 1:
                error += 1
                print("ERROR    %-46s no single generator class" % name, flush=True)
                continue
            generator = kinds[0]()
            report = generator.verify(sample=SAMPLE)
        except Exception as problem:
            error += 1
            print("ERROR    %-46s %s: %s" % (name, type(problem).__name__,
                                             str(problem).replace("\n", " ")[:110]),
                  flush=True)
            continue
        finally:
            sys.path[:] = [p for p in sys.path if p != here]
            for name in set(sys.modules) - before_modules:
                #Only what this generator brought in. Sage's own modules are
                #shared and expensive, and they were imported before the loop.
                if getattr(sys.modules[name], '__file__', '') and \
                        str(sys.modules[name].__file__).startswith(here):
                    del sys.modules[name]
            gc.collect()

        tid = getattr(generator, "table", "?")
        if report.ok:
            ok += 1
            print("OK       %-46s %-6s %s (%.0fs)"
                  % (name, tid, report, time.time() - began), flush=True)
        else:
            mismatch += 1
            print("MISMATCH %-46s %-6s %s" % (name, tid, report), flush=True)

    print("\n%d ok, %d mismatched, %d could not run, in %.0f minutes"
          % (ok, mismatch, error, (time.time() - started) / 60), flush=True)
    return 0 if (mismatch == 0 and error == 0) else 1


if __name__ == "__main__":
    sys.exit(main())

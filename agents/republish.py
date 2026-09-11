"""Move a table onto its generator's current grid, old arguments and all.

    cat ~/.config/numberdb/bmatschke-key | NUMBERDB_KEY_FROM_STDIN=1 \
        NUMBERDB_PUBLISH=1 agents/sage.sh agents/republish.py \
        generators/<name>/generate.py

The generator is the file mounted beside this one; `sage.sh` passes no
arguments to the script it runs.

`publish` adds and updates and never deletes, which is why T217 kept 89
entries after the filter that should have taken them out. `removing=True` is
the answer, but a generator must not carry it: a generator runs unattended,
and an `enumerate` that yields nothing would empty a published table. So
removal lives here, apart from them, run by hand at a table that needs it.

Done in two passes, and the order is the point. A single removing publish
sends the new entries first and deletes afterwards, so the table momentarily
holds both grids at once -- 1221 entries for T197, over the soft limit of
1200, and the API refused the whole run. Deleting first means the table only
ever shrinks and then grows back:

  1. Publish the arguments the two grids share, with `removing=True` and
     `overwrite=False`. Nothing is computed, because every one of them is
     already stored; the arguments the new grid drops are deleted.
  2. Publish the generator, which adds what the new grid gained.

Values that survive step 1 are recomputed in step 2 rather than trusted, so a
disagreement between the stored number and this environment still stops the
run the way it would in any other publish.
"""
import importlib.util
import os
import sys

import numberdb


def beside_me():
    """The generator mounted next to this script."""
    here = os.path.dirname(os.path.abspath(__file__))
    others = [name for name in sorted(os.listdir(here))
              if name.endswith(".py") and name != os.path.basename(__file__)]
    if len(others) != 1:
        raise SystemExit("expected one generator beside %s, found %s"
                         % (__file__, others))
    return os.path.join(here, others[0])


def load(path):
    name = os.path.basename(os.path.dirname(os.path.abspath(path))) or "generator"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    #Its `__main__` guard keeps the import from publishing anything itself.
    spec.loader.exec_module(module)
    return module


def generator_in(module):
    found = [value for value in vars(module).values()
             if isinstance(value, type)
             and issubclass(value, numberdb.Generator)
             and value is not numberdb.Generator]
    if len(found) != 1:
        raise SystemExit("expected one Generator in %s, found %s"
                         % (module.__name__, [c.__name__ for c in found]))
    return found[0]


def stored_keys(document):
    """Every stored entry, as a tuple of parameter values in declared order.

    The document nests one level per parameter, in the order `Parameters`
    declares them, so the leaves are reached by walking that deep.
    """
    depth = len(document.get("Parameters") or {})
    if not depth:
        raise SystemExit("this table has no parameters; nothing to regrid")

    found = set()

    def walk(node, path):
        if len(path) == depth:
            found.add(tuple(path))
            return
        if not isinstance(node, dict):
            raise SystemExit("expected %s levels of parameters, found a value "
                             "at %s" % (depth, path))
        for key, value in node.items():
            walk(value, path + [str(key)])

    walk(document.get("Numbers") or {}, [])
    return found


def key_of(params, order):
    return tuple(str(params[name]) for name in order)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else beside_me()
    message = (sys.argv[2] if len(sys.argv) > 2
               else "republished on the grid the generator now describes")

    module = load(path)
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        #Each generator carries this, and the module is imported rather than
        #run, so its `__main__` never reaches it.
        module._key_from_stdin()

    kind = generator_in(module)
    generator = kind()

    document = numberdb.table(generator.table)
    order = list((document.get("Parameters") or {}).keys())
    stored = stored_keys(document)
    wanted = [params for params in generator.enumerate()]
    keys = {key_of(params, order) for params in wanted}

    strays = stored - keys
    print("%s: %s stored, %s wanted, %s to remove, %s to add"
          % (generator.table, len(stored), len(keys), len(strays),
             len(keys - stored)))

    if strays:
        shared = [params for params in wanted if key_of(params, order) in stored]

        class Pruner(kind):
            def enumerate(self, **bounds):
                return iter(shared)

        pruner = Pruner()
        print(pruner.publish(message="removing the arguments the new grid drops",
                             removing=True, overwrite=False))

    print(generator.publish(message=message))


if __name__ == "__main__":
    main()

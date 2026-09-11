"""Republish a generator's table, removing whatever the run did not produce.

    cat ~/.config/numberdb/bmatschke-key | NUMBERDB_KEY_FROM_STDIN=1 \
        NUMBERDB_PUBLISH=1 agents/sage.sh agents/republish.py \
        generators/<name>/generate.py

The generator is the file mounted beside this one; `sage.sh` passes no
arguments to the script it runs.

A generator's own `--publish` adds and updates but never deletes, which is the
right default: a bug in `enumerate` that yields nothing would otherwise empty
a published table, and no amount of care at the call site makes that safe to
have lying around. But a table whose grid has been redrawn keeps its old
arguments for ever without a deletion, and the two grids sit on top of each
other looking like one.

So removal lives here, apart from the generators, spelled out and asked for by
hand. It is the same `publish(removing=True)` the client already offers; this
only makes using it a deliberate act rather than a flag somebody can leave set.
"""
import importlib.util
import os
import sys

import numberdb


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


def beside_me():
    """The generator mounted next to this script.

    `sage.sh` mounts every file it is given into one directory and runs the
    first, passing no arguments, so the path cannot arrive as one. The
    generator is whatever else is there.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    others = [name for name in sorted(os.listdir(here))
              if name.endswith(".py") and name != os.path.basename(__file__)]
    if len(others) != 1:
        raise SystemExit("expected one generator beside %s, found %s"
                         % (__file__, others))
    return os.path.join(here, others[0])


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else beside_me()
    message = (sys.argv[2] if len(sys.argv) > 2
               else "republished on a new grid, removing the old one")

    module = load(path)
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        #Each generator carries this, and the module is imported rather than
        #run, so its `__main__` never reaches it.
        module._key_from_stdin()

    generator = generator_in(module)()
    print(generator.publish(message=message, removing=True))


if __name__ == "__main__":
    main()

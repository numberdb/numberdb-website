# Generators

One directory per table, each holding the program that computes its numbers,
written against the [`numberdb`](https://pypi.org/project/numberdb/) package.

These are working copies. The copy that matters is the one **attached to the
table**, stored in the same revision as the numbers it produced, so that a
reader finds the code that made a value rather than the code that happens to be
here now. Publishing attaches the file automatically; this directory is where
it is edited and kept under version control.

## Running one

They need SageMath, which the web image already has. Against the local site:

```console
$ docker compose up -d web
$ docker compose run --rm \
    -w /generators/T27-unit-ball-volume \
    -e PYTHONPATH=/app/clients/python \
    -e NUMBERDB_URL=http://web:8000 \
    --entrypoint sage web -python generate.py
```

Three details, each of which costs an afternoon to rediscover:

- **`PYTHONPATH=/app/clients/python`** — the repository root holds a package
  called `numberdb` too, the Django project, and it wins otherwise.
- **`NUMBERDB_URL=http://web:8000`** — `web` is the service name on the compose
  network. `localhost` inside a `docker compose run` container is that
  container, not the site.
- **`--entrypoint sage`** — the image's entrypoint runs collectstatic and
  expects to be starting the server.

`docker-compose.override.yml` mounts this directory and adds `web` to
`ALLOWED_HOSTS`. That file is local-only and not in git, so a fresh checkout
needs both added again: without the first the generator is not visible inside
the container, and without the second Django answers a bare `400` that reads
like a broken endpoint rather than a rejected `Host` header.

## Checking before publishing

The interface worth knowing is not the command line. In a Sage session you have
the generator itself, and the two useful questions are one call each:

```python
report = Zeta().verify()          # ten entries, spread through the table
report                            # <VerifyReport T42: 10/10 matched, 0 differing>
report.differing                  # (identity, stored, recomputed) for each one
```

and, when something has drifted, the repair is the report handed straight back:

```python
zeta = Zeta()
report = zeta.verify()
if not report.ok:
    zeta.publish(only=report.to_fix())
```

That is the whole loop: ask what is wrong, fix exactly that. `to_fix()` yields
the parameters of the entries that disagreed, so the run recomputes those and
touches nothing else -- which matters on a table where recomputing everything
takes a day.

`verify()` needs no key and writes nothing: it compares a sample of the stored
table against what the code produces now.

`preview()` computes every entry and sends nothing, applying the same refusals
`publish()` would. It reports what a real run would change, which is the thing
worth reading before rewriting a table somebody is citing.

Only `publish()` writes, and it needs `NUMBERDB_API_KEY`.

## What conversion turns up

The first table converted, T27, is the pattern to expect. Of its 501 entries,
246 came out byte-identical and 255 differed — every one of them in the final
digit, because the original script truncated the last digit where the package
rounds it. Nothing contradicted anything: the comparison classified all 501 as
*same*, *agrees* or *refines*.

So converting a table is not a no-op even when the mathematics is unchanged.
Decide deliberately whether to publish the result, since it rewrites entries
that are already published and cited.

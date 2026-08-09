# Runbook: rebuilding numberdb.org from nothing

For the case where the server is gone: deleted for non-payment, destroyed, or
simply unreachable and not worth recovering.

Read the whole thing before starting. The order matters in one place (DNS
before TLS) and nowhere else.

## What you need, and where it is

| | where |
|---|---|
| The code | `git clone https://github.com/numberdb/numberdb-website` |
| The data | `git clone https://github.com/numberdb/numberdb-data` |
| The secrets | Bitwarden, secure note "numberdb.org production .env" |
| The database | `~/numberdb-backups/numberdb-*.sql.gz` on the laptop |
| The domain | the registrar account, which is its own single point of failure |

Nothing else is needed. TLS certificates reissue in minutes, static files are
regenerated on deploy, and the `numberdb-data` checkout on the server is a
clone that any deploy recreates.

**What is genuinely lost without the database backup:** user accounts, email
addresses, API keys and profiles. Tables and numbers rebuild from
`numberdb-data`, so before user editing ships, the irreplaceable payload is
about 4 KB. Once editing ships, the database *is* the corpus and this backup
becomes the only copy of it.

## 1. A new machine

Any Ubuntu VM with 1 GB of RAM and 25 GB of disk. Note its IP.

    scripts/deploy.sh stage --force-secrets user@NEW_IP /opt/numberdb-website

This installs Docker, copies the repository, generates a fresh `.env`, starts
the stack over HTTP, and seeds the data. It will come up with an **empty**
database and a **generated** `.env`; both are replaced below.

## 2. Restore the secrets

Paste the Bitwarden note over the generated file:

    ssh user@NEW_IP
    cd /opt/numberdb-website
    nano .env          # paste the note's contents, replacing everything
    chmod 600 .env

Check `SERVER_NAME=numberdb.org`, because the nginx entrypoint picks its HTTPS
configuration by looking for `/etc/letsencrypt/live/${SERVER_NAME}`, and a
wrong value here leaves the site on plain HTTP with no obvious symptom.

`POSTGRES_KEY` is a special case. Postgres only reads it when the data
directory is first created, so the restored value must match the password the
new database was initialised with. Either keep the generated one and update the
note afterwards, or set the password explicitly:

    docker compose exec -T db psql -U u_numberdb -d postgres \
        -c "ALTER USER u_numberdb WITH PASSWORD 'the-one-from-the-note';"

## 3. Restore the database

From the laptop, using the newest verified backup:

    f=$(ls -t ~/numberdb-backups/numberdb-*.sql.gz | head -1)
    gzip -dc "$f" | ssh user@NEW_IP \
        "cd /opt/numberdb-website && docker compose exec -T db psql -U u_numberdb -q -d numberdb"

The dump is written with `--clean --if-exists`, so it drops and recreates each
object and can be applied to a database that already has a schema. Expect zero
errors; a handful of `ERROR: ... does not exist` lines on a truly empty
database are harmless, since that is what `--if-exists` guards.

Then confirm it is really there:

    docker compose exec -T db psql -U u_numberdb -d numberdb -t -c \
      "select 'tables ' || count(*) from db_table
       union all select 'numbers ' || count(*) from db_number
       union all select 'users ' || count(*) from auth_user;"

Against the August 2026 backup that reads 107 tables, 45832 numbers, 15 users.

## 4. DNS, then TLS

Point the `A` record for `numberdb.org` at the new IP and wait for it to
propagate. Check from somewhere that is not your own resolver:

    dig +short @1.1.1.1 numberdb.org

**Do not run certbot before this resolves.** Let's Encrypt validates over HTTP
against the address DNS gives it, so issuing early fails and eats one of a
small number of attempts per hour.

    scripts/deploy.sh live user@NEW_IP numberdb.org you@example.org

That sets `SERVER_NAME` and `LETSENCRYPT_EMAIL`, exposes 80 and 443, issues the
certificate and restarts nginx.

## 5. Check it

    curl -s -o /dev/null -w "%{http_code}\n" https://numberdb.org/
    curl -s "https://numberdb.org/api/lookup?text=3.14159" | head -c 200
    ssh user@NEW_IP "cd /opt/numberdb-website && docker compose exec -T web sage -python manage.py check"

`manage.py check` is the quickest way to catch a half-restored `.env`: it
reports missing GitHub credentials as `numberdb.W001` and undeliverable mail as
`numberdb.W002`.

Finally, log in, and confirm search by number returns results, which exercises
the database, the GiST indexes and the evaluator together.

## The two commands

Since this runbook was written, the parts that can be a script are one:

    make backup           # pull a dump, verified: size, gzip, tables present
    make restore_check    # restore the newest one into a scratch database and
                          # count what came back, then drop it

`restore_check` touches nothing in use and is the one to run often. The first
time it ran it caught a real thing: the dump was twenty minutes older than the
migration that added revisions, so the table was missing. That is what a
rehearsal is for.

For the real thing, once this runbook has got you a host with the stack up and
the secrets in place:

    scripts/restore.sh --to root@newhost

It stops the app, replaces the database, starts it again, and prints the counts
so you can see what came back.

## Rehearsing it

An untested restore is a hypothesis. The cheap version, which does not need a
new VM and takes about a minute, is to restore into a scratch database:

    f=$(ls -t ~/numberdb-backups/numberdb-*.sql.gz | head -1)
    docker compose exec -T db psql -U u_numberdb -q -d postgres \
        -c "DROP DATABASE IF EXISTS restore_test;" -c "CREATE DATABASE restore_test;"
    gzip -dc "$f" | docker compose exec -T db psql -U u_numberdb -q -d restore_test
    docker compose exec -T db psql -U u_numberdb -d restore_test -t -c \
        "select count(*) from db_number;"
    docker compose exec -T db psql -U u_numberdb -q -d postgres \
        -c "DROP DATABASE restore_test;"

Done on 2026-08-03: zero errors, 107 tables, 45832 numbers, 15 users, 1038
polynomials, matching production exactly.

Worth repeating whenever the schema changes materially, and certainly before
user editing ships.

## The parts this does not solve

**The domain.** If `numberdb.org` lapses, no server backup helps. Registrar
credentials belong in the same vault as the `.env`, along with the 2FA recovery
codes, since losing access to the registrar during an outage is unrecoverable
by any other means.

**The backup machine.** Backups on one laptop have the same single-copy problem
this runbook exists to solve. A second copy somewhere the server has no
credentials for (external drive, another provider) closes it.

**Staleness of the note.** The Bitwarden note is a snapshot. Every time `.env`
changes on the server, it has to be re-pasted, or this runbook restores a
configuration that no longer works.

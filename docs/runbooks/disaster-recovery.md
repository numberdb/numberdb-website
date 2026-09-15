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
| The database | `~/numberdb-backups/repo`, a restic repository on the laptop, and its copy in S3 |
| The key to it | Bitwarden, secure note "numberdb.org restic repository" &mdash; **lose this and every snapshot is unreadable** |
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

From the laptop:

    scripts/restore.sh --to user@NEW_IP

That reads the newest restic snapshot, or the newest `numberdb-*.sql.gz` if
one is there, and prints the counts of what came back. By hand, if you would
rather see every step:

    export RESTIC_REPOSITORY=$HOME/numberdb-backups/repo
    export RESTIC_PASSWORD_FILE=$HOME/.config/numberdb/restic-password
    restic snapshots                      # which nights are here
    restic dump latest "$(restic snapshots latest --json |
        python3 -c 'import json,sys; print(json.load(sys.stdin)[-1]["paths"][0])')" \
      | ssh user@NEW_IP \
        "cd /opt/numberdb-website && docker compose exec -T db psql -U u_numberdb -q -d numberdb"

If the laptop is what went away, the same repository is in S3 and needs only
the password and a read-only key:

    . ~/.config/numberdb/s3-env        # or make a key; the policy is below
    export RESTIC_REPOSITORY=s3:s3.eu-central-1.amazonaws.com/numberdb-backups

An older `.sql.gz` restores the way it always did:

    gzip -dc ~/numberdb-backups/numberdb-20260915-031218.sql.gz | ssh user@NEW_IP \
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

## Setting up the two copies

Once, on the laptop. Everything below is opt-in: `scripts/backup.sh` works
without any of it and says what is missing.

**1. restic, and a key.** Version matters: compression arrived in 0.14 and
`copy` in 0.10, and Ubuntu 20.04 ships 0.9.6, which would dedup and then store
the chunks raw -- the first snapshot costing three times the `.sql.gz` it
replaces, with no off-site copy possible. `scripts/backup.sh` prefers
`~/.local/bin/restic` and refuses anything older than 0.14, so the
distribution's package can stay where it is:

    v=$(curl -s https://api.github.com/repos/restic/restic/releases/latest |
        grep -oP '"tag_name": "v\K[^"]+')
    curl -sL "https://github.com/restic/restic/releases/download/v$v/restic_${v}_linux_amd64.bz2" \
      | bunzip2 > ~/.local/bin/restic && chmod +x ~/.local/bin/restic

The key encrypts the repository and there is no way back from losing it, so it
goes into Bitwarden before the repository holds anything.
    mkdir -p ~/.config/numberdb
    openssl rand -base64 32 > ~/.config/numberdb/restic-password
    chmod 600 ~/.config/numberdb/restic-password
    # then paste it into Bitwarden as "numberdb.org restic repository"

Old `.sql.gz` dumps go in with `scripts/import-backups.sh`, dated from their
own stamps so the history reads as the nights it was taken. Done here on
2026-09-15: fourteen dumps, 690 MB of files, 231 MB of repository.

**2. A bucket, and a key that can only reach it.** The nightly timer has no
ssh agent and no AWS SSO session, so an expired `aws login` must not be able
to stop a backup: this wants a plain access key for a user that can do nothing
else. About a cent a month at the sizes involved.

    aws s3api create-bucket --bucket numberdb-backups \
        --region eu-central-1 \
        --create-bucket-configuration LocationConstraint=eu-central-1
    aws s3api put-public-access-block --bucket numberdb-backups \
        --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

The policy for the user, which names the bucket and nothing else:

    {"Version": "2012-10-17", "Statement": [
      {"Effect": "Allow", "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
       "Resource": "arn:aws:s3:::numberdb-backups"},
      {"Effect": "Allow",
       "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
       "Resource": "arn:aws:s3:::numberdb-backups/*"}]}

`DeleteObject` is needed: `forget --prune` removes packs nothing references
any more. If that worries you more than it helps, drop it and prune the remote
copy by hand from an account that may.

Then the credentials, in a file rather than the environment:

    umask 077; cat > ~/.config/numberdb/s3-env <<'EOF'
    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...
    EOF

and the repository, in the systemd unit beside `SSH_KEY`:

    Environment=NUMBERDB_S3_REPO=s3:s3.eu-central-1.amazonaws.com/numberdb-backups

**Do not put restic packs in Glacier Deep Archive.** They have to be readable
without thawing, and at a few hundred megabytes the storage class saves
fractions of a cent. Standard or Standard-IA.

## What is not backed up, and could be

Two thirds of the dump is the search index, which the database builds from the
revisions:

    db_number        203 MB   derived
    db_tablerevision  62 MB   the record
    db_tabledata      34 MB   derived
    db_polynomial     11 MB   derived

Dumping with `--exclude-table-data=db_number` and friends would make each dump
about 30 MB instead of 232. It is not the default and should not become one
until the rebuild has been rehearsed end to end: the restore then has to run
the pipeline that repopulates those tables, and *that* is the step which has
never been tested. Worth doing on purpose one afternoon, not by surprise at
three in the morning.

## Rehearsing it

An untested restore is a hypothesis. The cheap version, which does not need a
new VM and takes about a minute, is `scripts/restore.sh --verify` -- it
restores the newest snapshot into a throwaway database beside the real one,
counts what came back and drops it. By hand, from a `.sql.gz`:

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

# Build machines

A table build does not belong on the machine that serves the site. It needs
Sage, sometimes SnapPy, a few hundred megabytes and minutes of CPU; the site
needs to answer pages on 961 MB. Sharing one machine is what made
2026-09-11 and 2026-09-12 outages, and it is why two tables are stubs: T141
stops at ten crossings and T219 holds 2 of the closed census's 11,031
manifolds, both wanting a package nobody wants on a web server.

## What a builder is

Docker, and one image. No checkout, no compose file, no database, no secrets.
`agents/sage.sh` scp's the scripts it runs and mounts them read-only, and a
generator publishes to numberdb.org over the public API with a key that
arrives on stdin — exactly what an outside contributor does.

    scripts/provision-builder.sh user@host

    NUMBERDB_REMOTE=user@host NUMBERDB_SAGE_IMAGE=numberdb/builder:latest \
        agents/sage.sh generators/<name>/generate.py

The lock, the timeout and the 320 MB cap are unchanged; they are per-machine,
so a builder that only builds can be given more:

    NUMBERDB_SAGE_MEMORY=2g

## Credentials

A builder needs four: the Claude and ChatGPT sessions the agents run on, a
GitHub token, and the numberdb API key. Logging in by hand on each machine is
three browser flows and a person, which is a way to have exactly one machine.

So they live once, encrypted, in SSM Parameter Store under `/numberdb`, and a
machine reads its own:

    scripts/builder-secrets.sh

Nothing is baked into an image and nothing is copied between laptops. The
instance carries `numberdb-builder-role`, whose policy allows exactly
`ssm:Get*` on `/numberdb/*` and `kms:Decrypt` through SSM -- so there is no
key on the disk to steal, and rotating a credential in one place updates every
machine that reads it. Re-run the script after rotating.

To seed or rotate one, from a machine with the role:

    aws ssm put-parameter --name /numberdb/gh-token --type SecureString \
        --overwrite --value file://path/to/token

Read from a file rather than typed, so the value does not reach a shell
history or a transcript.

## Creating the VM

Per-cloud, and the only per-cloud part. Sage is **amd64 only** — the
`sagemath/sagemath` images publish no arm64 build — so Graviton, Ampere and
Azure's ARM sizes are out without building Sage yourself.

Sizes below are the smallest that comfortably fit a build: the heaviest
generator measured peaks at 211 MB and the worst ever seen was 386 MB, but
the image alone wants ~8 GB of disk.

### Google Cloud

    gcloud compute instances create numberdb-builder \
        --project=<project> --zone=us-central1-a \
        --machine-type=e2-small \
        --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
        --boot-disk-size=30GB
    gcloud compute ssh numberdb-builder --zone=us-central1-a   # once, for the key

### Azure

    az vm create --resource-group <group> --name numberdb-builder \
        --image Ubuntu2404 --size Standard_B1ms \
        --admin-username azureuser --generate-ssh-keys --os-disk-size-gb 30

### AWS

    aws ec2 run-instances --image-id <ubuntu-24.04-amd64-ami> \
        --instance-type t3.small --key-name <key> \
        --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=30}'

Then add the host to `~/.ssh/config` under a name, and pass that name as
`NUMBERDB_REMOTE`.

## What it costs

A 15-table campaign is about 12 hours of wall clock, of which the builder is
busy for a small part. Measured against the campaign's own ledger, which put
that campaign at **$239.23** of model spend:

| | hourly | 12 hours |
|---|---|---|
| Hetzner CX22 (2 vCPU, 4 GB) | €0.0060 | €0.07 |
| GCP e2-small | ~$0.0168 | $0.20 |
| Azure B1ms | ~$0.0208 | $0.25 |
| AWS t3.small | ~$0.0208 | $0.25 |

The spread across every provider is pennies against $239, so choose on
convenience and quota, not price. Keep the disk between campaigns rather than
destroying the VM: re-pulling 3 GB costs more than the disk does.

## Why not a serverless job

A cold start re-pulls the image. The work a build actually does is often
seconds — all 1001 values of the error-function table compute in under one —
so a minute of image pull per run is the dominant cost. A small VM that stays
warm pulls once, ever.

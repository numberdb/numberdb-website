# Deployment Scripts

- `provision_vm.sh`: Bootstrap a fresh Ubuntu VM, install Docker + Compose, copy the repo, generate `.env` and `.env.prod`, seed data/admin, and start the stack over HTTP.
- `deploy.sh`: Convenience wrapper for common flows:
  - `stage` — provision via SSH, optionally bind Nginx to localhost and open a tunnel
  - `live` — set domain/email, issue TLS cert, expose 80/443
  - `status` — show Compose status and configured domain
  - `quickstage` — one-shot staging + tunnel + synchronous core build
- `deploy_ssh.sh`: Use Docker contexts over SSH to build and bring up services on a remote Docker host; attempts TLS issuance.

See the root README for usage examples. These scripts assume your server `.env` includes `SERVER_NAME` and `LETSENCRYPT_EMAIL` for TLS.


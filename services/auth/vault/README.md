# Vault local infrastructure

This directory contains a small local Vault setup with two layers:

- `vault-unseal` — root-of-trust Vault used only for Transit auto-unseal.
- `vault-leader`, `vault-slave1`, `vault-slave2` — main application Vault Raft cluster.

The scripts are host-side helpers. They execute `vault` inside the Vault Docker
containers through Docker Compose, so the host does not need the Vault CLI.

## Important files

```txt
.env.example                 example local env file
.env                         local secrets; ignored by git
bootstrap-output/            generated keys/tokens; ignored by git
scripts/                     bootstrap/status helper scripts
policies/auth-jwt-signer.hcl policy for auth-service JWT signing
```

Do not commit `.env` or anything from `bootstrap-output/`.

## First-time startup

From this directory:

```bash
cp .env.example .env

# 1. Bootstrap the unseal-storage Vault.
./scripts/bootstrap-unseal-storage.sh --print-sensitive
```

Copy the printed `VAULT_TRANSIT_TOKEN=...` into your local `.env`. Main Vault nodes use this token for Transit auto-unseal, so `bootstrap-main-storage.sh` checks that it is configured before starting them.

Then start and initialize the main application Vault cluster:

```bash
# 2. Bootstrap main Vault and create the initial JWT signing key.
./scripts/bootstrap-main-storage.sh --create-dev-auth-token --print-sensitive
```

This creates:

- main Vault recovery keys and root token;
- `transit/keys/auth-jwt` for JWT signing;
- `auth-jwt-signer` policy;
- optional dev auth-service token when `--create-dev-auth-token` is used.

Sensitive output is saved under `bootstrap-output/` and printed only when
`--print-sensitive` is passed.

## Normal restart

If only main Vault nodes restart, they should auto-unseal using `vault-unseal`.
Usually you only need:

```bash
docker compose up -d
./scripts/status-main-storage.sh
```

If `vault-unseal` itself restarted and is sealed, unseal it first:

```bash
./scripts/unseal-unseal-storage.sh
```

For local dev convenience, you can unseal it from the generated init JSON:

```bash
./scripts/unseal-unseal-storage.sh --from-file bootstrap-output/unseal-storage-init-YYYYMMDD-HHMMSS.json
```

## Main Vault API paths

For containers inside `vault-internal`, the main Vault address is:

```txt
http://vault-leader:8200
```

JWT key metadata/public key:

```txt
GET /v1/transit/keys/auth-jwt
```

JWT signing operation for RS256-compatible signatures:

```txt
POST /v1/transit/sign/auth-jwt/sha2-256
```

Example body:

```json
{
  "input": "<base64(jwt_header.payload)>",
  "signature_algorithm": "pkcs1v15"
}
```

The auth service should use this signing endpoint when issuing tokens. Gateways
and services should verify JWTs locally using cached public keys/JWKS, not by
calling Vault on every request.

## Useful commands

```bash
./scripts/status-unseal-storage.sh
./scripts/status-main-storage.sh

VAULT_TOKEN=<root-or-admin-token> ./scripts/configure-main-storage.sh
VAULT_TOKEN=<root-or-admin-token> ./scripts/configure-main-storage.sh --create-dev-auth-token --print-sensitive
```

## Safety notes

- `vault operator init` is one-time per persistent storage volume.
- Main Vault uses recovery keys because it is auto-unsealed through Transit.
- Root tokens should be used only for bootstrap/admin work.
- The auth-service token should only have the `auth-jwt-signer` policy.
- Do not store application private signing keys in Postgres or KV; use Transit.

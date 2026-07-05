# Vault unseal storage scripts

These scripts are host-side helpers. They call the Vault CLI inside the
`vault-unseal` container through Docker Compose, so you do not need `vault`
installed on the host.

## First bootstrap

```bash
./scripts/bootstrap-unseal-storage.sh
```

This starts `vault-unseal`, initializes it if needed, unseals it after fresh
init, enables Transit, creates `transit/keys/unseal-key`, writes the policy, and
creates a periodic orphan token for the main Vault nodes.

Sensitive output is saved under `bootstrap-output/` and ignored by git.

To print the generated main Vault transit token explicitly:

```bash
./scripts/bootstrap-unseal-storage.sh --print-sensitive
```

Copy the printed token to local `.env` as `VAULT_TRANSIT_TOKEN=...` for dev.

## Unseal after restart

Safer interactive mode:

```bash
./scripts/unseal-unseal-storage.sh
```

Dev convenience mode using the generated init JSON:

```bash
./scripts/unseal-unseal-storage.sh --from-file bootstrap-output/unseal-storage-init-YYYYMMDD-HHMMSS.json
```

## Recreate main Vault transit token

When `vault-unseal` is already initialized and unsealed:

```bash
VAULT_TOKEN=<root-or-admin-token> ./scripts/configure-unseal-storage.sh --print-sensitive
```

## Status

```bash
./scripts/status-unseal-storage.sh
```

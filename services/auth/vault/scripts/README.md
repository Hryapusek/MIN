# Vault scripts

Run scripts from the `vault/` directory.

## Unseal-storage Vault

First-time bootstrap:

```bash
./scripts/bootstrap-unseal-storage.sh --print-sensitive
```

Copy the printed `VAULT_TRANSIT_TOKEN=...` into local `.env`.

Unseal after `vault-unseal` restart:

```bash
./scripts/unseal-unseal-storage.sh
```

Dev convenience mode:

```bash
./scripts/unseal-unseal-storage.sh --from-file bootstrap-output/unseal-storage-init-YYYYMMDD-HHMMSS.json
```

Recreate the main Vault auto-unseal token:

```bash
VAULT_TOKEN=<root-or-admin-token> ./scripts/configure-unseal-storage.sh --print-sensitive
```

Status:

```bash
./scripts/status-unseal-storage.sh
```

## Main application Vault cluster

First-time bootstrap:

```bash
./scripts/bootstrap-main-storage.sh --create-dev-auth-token --print-sensitive
```

Without printing sensitive values:

```bash
./scripts/bootstrap-main-storage.sh --create-dev-auth-token
```

Rerun-safe configuration after init:

```bash
VAULT_TOKEN=<root-or-admin-token> ./scripts/configure-main-storage.sh
```

Create a new dev auth-service token:

```bash
VAULT_TOKEN=<root-or-admin-token> ./scripts/configure-main-storage.sh --create-dev-auth-token --print-sensitive
```

Status:

```bash
./scripts/status-main-storage.sh
```

## Generated sensitive files

The scripts write sensitive JSON bundles to `bootstrap-output/`. The directory is
ignored by git and should not be shared or committed.

# Messenger auth service skeleton

This batch implements the signing-key foundation for the future OAuth/JWT flow. It still does **not** expose registration, login, refresh, logout, JWKS, or token endpoints.

## Implemented now

- SQLAlchemy models for users, device sessions, refresh tokens, and signing-key metadata.
- Provider-neutral `SigningProvider` interface.
- Persistent `LocalFileSigningProvider` with explicit key references and versions.
- Local key-ring bootstrap policies:
  - `generate_if_empty`;
  - `require_existing`;
  - `disabled`.
- RSA/RS256 local signing with JWK-thumbprint `kid` generation.
- Database reconciliation of provider keys.
- Key lifecycle states: `standby`, `active`, `retiring`, and `disabled`.
- One active key per purpose/algorithm, enforced by a PostgreSQL partial unique index.
- First-key activation policy.
- Active-key resolution and provider-routed signing.
- Administrative CLI for bootstrap, synchronization, and registry inspection.
- A Vault provider stub behind the same interface.

The database never stores private-key material. It stores provider routing, lifecycle policy, public PEM, and public JWK metadata.

## Key ownership

```text
Local protected directory / Vault Transit
    owns private keys and performs signing
                |
                v
SigningProvider
    lists public descriptors and signs with an explicit version
                |
                v
SigningKeyRegistry
    reconciles descriptors and controls lifecycle policy
                |
                v
PostgreSQL signing_keys
    stores kid, provider reference, public material, and status
```

Discovering a new key does not automatically activate it. Automatic activation is allowed only when `INITIAL_KEY_ACTIVATION_POLICY=if_registry_empty`, the registry was empty before reconciliation, and exactly one key was discovered.

## Install and run the database

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d pgsql
alembic upgrade head
```

## Local-machine signing

The default configuration is:

```env
TOKEN_SIGNING_BACKEND=local
SIGNING_PROVIDER_NAME=local-primary
LOCAL_SIGNING_KEY_DIRECTORY=.local/signing-keys
LOCAL_KEY_BOOTSTRAP_POLICY=generate_if_empty
INITIAL_KEY_ACTIVATION_POLICY=if_registry_empty
```

Prepare the local key ring:

```bash
python -m app.cli signing-keys bootstrap
```

The first run creates:

```text
.local/signing-keys/
├── keyset.json
└── access-token-001-private.pem
```

Both files are created with mode `0600` on POSIX systems. The directory is excluded by `.gitignore`. A later run validates and reuses the same key instead of generating another one.

After PostgreSQL and migrations are ready, synchronize public metadata:

```bash
python -m app.cli signing-keys sync
python -m app.cli signing-keys list
```

The first synchronization activates the only key when the registry is empty. Later newly discovered keys remain `standby` until explicitly activated by administrative code.

## Docker without Vault

There are two intended variants.

### Development Compose

Mount a persistent named volume at a path such as:

```text
/var/lib/messenger-id/signing-keys
```

Use:

```env
TOKEN_SIGNING_BACKEND=local
LOCAL_SIGNING_KEY_DIRECTORY=/var/lib/messenger-id/signing-keys
LOCAL_KEY_BOOTSTRAP_POLICY=generate_if_empty
```

The key directory must be a persistent volume, never only the container writable layer.

### Stricter Docker deployment

Generate key material in a one-shot initializer, then mount it read-only into the API container:

```bash
LOCAL_KEY_BOOTSTRAP_POLICY=generate_if_empty \
LOCAL_SIGNING_KEY_DIRECTORY=/keys \
python -m app.cli signing-keys bootstrap
```

Run the API container with:

```env
LOCAL_SIGNING_KEY_DIRECTORY=/run/secrets/auth-signing
LOCAL_KEY_BOOTSTRAP_POLICY=require_existing
LOCAL_SIGNING_STRICT_PERMISSIONS=true
```

A typical API entrypoint can later run:

```bash
alembic upgrade head
python -m app.cli signing-keys sync
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Only the one-shot initializer needs write access. The API needs read access because local signing still requires the private key.

## Vault mode later

The configuration boundary already supports:

```env
TOKEN_SIGNING_BACKEND=vault
SIGNING_PROVIDER_NAME=vault-primary
INITIAL_KEY_ACTIVATION_POLICY=manual
VAULT_ADDR=http://vault:8200
VAULT_TRANSIT_MOUNT=transit
VAULT_JWT_KEY_NAME=auth-jwt
VAULT_TOKEN_FILE=/run/secrets/vault-token
```

`VaultTransitSigningProvider` is intentionally still a stub. When implemented, it will return the same `SigningKeyDescriptor` values and accept the same explicit-version signing request as the local provider. OAuth/JWT issuance will not need a second code path.

## Local key manifest

`keyset.json` contains non-secret routing metadata:

```json
{
  "format_version": 1,
  "keys": [
    {
      "reference": "access-token-001",
      "version": 1,
      "purpose": "access_token",
      "algorithm": "RS256",
      "private_key_file": "access-token-001-private.pem",
      "created_at": "..."
    }
  ]
}
```

The provider rejects duplicate identities, unsupported algorithms, missing files, malformed private keys, and paths escaping the configured key directory.

## Tests

```bash
python -m pytest -q
```

Tests cover persistent bootstrap, required-existing behavior, real RSA signature verification, initial registry activation, repeat reconciliation, and unavailable active keys.

## Next batch

The next logical step is the actual local OAuth service layer:

- password hashing;
- user registration/login services;
- device-session creation;
- opaque refresh-token generation and rotation;
- JWT construction using `SigningService`;
- JWKS projection from `SigningKeyRegistry.publishable()`;
- HTTP endpoints after those services are tested.

# Messenger identity skeleton — service layout

The project remains one Python codebase with one dependency set and one test suite, but the runtime components now have separate application folders. No Docker images, Kubernetes manifests, signer networking, or OAuth endpoints are introduced here.

## Structure

```text
module/
├── messenger/
│   ├── services/
│   │   ├── auth/
│   │   │   ├── main.py
│   │   │   └── models/
│   │   ├── key_manager/
│   │   │   ├── main.py
│   │   │   ├── cli.py
│   │   │   ├── models/
│   │   │   ├── providers.py
│   │   │   ├── registry.py
│   │   │   └── service.py
│   │   └── signer/
│   │       ├── factory.py
│   │       ├── providers.py
│   │       └── service.py
│   └── shared/
│       ├── core/
│       ├── db/
│       └── signing/
├── alembic/
├── tests/
└── requirements.txt
```

`services/` contains component-owned code. `shared/` contains only primitives genuinely required by more than one component.

## Ownership

```text
Auth service
    owns users, device sessions, and refresh-token models
    exposes the FastAPI application
    does not bootstrap, discover, reconcile, or sign keys

Key manager
    owns the signing-key registry model and lifecycle logic
    bootstraps local development keys
    discovers public metadata and writes PostgreSQL registry state

Signer
    performs an explicit signing request
    does not import SQLAlchemy, ORM models, or database sessions

Shared signing package
    contracts, request/result types, JWK helpers, local key-ring reader
```

The signer does not yet have a process entry point because its HTTP/gRPC transport is intentionally deferred. Its service package is ready to be wrapped by a transport later.

## Install and migrate

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d pgsql
alembic upgrade head
```

Alembic imports the auth-owned and key-manager-owned model packages into the current shared metadata registry. Phase two will add PostgreSQL schemas and component-specific runtime credentials.

## Run auth

```bash
uvicorn messenger.services.auth.main:app --reload
```

Health endpoint:

```text
GET /health
```

## Run the key manager

One synchronization cycle:

```bash
python -m messenger.services.key_manager.main --once
```

Continuous polling:

```bash
python -m messenger.services.key_manager.main
```

The polling interval is configured with:

```env
KEY_MANAGER_SYNC_INTERVAL_SECONDS=30
```

Administrative commands remain thin delegates to the key-manager code:

```bash
python -m messenger.services.key_manager.cli signing-keys bootstrap
python -m messenger.services.key_manager.cli signing-keys sync
python -m messenger.services.key_manager.cli signing-keys list
```

## Runtime signer contract

The caller supplies:

```text
provider_name
external_reference
provider_version
algorithm
signing_input
```

The signer returns the routing metadata and raw signature bytes. It never queries PostgreSQL, selects the active key, bootstraps material, or changes lifecycle state.

## Local key ring

The existing `keyset.json` format is unchanged. The key manager may use the directory read-write for development bootstrap; the signer only requires read access for explicit-key signing.

Preserved behavior includes:

- `generate_if_empty`, `require_existing`, and `disabled`;
- atomic key and manifest creation;
- path traversal protection;
- optional strict private-key permission checks;
- RS256 signing;
- deterministic JWK-thumbprint `kid` calculation during reconciliation.

## Tests

```bash
python -m pytest -q
```

The tests cover local persistence, discovery, explicit signing, reconciliation, key-manager transactions, physical service boundaries, signer database independence, and auth startup isolation.

## Intentionally deferred

- OAuth and JWT implementation;
- signer HTTP/gRPC API and process entry point;
- Vault Transit calls;
- local key rotation generation;
- leader election;
- separate dependencies or repositories per service;
- Docker images and Kubernetes resources;
- PostgreSQL schemas and application roles.

See `NEXT_PROMPT.md` for the phase-two database-boundary task.

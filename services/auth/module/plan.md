# Project plan

## Completed — component and folder boundaries

```text
[x] One Python project and dependency set
[x] Separate messenger/services/auth folder
[x] Separate messenger/services/key_manager folder
[x] Separate messenger/services/signer folder
[x] Auth-owned ORM models live with auth
[x] SigningKey ORM model lives with key manager
[x] Shared code limited to configuration, current DB foundation, and signing primitives
[x] Key discovery separated from runtime signing
[x] Local bootstrap and reconciliation owned by key manager
[x] Explicit-key, database-independent signer
[x] FastAPI auth composition root
[x] Single-instance polling key-manager entry point
[x] Existing Alembic history preserved
[x] Focused boundary and lifecycle tests
```

## Current responsibility split

```text
Auth
    users, device sessions, refresh tokens, future OAuth/JWT workflows

Key manager
    bootstrap, discovery, reconciliation, activation, retirement, disable

Signer
    execute an explicit signing request only

Shared
    small cross-service contracts and infrastructure required in this phase
```

## Intentionally not implemented yet

```text
[ ] OAuth endpoints
[ ] JWT construction
[ ] Signer HTTP/gRPC API and executable transport
[ ] Vault Transit integration
[ ] Local key rotation generation
[ ] Leader election
[ ] Separate Python projects or repositories
[ ] Docker images
[ ] Kubernetes manifests
[ ] Separate physical databases
```

## Phase two

See `NEXT_PROMPT.md`:

```text
[ ] PostgreSQL auth and key_management schemas
[ ] Separate runtime database credentials and grants
[ ] Safe Alembic table moves
[ ] Development database initialization
[ ] Signer remains database-independent
```

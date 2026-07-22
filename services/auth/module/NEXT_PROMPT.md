
# Current source layout

The baseline now uses one Python package with separate service folders:

```text
messenger/services/auth
messenger/services/key_manager
messenger/services/signer
messenger/shared
```

Auth-owned ORM models are under `messenger/services/auth/models`. The `SigningKey` ORM model is under `messenger/services/key_manager/models`. Shared SQLAlchemy foundations currently remain under `messenger/shared/db` and should be split into explicit auth/key-manager runtime session factories as part of this phase. Preserve this service-folder layout.

Use the attached phase-one project as the baseline.

Implement **phase two only**: introduce clear PostgreSQL schema ownership and database permissions while keeping one PostgreSQL instance and one logical database.

The project currently has three component boundaries:

1. **Auth service**
   - Owns users, device sessions, and refresh tokens.
   - Must have read/write access to its own tables.
   - Needs read-only access to signing-key public metadata later.
   - Must not modify signing-key lifecycle.

2. **Key manager**
   - Runs as a single instance for now.
   - Is the only writer of signing-key registry data.
   - Must not access auth user/session/token data.

3. **Signer service**
   - Is horizontally scalable and database-independent.
   - Must not receive PostgreSQL credentials or import database/ORM code.

Do not implement OAuth endpoints, JWT construction, a signer network API, Vault HTTP communication, leader election, message brokers, Kubernetes resources, or separate physical databases in this phase.

# Main goal

Keep one PostgreSQL database, but introduce two schemas:

```text
auth
key_management
```

Move tables as follows:

```text
auth.users
auth.device_sessions
auth.refresh_tokens

key_management.signing_keys
```

Enforce the boundary using separate PostgreSQL roles and grants:

```text
auth application role:
    read/write auth.*
    read-only key_management.signing_keys

key-manager application role:
    read/write key_management.*
    no access to auth.*

signer:
    no database role or credentials
```

Keep the implementation practical for one developer. Do not add a generic permission framework or unnecessary infrastructure.

# ORM changes

Update SQLAlchemy models so their table schemas are explicit.

Expected direction:

```python
class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}
```

For models that already have indexes or constraints in `__table_args__`, preserve them and add the schema option correctly.

Update foreign keys to use schema-qualified targets:

```text
auth.device_sessions.user_id -> auth.users.id
auth.refresh_tokens.device_session_id -> auth.device_sessions.id
auth.refresh_tokens.replaced_by_id -> auth.refresh_tokens.id
```

`SigningKey` must use the `key_management` schema.

Do not change the user, device-session, refresh-token, or signing-key domain fields unless schema qualification requires it.

# Alembic migration

Create a new migration after the current head. Do not rewrite or squash existing migrations.

The migration must safely handle an existing database created by phase one, where all tables currently live in the default `public` schema.

The upgrade should:

1. Create schemas `auth` and `key_management` if they do not exist.
2. Move the existing tables from `public` into their target schemas without dropping their data.
3. Preserve primary keys, foreign keys, indexes, check constraints, and unique constraints.
4. Ensure foreign-key references remain valid and schema-qualified after the move.
5. Keep PostgreSQL sequence/default behavior correct if any sequences exist.

Prefer PostgreSQL table schema transfer operations such as `ALTER TABLE ... SET SCHEMA` rather than recreating tables and copying data.

The downgrade should move the tables safely back to `public`, in an order that respects foreign-key dependencies, and drop the two schemas only when they are empty.

Validate both upgrade and downgrade SQL generation.

# Alembic metadata and version table

Update Alembic configuration so autogeneration sees schema-qualified tables correctly.

Use `include_schemas=True` where needed.

Keep Alembic's own version table simple. It may remain in `public`; do not introduce another migration system or separate Alembic histories in this phase.

# Database roles and grants

Add a small PostgreSQL initialization script for development Docker Compose. It should create two non-superuser login roles, with names configurable through environment variables where practical:

```text
auth_app
key_manager_app
```

The existing PostgreSQL owner/admin account remains responsible for migrations.

Grant the following after schemas/tables exist:

## Auth role

```text
USAGE on schema auth
SELECT, INSERT, UPDATE, DELETE on all current tables in auth
appropriate sequence privileges in auth
USAGE on schema key_management
SELECT on key_management.signing_keys
no INSERT, UPDATE, DELETE on key_management.signing_keys
```

## Key-manager role

```text
USAGE on schema key_management
SELECT, INSERT, UPDATE, DELETE on all current tables in key_management
appropriate sequence privileges in key_management
no privileges on auth schema or auth tables
```

Configure default privileges so future tables created by the migration owner inside each schema receive the intended grants.

Do not grant schema ownership, superuser, database creation, role creation, or broad privileges on `public` to either application role.

Because PostgreSQL Docker initialization scripts run only on first database creation, document this limitation clearly. Provide an explicit command or SQL script that can be rerun against an existing development database after migrations.

# Configuration

Keep the existing migration/admin database configuration.

Add separate runtime database configuration for:

```text
auth service database user/password
key manager database user/password
```

Avoid duplicating the whole settings model unnecessarily. A small shared database settings type or clear prefixed settings is sufficient.

The key-manager entry point must build its SQLAlchemy engine/session using the key-manager credentials.

The future auth runtime should have a factory/settings path for auth credentials, even though OAuth endpoints are still not implemented.

The signer package must remain completely independent of all database settings.

Update `.env.example` with clear development-only defaults/placeholders. Do not commit real credentials.

# Docker Compose

Update the module's Docker Compose setup with the smallest practical solution:

- one PostgreSQL container;
- one logical database;
- initialization scripts mounted into `/docker-entrypoint-initdb.d` when useful;
- environment variables for the admin/migration account, auth role, and key-manager role;
- no additional database containers.

Do not add application containers unless genuinely required to validate the database setup.

Provide commands for:

1. Starting a fresh database.
2. Running Alembic migrations with the owner/admin credentials.
3. Applying or reapplying grants after migrations.
4. Verifying auth-role permissions.
5. Verifying key-manager-role permissions.

# Repository/query boundary

Move or add database-session factories so component ownership is explicit:

```text
Auth session factory
    uses auth credentials

Key-manager session factory
    uses key-manager credentials

Migration/Alembic engine
    uses owner/admin credentials
```

Do not create a signer session factory.

The key manager must continue to perform all writes to `key_management.signing_keys`.

It is acceptable for the auth component to have a small read-only repository for signing-key metadata in this phase only if it helps verify permissions. Do not implement caching, JWT issuance, or JWKS endpoints yet.

# Tests

Keep all phase-one tests passing and add focused tests for:

1. ORM tables have the expected schemas.
2. Foreign keys target schema-qualified auth tables.
3. The signer package still has no SQLAlchemy, ORM, or database-settings dependency.
4. Key-manager session construction uses key-manager credentials.
5. Auth session construction uses auth credentials.
6. The new Alembic migration has a valid upgrade and downgrade path.
7. When PostgreSQL is available, integration checks demonstrate:
   - auth role can read/write `auth.*`;
   - auth role can select but cannot modify `key_management.signing_keys`;
   - key-manager role can read/write `key_management.signing_keys`;
   - key-manager role cannot select from `auth.users`;
   - signer receives no database configuration.

If Docker/PostgreSQL is unavailable in the execution environment, keep integration tests optional/skippable and still validate generated SQL and static configuration. Report the limitation honestly.

# Documentation

Update `README.md` and `plan.md` with the practical ownership model:

```text
One PostgreSQL instance
One logical database
Two schemas
Two application roles
One migration owner
No signer database access
```

Explain that separate physical databases can be considered later, but are intentionally avoided now because they would require an API/event replication path for active signing-key metadata.

Document fresh-development setup and existing-database migration separately.

# Cleanup and constraints

- Do not modify the top-level Vault setup.
- Do not move private keys into PostgreSQL.
- Do not let auth write signing-key lifecycle fields.
- Do not let key manager access auth tables.
- Do not give signer database credentials.
- Do not create separate physical databases.
- Do not add OAuth endpoints or signer networking.
- Avoid duplicate engines, settings, or grant scripts when one small reusable implementation is enough.
- Do not commit generated keys, `.env`, caches, virtual environments, database volumes, or runtime files.

# Required final response

After implementation, report:

1. The resulting schema/table layout.
2. The PostgreSQL roles and exact intended permissions.
3. The new migration behavior for upgrade and downgrade.
4. How auth, key manager, and Alembic obtain their respective credentials.
5. Docker Compose initialization and rerunnable grant commands.
6. Tests and validation performed.
7. Any limitations intentionally left for later.

Do not begin OAuth or signer networking work in this phase.

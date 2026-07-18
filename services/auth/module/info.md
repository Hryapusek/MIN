# Auth schema notes

The ORM models in `app/models` are the source of truth. This document only explains the current small design.

## User

`users` stores the local account:

- UUID primary key;
- normalized email (normalization will be implemented in the service layer);
- password hash, never a plaintext password;
- one global role: `user`, `moderator`, or `admin`;
- `is_active` for account disabling;
- `token_version` for coarse account-wide access-token invalidation later;
- creation/update timestamps.

A single role is intentional for the first version. Fine-grained permissions and conversation-local membership do not belong in this first auth migration.

## Device session

`device_sessions` represents one authenticated application installation or browser session. Its UUID can be copied into the access-token `sid` claim.

It stores:

- owning user;
- client-generated random `device_id`;
- optional display name, User-Agent, IP, and app version;
- creation and last-seen timestamps;
- session expiry;
- nullable `revoked_at`.

A session is active when `revoked_at IS NULL` and it has not expired. Logging out one device revokes one row. Logging out everywhere revokes all sessions belonging to the user.

## Refresh token

`refresh_tokens` stores one hash per issued opaque refresh token. Raw refresh tokens are returned to clients and must never be persisted in this database.

Rotation fields:

- `family_id` groups the complete login/rotation chain;
- `consumed_at` marks a token already exchanged;
- `replaced_by_id` points to the newly issued token;
- reusing a consumed token can later revoke the whole family/session;
- `revoked_at` supports explicit invalidation.

Refresh tokens work identically regardless of whether access tokens are signed locally or through Vault.

## Signing key metadata

`signing_keys` stores only public and routing metadata:

- `kid` placed in the JWT header;
- `backend`: `local` or `vault`;
- JWT algorithm;
- `key_reference` identifying an external key source;
- public key PEM for verification/JWKS conversion later;
- active/retired lifecycle timestamps.

There is deliberately no private-key column.

For a local development key, `key_reference` can point to an environment variable or mounted file. For Vault, it can identify a Transit key. In both cases the access token remains the same JWT format; only the signing backend changes.

# Auth schema and signing-key notes

The ORM models are the schema source of truth.

## User

`users` stores a local account with a UUID, email, password hash, one small global role, activity status, token version, and timestamps. The initial global roles remain `user`, `moderator`, and `admin`.

## Device session

`device_sessions` represents one authenticated browser or application installation. Its UUID is suitable for the JWT `sid` claim. Revoking one row logs out one device after current short-lived access tokens expire, unless an online revocation check is added later.

## Refresh token

`refresh_tokens` stores hashes of opaque refresh tokens. `family_id`, `consumed_at`, `replaced_by_id`, and `revoked_at` support rotation and later reuse detection. Refresh tokens are independent of the access-token signing provider.

## Signing key registry

`signing_keys` is a catalog and policy table, not a secret store.

It contains:

- deterministic public-key `kid`;
- configured `provider_name`;
- backend type (`local` or `vault`);
- provider-owned external reference and version;
- purpose and algorithm;
- public PEM and public JWK;
- lifecycle status;
- discovery, availability, activation, retirement, and disabling timestamps.

Lifecycle states:

```text
standby  -> discovered but not used for new tokens
active   -> signs newly issued access tokens
retiring -> no new signing; remains publishable through JWKS
disabled -> neither signs nor normally appears in JWKS
```

A partial unique index permits only one `active` row for a purpose/algorithm pair.

Provider reconciliation is conservative:

- a new provider version becomes `standby`;
- an existing version must retain the same public key and immutable metadata;
- a missing provider key is marked unavailable rather than deleted;
- an active unavailable key causes signing to fail closed;
- the first and only key may auto-activate only when the registry was empty.

Private RSA PEM files remain in the configured protected local directory. Vault private keys will remain inside Transit when that provider is implemented.

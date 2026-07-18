# Current batch status

## Auth data model

```text
[x] User with a small global role
[x] DeviceSession
[x] Hashed opaque RefreshToken rotation model
[x] SigningKey registry without private material
```

## Signing provider architecture

```text
[x] Provider-neutral SigningProvider interface
[x] Explicit provider name, key reference, and provider version
[x] Local persistent key ring
[x] generate_if_empty bootstrap policy
[x] require_existing bootstrap policy
[x] disabled bootstrap policy
[x] Atomic local key-file creation
[x] Path traversal and manifest validation
[x] RS256 signing
[x] Public JWK derivation
[x] Deterministic JWK-thumbprint kid
[x] Vault Transit provider boundary
[ ] Vault Transit discovery/signing implementation
```

## Registry policy

```text
[x] Provider-to-database reconciliation
[x] standby / active / retiring / disabled lifecycle
[x] First-key activation policy
[x] One active key per purpose/algorithm
[x] Missing-provider-key detection
[x] Active-key resolution
[x] Explicit-provider-version signing
[x] Manual activation/retirement service method
[x] Disable service method
[x] Publishable-key query for future JWKS
[ ] Administrative HTTP/CLI rotation command
[ ] Automatic retirement cleanup policy
```

## Operational profiles

```text
[x] Local machine with persistent Git-ignored keys
[x] Docker development volume design
[x] Docker one-shot initializer / read-only runtime design
[x] Vault configuration boundary
[x] Bootstrap/sync/list CLI commands
```

## OAuth work not implemented yet

```text
[ ] Password hashing
[ ] User registration service
[ ] Login service
[ ] Device-session service
[ ] Refresh-token generation
[ ] Refresh-token rotation and reuse detection
[ ] JWT encoding and claims
[ ] JWKS endpoint
[ ] Register/login/refresh/logout HTTP endpoints
[ ] Vault Transit implementation
```

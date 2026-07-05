# Auth service policy for signing JWT access tokens through Vault Transit.
# It intentionally does not allow exporting, deleting, rotating, or changing the key.

path "transit/sign/auth-jwt" {
  capabilities = ["update"]
}

path "transit/sign/auth-jwt/sha2-256" {
  capabilities = ["update"]
}

path "transit/keys/auth-jwt" {
  capabilities = ["read"]
}

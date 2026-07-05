#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/vault-common.sh"

PRINT_SENSITIVE=false
CREATE_DEV_AUTH_TOKEN=false

usage() {
  cat <<USAGE
Usage: VAULT_TOKEN=<root-or-admin-token> $0 [--create-dev-auth-token] [--print-sensitive]

Rerun-safe configuration for an already initialized and unsealed main Vault:
  - enables Transit if missing
  - creates transit/keys/auth-jwt if missing
  - writes the auth-jwt-signer policy
  - optionally creates a dev auth-service token
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --create-dev-auth-token)
      CREATE_DEV_AUTH_TOKEN=true
      ;;
    --print-sensitive)
      PRINT_SENSITIVE=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
  shift
done

[ -n "${VAULT_TOKEN:-}" ] || die "VAULT_TOKEN is required"
require_main_transit_token_configured

ensure_main_leader_container
wait_for_main_leader_api

main_initialized=$(main_status_field Initialized || true)
main_sealed=$(main_status_field Sealed || true)

[ "$main_initialized" = "true" ] || die "Main Vault is not initialized. Run scripts/bootstrap-main-storage.sh first."
[ "$main_sealed" = "false" ] || die "Main Vault leader is sealed. Check vault-unseal and VAULT_TRANSIT_TOKEN."

configure_main_transit "$CREATE_DEV_AUTH_TOKEN" "$PRINT_SENSITIVE"

printf '\n%s\n' "Main storage configuration complete."
print_main_storage_api_examples

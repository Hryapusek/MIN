#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/vault-common.sh"

PRINT_SENSITIVE=false

usage() {
  cat <<USAGE
Usage: VAULT_TOKEN=<root-or-admin-token> $0 [--print-sensitive]

Configures an already initialized and unsealed vault-unseal storage Vault:
  - enables Transit if missing
  - creates transit/keys/unseal-key if missing
  - writes the unseal policy
  - creates a fresh orphan periodic token for main Vault auto-unseal
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
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

ensure_unseal_storage_container
wait_for_unseal_storage_api

initialized=$(vault_status_field Initialized || true)
sealed=$(vault_status_field Sealed || true)

[ "$initialized" = "true" ] || die "$UNSEAL_SERVICE is not initialized. Run bootstrap-unseal-storage.sh first."
[ "$sealed" = "false" ] || die "$UNSEAL_SERVICE is sealed. Run unseal-unseal-storage.sh first."

token_file=$(configure_unseal_transit)

printf '\n%s\n' "Configuration complete."
print_transit_token_hint "$token_file" "$PRINT_SENSITIVE"

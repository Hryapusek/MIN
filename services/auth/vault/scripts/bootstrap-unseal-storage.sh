#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/vault-common.sh"

AUTO_UNSEAL=true
PRINT_SENSITIVE=false

usage() {
  cat <<USAGE
Usage: $0 [--no-auto-unseal] [--print-sensitive]

Bootstraps the vault-unseal storage Vault:
  1. Starts vault-unseal container
  2. Initializes it if needed
  3. Unseals it after fresh init unless --no-auto-unseal is used
  4. Enables Transit
  5. Creates transit/keys/unseal-key
  6. Writes the unseal policy
  7. Creates an orphan periodic token for the main Vault nodes

Default behavior saves sensitive bootstrap data to bootstrap-output/ and does not
print tokens to console.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-auto-unseal)
      AUTO_UNSEAL=false
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


ensure_output_dir

ensure_unseal_storage_container

wait_for_unseal_storage_api

initialized=$(vault_status_field Initialized || true)
sealed=$(vault_status_field Sealed || true)

if [ "$initialized" = "false" ]; then
  timestamp=$(date +%Y%m%d-%H%M%S)
  init_file="$BOOTSTRAP_OUTPUT_DIR/unseal-storage-init-$timestamp.json"

  log "Initializing $UNSEAL_SERVICE..."
  vault_unseal_exec operator init \
    -key-shares=5 \
    -key-threshold=3 \
    -format=json > "$init_file"

  chmod 600 "$init_file" 2>/dev/null || true
  log "Init bundle saved: $init_file"

  if [ "$AUTO_UNSEAL" = "true" ]; then
    unseal_from_init_file "$init_file"
  else
    warn "Vault was initialized but not unsealed. Run scripts/unseal-unseal-storage.sh --from-file '$init_file'"
    exit 0
  fi

  VAULT_TOKEN=$(json_read "$init_file" root_token)
  export VAULT_TOKEN
else
  log "$UNSEAL_SERVICE is already initialized"

  if [ "$sealed" = "true" ]; then
    die "$UNSEAL_SERVICE is sealed. Run scripts/unseal-unseal-storage.sh first."
  fi

  [ -n "${VAULT_TOKEN:-}" ] || die "Already initialized. Export a root/admin VAULT_TOKEN before configuring Transit."
fi

token_file=$(configure_unseal_transit)

printf '\n%s\n' "Bootstrap complete."
printf '%s\n' "Important local files are under: $BOOTSTRAP_OUTPUT_DIR"
print_transit_token_hint "$token_file" "$PRINT_SENSITIVE"

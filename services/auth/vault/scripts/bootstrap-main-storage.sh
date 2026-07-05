#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/vault-common.sh"

PRINT_SENSITIVE=false
CREATE_DEV_AUTH_TOKEN=false
START_FOLLOWERS=true

usage() {
  cat <<USAGE
Usage: $0 [--create-dev-auth-token] [--print-sensitive] [--no-followers]

Bootstraps the main application Vault storage cluster:
  1. Checks that vault-unseal is initialized and unsealed
  2. Starts vault-leader
  3. Initializes vault-leader if needed and saves recovery keys/root token
  4. Enables Transit on the main Vault
  5. Creates transit/keys/auth-jwt for JWT signing
  6. Writes the auth-jwt-signer policy
  7. Optionally creates a dev auth-service token
  8. Starts follower nodes and prints status/API examples

If main Vault is already initialized, export VAULT_TOKEN=<root-or-admin-token>
so the script can rerun the configuration step safely.
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
    --no-followers)
      START_FOLLOWERS=false
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
unseal_initialized=$(vault_status_field Initialized || true)
unseal_sealed=$(vault_status_field Sealed || true)

[ "$unseal_initialized" = "true" ] || die "$UNSEAL_SERVICE is not initialized. Run scripts/bootstrap-unseal-storage.sh first."
[ "$unseal_sealed" = "false" ] || die "$UNSEAL_SERVICE is sealed. Run scripts/unseal-unseal-storage.sh first."

require_main_transit_token_configured
ensure_main_leader_container
wait_for_main_leader_api

main_initialized=$(main_status_field Initialized || true)
main_sealed=$(main_status_field Sealed || true)

if [ "$main_initialized" = "false" ]; then
  timestamp=$(date +%Y%m%d-%H%M%S)
  init_file="$BOOTSTRAP_OUTPUT_DIR/main-storage-init-$timestamp.json"

  log "Initializing main Vault leader with recovery keys..."
  main_vault_exec operator init \
    -recovery-shares=5 \
    -recovery-threshold=3 \
    -format=json > "$init_file"

  chmod 600 "$init_file" 2>/dev/null || true
  log "Main Vault init bundle saved: $init_file"

  wait_for_vault_unsealed "$MAIN_LEADER_SERVICE" "$MAIN_VAULT_ADDR" 60

  VAULT_TOKEN=$(json_read "$init_file" root_token)
  export VAULT_TOKEN

  if [ "$PRINT_SENSITIVE" = "true" ]; then
    printf '\n%s\n' "Main Vault init bundle contains recovery keys and root token:"
    cat "$init_file"
  else
    printf '\n%s\n' "Main Vault recovery keys/root token were NOT printed."
    printf '%s\n' "Saved sensitive init bundle: $init_file"
  fi
else
  log "Main Vault is already initialized"
  [ "$main_sealed" = "false" ] || die "Main Vault leader is sealed. Check VAULT_TRANSIT_TOKEN and vault-unseal status."
  [ -n "${VAULT_TOKEN:-}" ] || die "Main Vault already initialized. Export VAULT_TOKEN=<root-or-admin-token> to configure it."
fi

configure_main_transit "$CREATE_DEV_AUTH_TOKEN" "$PRINT_SENSITIVE"

if [ "$START_FOLLOWERS" = "true" ]; then
  ensure_service "$MAIN_SLAVE1_SERVICE"
  ensure_service "$MAIN_SLAVE2_SERVICE"
  wait_for_vault_api "$MAIN_SLAVE1_SERVICE" "$MAIN_VAULT_ADDR" 60
  wait_for_vault_api "$MAIN_SLAVE2_SERVICE" "$MAIN_VAULT_ADDR" 60
  wait_for_vault_unsealed "$MAIN_SLAVE1_SERVICE" "$MAIN_VAULT_ADDR" 90
  wait_for_vault_unsealed "$MAIN_SLAVE2_SERVICE" "$MAIN_VAULT_ADDR" 90
fi

printf '\n%s\n' "Main storage bootstrap/configuration complete."
print_main_storage_api_examples
print_raft_peers_if_authorized

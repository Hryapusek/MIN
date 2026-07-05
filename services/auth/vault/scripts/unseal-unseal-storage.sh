#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/vault-common.sh"

INIT_FILE=""
KEY_COUNT=${UNSEAL_THRESHOLD:-3}

usage() {
  cat <<USAGE
Usage: $0 [--from-file path/to/unseal-storage-init.json]

Unseals the vault-unseal storage Vault after restart.

Modes:
  --from-file FILE   Dev convenience mode. Reads threshold keys from init JSON.
  no arguments       Safer interactive mode. Prompts for key shares.

Do not commit init JSON files. They contain unseal keys and root token.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --from-file)
      shift
      [ "$#" -gt 0 ] || die "--from-file requires a path"
      INIT_FILE=$1
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

ensure_unseal_storage_container
wait_for_unseal_storage_api

initialized=$(vault_status_field Initialized || true)
sealed=$(vault_status_field Sealed || true)

[ "$initialized" = "true" ] || die "$UNSEAL_SERVICE is not initialized. Run bootstrap-unseal-storage.sh first."

if [ "$sealed" = "false" ]; then
  log "$UNSEAL_SERVICE is already unsealed"
  vault_status_output || true
  exit 0
fi

if [ -n "$INIT_FILE" ]; then
  unseal_from_init_file "$INIT_FILE"
  vault_status_output || true
  exit 0
fi

log "Interactive unseal mode. Enter $KEY_COUNT key shares."

i=1
while [ "$i" -le "$KEY_COUNT" ]; do
  printf 'Unseal key %s: ' "$i" >&2

  # Hide input when running in a terminal. Fallback to normal read otherwise.
  if [ -t 0 ]; then
    stty -echo
    IFS= read -r key
    stty echo
    printf '\n' >&2
  else
    IFS= read -r key
  fi

  [ -n "$key" ] || die "Empty unseal key"
  vault_unseal_exec operator unseal "$key" >/dev/null

  sealed=$(vault_status_field Sealed || true)
  if [ "$sealed" = "false" ]; then
    log "$UNSEAL_SERVICE is unsealed"
    vault_status_output || true
    exit 0
  fi

  i=$((i + 1))
done

sealed=$(vault_status_field Sealed || true)
[ "$sealed" = "false" ] || die "$UNSEAL_SERVICE is still sealed"

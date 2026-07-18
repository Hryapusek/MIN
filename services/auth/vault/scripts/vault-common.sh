#!/bin/sh

# Common helpers for host-side Vault devops scripts.
# These scripts intentionally execute the Vault CLI inside the vault-unseal
# container, so the host machine does not need the vault binary installed.
echo "Entered vault-common.sh"

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VAULT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

COMPOSE_FILE=${COMPOSE_FILE:-"$VAULT_DIR/docker-compose.yml"}
UNSEAL_SERVICE=${UNSEAL_SERVICE:-vault-unseal}
UNSEAL_VAULT_ADDR=${UNSEAL_VAULT_ADDR:-http://127.0.0.1:8200}
BOOTSTRAP_OUTPUT_DIR=${BOOTSTRAP_OUTPUT_DIR:-"$VAULT_DIR/bootstrap-output"}

echo "[vault-common.sh] vars created successfully"

log() {
  printf '%s\n' "[vault] $*" >&2
}

warn() {
  printf '%s\n' "[vault][warn] $*" >&2
}

die() {
  printf '%s\n' "[vault][error] $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

python_bin() {
  if command -v python3 >/dev/null 2>&1; then
    printf '%s\n' python3
  elif command -v python >/dev/null 2>&1; then
    printf '%s\n' python
  else
    die "python3 or python is required for reading Vault JSON output"
  fi
}

compose() {
  require_command docker
  (cd "$VAULT_DIR" && docker compose -f "$COMPOSE_FILE" "$@")
}

ensure_output_dir() {
  mkdir -p "$BOOTSTRAP_OUTPUT_DIR"
  chmod 700 "$BOOTSTRAP_OUTPUT_DIR" 2>/dev/null || true
}

ensure_unseal_storage_container() {
  log "Starting $UNSEAL_SERVICE if needed..."
  compose up -d "$UNSEAL_SERVICE"
}

vault_unseal_exec() {
  compose exec -T "$UNSEAL_SERVICE" env VAULT_ADDR="$UNSEAL_VAULT_ADDR" vault "$@"
}

vault_unseal_exec_auth() {
  [ -n "${VAULT_TOKEN:-}" ] || die "VAULT_TOKEN is required for this operation"
  compose exec -T -e VAULT_TOKEN="$VAULT_TOKEN" "$UNSEAL_SERVICE" \
    env VAULT_ADDR="$UNSEAL_VAULT_ADDR" vault "$@"
}

vault_status_output() {
  set +e
  output=$(vault_unseal_exec status 2>&1)
  code=$?
  printf '%s\n' "$output"
  return "$code"
}

vault_status_field() {
  field_name=$1
  # Example status lines: "Initialized     true", "Sealed          false"
  vault_status_output 2>/dev/null | awk -v key="$field_name" '$1 == key { print $2; exit }'
  set -e
}

wait_for_unseal_storage_api() {
  echo "[vault-common.sh] wait_for_unseal_storage_api entry"
  attempts=${1:-60}
  i=1

  echo "[vault-common.sh] before while loop"
  while [ "$i" -le "$attempts" ]; do
    set +e
    echo "[vault-common.sh] obtaining status"
    vault_status_output >/dev/null 2>&1
    code=$?
    echo "[vault-common.sh] code is $code"
    set -e

    # vault status returns 0 when unsealed and 2 when sealed.
    # Both mean the API is reachable.
    if [ "$code" -eq 0 ] || [ "$code" -eq 2 ]; then
      return 0
    fi

    sleep 1
    i=$((i + 1))
  done

  die "$UNSEAL_SERVICE API did not become reachable"
}

json_read() {
  file=$1
  path=$2
  py=$(python_bin)

  "$py" - "$file" "$path" <<'PY'
import json
import sys

file_name = sys.argv[1]
path = sys.argv[2]

with open(file_name, "r", encoding="utf-8") as f:
    value = json.load(f)

for part in path.split("."):
    if isinstance(value, list):
        value = value[int(part)]
    else:
        value = value[part]

print(value)
PY
}

json_unseal_keys_for_threshold() {
  file=$1
  py=$(python_bin)

  "$py" - "$file" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)

threshold = int(data.get("unseal_threshold", 3))
keys = data.get("unseal_keys_b64") or []

for key in keys[:threshold]:
    print(key)
PY
}

unseal_from_init_file() {
  init_file=$1
  [ -f "$init_file" ] || die "Init file does not exist: $init_file"

  log "Unsealing $UNSEAL_SERVICE using threshold keys from $init_file"

  keys=$(json_unseal_keys_for_threshold "$init_file")
  echo "$keys"
  for key in $keys
  do
    [ -n "$key" ] || continue
    vault_unseal_exec operator unseal "$key" >/dev/null
  done

  sealed=$(vault_status_field Sealed || true)
  [ "$sealed" = "false" ] || die "$UNSEAL_SERVICE is still sealed after applying keys"

  log "$UNSEAL_SERVICE is unsealed"
}

configure_unseal_transit() {
  ensure_output_dir
  timestamp=$(date +%Y%m%d-%H%M%S)
  token_file="$BOOTSTRAP_OUTPUT_DIR/main-vault-transit-token-$timestamp.json"

  log "Checking Transit secrets engine..."
  if vault_unseal_exec_auth secrets list -format=json | grep -q '"transit/"'; then
    log "Transit is already enabled"
  else
    vault_unseal_exec_auth secrets enable transit >/dev/null
    log "Transit enabled"
  fi

  log "Checking Transit key: unseal-key"
  if vault_unseal_exec_auth read transit/keys/unseal-key >/dev/null 2>&1; then
    log "Transit key already exists: unseal-key"
  else
    vault_unseal_exec_auth write -f transit/keys/unseal-key >/dev/null
    log "Transit key created: unseal-key"
  fi

  log "Writing policy: unseal"
  vault_unseal_exec_auth policy write unseal /policy.hcl >/dev/null

  log "Creating orphan periodic token for main Vault auto-unseal..."
  vault_unseal_exec_auth token create \
    -orphan \
    -period=24h \
    -policy=unseal \
    -no-default-policy \
    -display-name=main-vault-auto-unseal \
    -format=json > "$token_file"

  chmod 600 "$token_file" 2>/dev/null || true

  log "Transit token bundle saved: $token_file"
  printf '%s\n' "$token_file"
}

print_transit_token_hint() {
  token_file=$1
  print_sensitive=${2:-false}

  if [ "$print_sensitive" = "true" ]; then
    token=$(json_read "$token_file" auth.client_token)
    accessor=$(json_read "$token_file" auth.accessor)
    printf '\n%s\n' "Copy into local .env if this is a dev environment only:"
    printf '%s\n' "VAULT_TRANSIT_TOKEN=$token"
    printf '\n%s\n' "Token accessor, useful for lookup/revoke:"
    printf '%s\n' "$accessor"
  else
    printf '\n%s\n' "Sensitive token was NOT printed."
    printf '%s\n' "To print it explicitly, rerun with --print-sensitive or read:"
    printf '%s\n' "  $token_file"
  fi
}

echo "[vault-common.sh] functions sourced"

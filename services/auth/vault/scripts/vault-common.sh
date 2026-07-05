#!/bin/sh

# Common helpers for host-side Vault devops scripts.
# The scripts execute the Vault CLI inside Vault containers through Docker Compose,
# so the host machine does not need the vault binary installed.

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VAULT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

COMPOSE_FILE=${COMPOSE_FILE:-"$VAULT_DIR/docker-compose.yml"}
BOOTSTRAP_OUTPUT_DIR=${BOOTSTRAP_OUTPUT_DIR:-"$VAULT_DIR/bootstrap-output"}

UNSEAL_SERVICE=${UNSEAL_SERVICE:-vault-unseal}
UNSEAL_VAULT_ADDR=${UNSEAL_VAULT_ADDR:-http://127.0.0.1:8200}

MAIN_LEADER_SERVICE=${MAIN_LEADER_SERVICE:-vault-leader}
MAIN_SLAVE1_SERVICE=${MAIN_SLAVE1_SERVICE:-vault-slave1}
MAIN_SLAVE2_SERVICE=${MAIN_SLAVE2_SERVICE:-vault-slave2}
MAIN_VAULT_ADDR=${MAIN_VAULT_ADDR:-http://127.0.0.1:8200}
MAIN_INTERNAL_ADDR=${MAIN_INTERNAL_ADDR:-http://vault-leader:8200}

JWT_TRANSIT_KEY=${JWT_TRANSIT_KEY:-auth-jwt}
JWT_TRANSIT_KEY_TYPE=${JWT_TRANSIT_KEY_TYPE:-rsa-2048}
JWT_SIGNER_POLICY=${JWT_SIGNER_POLICY:-auth-jwt-signer}
JWT_SIGNER_POLICY_FILE=${JWT_SIGNER_POLICY_FILE:-"$VAULT_DIR/policies/auth-jwt-signer.hcl"}
AUTH_SERVICE_TOKEN_PERIOD=${AUTH_SERVICE_TOKEN_PERIOD:-24h}

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

ensure_service() {
  service=$1
  log "Starting $service if needed..."
  compose up -d "$service"
}

vault_exec() {
  service=$1
  addr=$2
  shift 2
  compose exec -T "$service" env VAULT_ADDR="$addr" vault "$@"
}

vault_exec_auth_token() {
  service=$1
  addr=$2
  token=$3
  shift 3
  [ -n "$token" ] || die "Vault token is required for this operation"
  compose exec -T -e VAULT_TOKEN="$token" "$service" env VAULT_ADDR="$addr" vault "$@"
}

vault_write_policy_from_file() {
  service=$1
  addr=$2
  token=$3
  policy_name=$4
  policy_file=$5

  [ -f "$policy_file" ] || die "Policy file does not exist: $policy_file"
  cat "$policy_file" | compose exec -T -e VAULT_TOKEN="$token" "$service" \
    env VAULT_ADDR="$addr" vault policy write "$policy_name" - >/dev/null
}

vault_status_output_for() {
  service=$1
  addr=$2
  set +e
  output=$(vault_exec "$service" "$addr" status 2>&1)
  code=$?
  printf '%s\n' "$output"
  return "$code"
}

vault_status_field_for() {
  service=$1
  addr=$2
  field_name=$3
  vault_status_output_for "$service" "$addr" 2>/dev/null | awk -v key="$field_name" '$1 == key { print $2; exit }'
}

wait_for_vault_api() {
  service=$1
  addr=$2
  attempts=${3:-60}
  i=1

  while [ "$i" -le "$attempts" ]; do
    set +e
    vault_status_output_for "$service" "$addr" >/dev/null 2>&1
    code=$?

    # vault status returns 0 when unsealed and 2 when sealed/uninitialized.
    # Both mean the API is reachable.
    if [ "$code" -eq 0 ] || [ "$code" -eq 2 ]; then
      return 0
    fi

    sleep 1
    i=$((i + 1))
  done

  die "$service API did not become reachable"
}

wait_for_vault_unsealed() {
  service=$1
  addr=$2
  attempts=${3:-60}
  i=1

  while [ "$i" -le "$attempts" ]; do
    sealed=$(vault_status_field_for "$service" "$addr" Sealed || true)
    initialized=$(vault_status_field_for "$service" "$addr" Initialized || true)

    if [ "$initialized" = "true" ] && [ "$sealed" = "false" ]; then
      return 0
    fi

    sleep 1
    i=$((i + 1))
  done

  die "$service did not become initialized and unsealed"
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

ensure_unseal_storage_container() {
  ensure_service "$UNSEAL_SERVICE"
}

vault_unseal_exec() {
  vault_exec "$UNSEAL_SERVICE" "$UNSEAL_VAULT_ADDR" "$@"
}

vault_unseal_exec_auth() {
  [ -n "${VAULT_TOKEN:-}" ] || die "VAULT_TOKEN is required for this operation"
  vault_exec_auth_token "$UNSEAL_SERVICE" "$UNSEAL_VAULT_ADDR" "$VAULT_TOKEN" "$@"
}

vault_status_output() {
  vault_status_output_for "$UNSEAL_SERVICE" "$UNSEAL_VAULT_ADDR"
}

vault_status_field() {
  vault_status_field_for "$UNSEAL_SERVICE" "$UNSEAL_VAULT_ADDR" "$1"
}

wait_for_unseal_storage_api() {
  wait_for_vault_api "$UNSEAL_SERVICE" "$UNSEAL_VAULT_ADDR" "${1:-60}"
}

unseal_from_init_file() {
  init_file=$1
  [ -f "$init_file" ] || die "Init file does not exist: $init_file"

  log "Unsealing $UNSEAL_SERVICE using threshold keys from $init_file"

  keys=$(json_unseal_keys_for_threshold "$init_file")
  for key in $keys; do
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

  log "Checking Transit secrets engine on $UNSEAL_SERVICE..."
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


main_transit_token_configured() {
  if [ -n "${VAULT_TRANSIT_TOKEN:-}" ]; then
    return 0
  fi

  env_file="$VAULT_DIR/.env"
  [ -f "$env_file" ] || return 1

  token_line=$(grep -E '^VAULT_TRANSIT_TOKEN=' "$env_file" | tail -n 1 || true)
  [ -n "$token_line" ] || return 1

  token_value=${token_line#VAULT_TRANSIT_TOKEN=}
  [ -n "$token_value" ] || return 1
  [ "$token_value" != "replace-with-token-from-bootstrap-output" ] || return 1

  return 0
}

require_main_transit_token_configured() {
  main_transit_token_configured || die "VAULT_TRANSIT_TOKEN is not configured. Run scripts/bootstrap-unseal-storage.sh --print-sensitive, copy the printed token into .env, then retry."
}

ensure_main_leader_container() {
  ensure_service "$MAIN_LEADER_SERVICE"
}

ensure_main_cluster_containers() {
  ensure_service "$MAIN_LEADER_SERVICE"
  ensure_service "$MAIN_SLAVE1_SERVICE"
  ensure_service "$MAIN_SLAVE2_SERVICE"
}

main_vault_exec() {
  vault_exec "$MAIN_LEADER_SERVICE" "$MAIN_VAULT_ADDR" "$@"
}

main_vault_exec_auth() {
  [ -n "${VAULT_TOKEN:-}" ] || die "VAULT_TOKEN is required for this operation"
  vault_exec_auth_token "$MAIN_LEADER_SERVICE" "$MAIN_VAULT_ADDR" "$VAULT_TOKEN" "$@"
}

main_status_output() {
  vault_status_output_for "$MAIN_LEADER_SERVICE" "$MAIN_VAULT_ADDR"
}

main_status_field() {
  vault_status_field_for "$MAIN_LEADER_SERVICE" "$MAIN_VAULT_ADDR" "$1"
}

wait_for_main_leader_api() {
  wait_for_vault_api "$MAIN_LEADER_SERVICE" "$MAIN_VAULT_ADDR" "${1:-60}"
}

configure_main_transit() {
  create_dev_auth_token=${1:-false}
  print_sensitive=${2:-false}

  ensure_output_dir
  timestamp=$(date +%Y%m%d-%H%M%S)
  auth_token_file="$BOOTSTRAP_OUTPUT_DIR/auth-service-token-$timestamp.json"

  log "Checking Transit secrets engine on main Vault..."
  if main_vault_exec_auth secrets list -format=json | grep -q '"transit/"'; then
    log "Transit is already enabled"
  else
    main_vault_exec_auth secrets enable transit >/dev/null
    log "Transit enabled"
  fi

  log "Checking JWT signing key: transit/keys/$JWT_TRANSIT_KEY"
  if main_vault_exec_auth read "transit/keys/$JWT_TRANSIT_KEY" >/dev/null 2>&1; then
    log "Transit key already exists: $JWT_TRANSIT_KEY"
  else
    main_vault_exec_auth write "transit/keys/$JWT_TRANSIT_KEY" \
      type="$JWT_TRANSIT_KEY_TYPE" \
      exportable=false \
      allow_plaintext_backup=false >/dev/null
    log "Transit key created: $JWT_TRANSIT_KEY ($JWT_TRANSIT_KEY_TYPE)"
  fi

  log "Writing policy: $JWT_SIGNER_POLICY"
  vault_write_policy_from_file \
    "$MAIN_LEADER_SERVICE" \
    "$MAIN_VAULT_ADDR" \
    "$VAULT_TOKEN" \
    "$JWT_SIGNER_POLICY" \
    "$JWT_SIGNER_POLICY_FILE"

  if [ "$create_dev_auth_token" = "true" ]; then
    log "Creating dev auth-service token..."
    main_vault_exec_auth token create \
      -orphan \
      -period="$AUTH_SERVICE_TOKEN_PERIOD" \
      -policy="$JWT_SIGNER_POLICY" \
      -no-default-policy \
      -display-name=auth-service-dev \
      -format=json > "$auth_token_file"

    chmod 600 "$auth_token_file" 2>/dev/null || true
    log "Auth-service token bundle saved: $auth_token_file"

    if [ "$print_sensitive" = "true" ]; then
      token=$(json_read "$auth_token_file" auth.client_token)
      accessor=$(json_read "$auth_token_file" auth.accessor)
      printf '\n%s\n' "Copy into auth-service local env/config for dev only:"
      printf '%s\n' "VAULT_TOKEN=$token"
      printf '\n%s\n' "Auth-service token accessor, useful for lookup/revoke:"
      printf '%s\n' "$accessor"
    else
      printf '\n%s\n' "Auth-service token was created but NOT printed."
      printf '%s\n' "To inspect it, read:"
      printf '%s\n' "  $auth_token_file"
    fi
  fi
}

print_main_storage_api_examples() {
  printf '\n%s\n' "Main Vault API examples for containers on vault-internal:"
  printf '%s\n' "  VAULT_ADDR=$MAIN_INTERNAL_ADDR"
  printf '%s\n' "  Read JWT key metadata/public key:"
  printf '%s\n' "    GET $MAIN_INTERNAL_ADDR/v1/transit/keys/$JWT_TRANSIT_KEY"
  printf '%s\n' "  Sign JWT signing input with RS256-compatible padding:"
  printf '%s\n' "    POST $MAIN_INTERNAL_ADDR/v1/transit/sign/$JWT_TRANSIT_KEY/sha2-256"
  printf '%s\n' "    Body: {\"input\":\"<base64(jwt_header.payload)>\",\"signature_algorithm\":\"pkcs1v15\"}"
  printf '%s\n' "  Runtime token policy for auth service: $JWT_SIGNER_POLICY"
}

print_main_cluster_status() {
  for item in \
    "$MAIN_LEADER_SERVICE:$MAIN_VAULT_ADDR" \
    "$MAIN_SLAVE1_SERVICE:$MAIN_VAULT_ADDR" \
    "$MAIN_SLAVE2_SERVICE:$MAIN_VAULT_ADDR"
  do
    service=${item%%:*}
    addr=${item#*:}
    printf '\n%s\n' "== $service =="
    vault_status_output_for "$service" "$addr" || true
  done
}

print_raft_peers_if_authorized() {
  if [ -z "${VAULT_TOKEN:-}" ]; then
    printf '\n%s\n' "Raft peers were not queried because VAULT_TOKEN is not set."
    return 0
  fi

  printf '\n%s\n' "== main Vault raft peers =="
  main_vault_exec_auth operator raft list-peers || true
}

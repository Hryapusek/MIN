#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/vault-common.sh"

ensure_unseal_storage_container
wait_for_unseal_storage_api
vault_status_output || true

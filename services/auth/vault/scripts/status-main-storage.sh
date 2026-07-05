#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/vault-common.sh"

print_main_cluster_status
print_raft_peers_if_authorized

#!/bin/sh
set -eu

cat <<'MSG'
This container-side setup.sh is intentionally disabled.

Use the host-side scripts instead:
  ./scripts/bootstrap-unseal-storage.sh
  ./scripts/unseal-unseal-storage.sh
  ./scripts/configure-unseal-storage.sh
  ./scripts/status-unseal-storage.sh

Reason: blind `vault operator init` is dangerous after persistent data exists.
MSG

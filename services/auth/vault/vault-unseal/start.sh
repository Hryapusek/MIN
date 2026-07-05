#!/bin/sh
set -eu

mkdir -p /vault/data/unseal-data
vault server -config=/vault/config/vault.hcl

#!/bin/sh

mkdir -p /vault/data/leader-data
vault server -config=/vault/config/vault.hcl
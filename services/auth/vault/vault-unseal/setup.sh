#!/usr/bin/bash

export VAULT_ADDR=http://127.0.0.1:8200
vault operator init
vault operator unseal
vault operator unseal
vault operator unseal
vault login

vault secrets list
vault secrets enable transit
vault write -f transit/keys/unseal-key
vault list transit/keys
vault policy write unseal /policy.hcl
vault token create -orphan -period=24h -policy=unseal

# vault token lookup -accessor

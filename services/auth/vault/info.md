# Vault notes

This file is kept as a lightweight pointer for older notes. The current local
workflow is documented in `README.md` and `scripts/README.md`.

Current architecture:

```txt
vault-unseal
  root-of-trust Vault used for Transit auto-unseal

vault-leader / vault-slave1 / vault-slave2
  main application Vault Raft cluster
  auto-unsealed through vault-unseal
```

Important rules:

- Initialize `vault-unseal` once with `scripts/bootstrap-unseal-storage.sh`.
- Copy the generated `VAULT_TRANSIT_TOKEN` into local `.env`.
- Initialize only `vault-leader` for the main cluster with `scripts/bootstrap-main-storage.sh`.
- Do not run `vault operator init` on the slave nodes; they join through Raft `retry_join`.
- Main Vault init produces recovery keys, not normal unseal keys, because it uses Transit auto-unseal.
- Do not commit `.env` or `bootstrap-output/`.

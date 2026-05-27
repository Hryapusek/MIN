# Vault
Vault is used to store APPLICATION secrets, such as API keys, passwords, and tokens.
It should not be used to store some user data, like passwords and other.

We use backend storage raft to have high availability. The idea is simple as that. If one node fails, the other nodes can take over using voting mechanism. Below are simple setup instructions.

## Setup
### Leader node
First we should create a directory for vault data. We better put it under a docker volume to make it persistent.
Example:
```bash
mkdir -p mkdir /vault/data/leader-data
```

Then we should create a configuration file for vault.
For leader node:
```hcl
storage "raft" {
  path = "/vault/data/leader-data"
  node_id = "node1"
}

listener "tcp" {
  address         = "0.0.0.0:8200"
  cluster_address = "0.0.0.0:8201"
  tls_disable     = true
}

api_addr     = "http://127.0.0.1:8200"
cluster_addr = "http://vault-leader:8201"
ui = true
disable_mlock = false
```

- disable_mlock is needed to prevent vault saving passwords in swap space. This is a security issue
- ui is needed to access vault ui
- cluster_addr see [here](https://developer.hashicorp.com/vault/docs/configuration#cluster_addr)
- api_addr see [here](https://developer.hashicorp.com/vault/docs/configuration#api_addr)
- listener is just accepting connections from outside
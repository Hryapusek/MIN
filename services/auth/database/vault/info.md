# Vault
Vault is used to store APPLICATION secrets, such as API keys, passwords, and tokens.
It should not be used to store some user data, like passwords and other.

We use backend storage raft to have high availability. The idea is simple as that. If one node fails, the other nodes can take over using voting mechanism. Below are simple setup instructions.

## Setup
### Nodes setup
#### Leader node
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

#### Slave node

Again we create a directory:
```bash
mkdir -p /vault/data/slave2-data
```

And a configuration file:

```hcl
storage "raft" {
  path = "/vault/data/slave1-data"
  node_id = "slave1"

  retry_join {
    leader_api_addr = "http://vault-leader:8200"
  }
}

listener "tcp" {
  address         = "0.0.0.0:8200"
  cluster_address = "0.0.0.0:8201"
  tls_disable     = true
}

api_addr     = "http://127.0.0.1:8200"
cluster_addr = "http://vault-slave1:8201"
ui = true
disable_mlock = false
```

### General configuration

### Vault auto unseal storage configuration
Example configuration looks like this. First we should setup the vault as a default storage for example like this:

```python
storage "raft" {
  path = "/vault/data/unseal-data"
  node_id = "unseal"
}

listener "tcp" {
  address         = "0.0.0.0:8200"
  cluster_address = "0.0.0.0:8201"
  tls_disable     = true
}

api_addr     = "http://127.0.0.1:8200"
cluster_addr = "http://vault-unseal:8201"
ui = true
disable_mlock = false
```

Put it as usual into `/vault/config/vault.hcl`

Then after running the server using `vault server -config=/vault/config/vault.hcl` we should continue the setup in a separate console.

First we should export the address of vault api.
```bash
export VAULT_ADDR=http://127.0.0.1:8200
```
For now the vault is sealed, so we should unseal it first

```bash
vault operator init
```

> This command also accepts some parameters. The most popular and easy are -key-shares, -key-threshold, -recovery-shares, -recovery-threshold

First call of `vault operator init` does not require no credentials. After calling this command and waiting for a little time - we should see unseal keys on the screen. Share them between operators(or just save to plain txt file huh) and pass the key one by one to the following command:

```bash
vault operator unseal
```

This command should be called three times in order to unlock the vault.

After the third unsealing - we shuld see something like this:

```txt
Unseal Key 1: EutYOnNqwzo0PJLmCi0y5/YgGjuKhI2erWDvYe9PU3FR
Unseal Key 2: xPqr2UyyD1HqKs9TpzETri6rCMrNeAwNHqfEwTL41fYa
Unseal Key 3: eM8SSsdsCaL26g8pvBubdhLxmyr9/wafvl1+eMuKzpEI
Unseal Key 4: ezKatmIQQDKVS3WBgrWyPx0VRA5wzdoZT2MYhMY7oToq
Unseal Key 5: njoAFwuBekiZ8gTFONzERHP1lpcJFH+oamnjchTFdZJf

Initial Root Token: token_here

Vault initialized with 5 key shares and a key threshold of 3. Please securely
distribute the key shares printed above. When the Vault is re-sealed,
restarted, or stopped, you must supply at least 3 of these keys to unseal it
before it can start servicing requests.

Vault does not store the generated root key. Without at least 3 keys to
reconstruct the root key, Vault will remain permanently sealed!

It is possible to generate new unseal keys, provided you have a quorum of
existing unseal keys shares. See "vault operator rekey" for more information.
```

Next thing we do is logging using the token

```bash
vault login
```

> This command also supports a set of parameters. Most popular are `-no-store`, `-method`. Example: `vault login -method=userpass username=my-username`

We should provide the token into the prompted line. Its not neccessarily the root token of course. You can create tokens with some policies using the command:
```bash
vault token create -orphan -period=24h -policy=policy-name
```

> There are much args as well

In fact, we should only use root token on bootstrap. Then we should save it in a glass box or even better revoke it for the further safety

After we successfully logged in, we can continue our setup. 

Right after the container creation - we should see the following result after calling the `vault secrets list`
```txt
Path               Type              Accessor                   Description
----               ----              --------                   -----------
agent-registry/    agent_registry    agent-registry_fd948700    agent registry
cubbyhole/         cubbyhole         cubbyhole_bb61544b         per-token private secret storage
identity/          identity          identity_31dd1610          identity store
sys/               system            system_fb3aef70            system endpoints used for control, policy and debugging
```

If you still remember - we are setting up a transit point. As GPT explained:

> Transit is “cryptography as a service”: Vault keeps the key and exposes operations like encrypt/decrypt/sign/verify. It does not store your application data

Transit is a vault builtin plugin. So we should just enable it:
```bash
vault secrets enable transit
```

Next thing we want - create an unseal key. We are asking vault to do that, we dont need to worry about key type, vault will do it for us:
```bash
vault write -f transit/keys/unseal-key
```
Here `unseal-key` is just the name of the key.

Vault has deny-by-default policy. Which means right now nobody can access this key. We should manually create policy that allows usage of that key. Here we go:
```hcl
path "transit/encrypt/unseal-key" {
  capabilities = ["update"]
}

path "transit/decrypt/unseal-key" {
  capabilities = ["update"]
}
```

We can save this policy to a file and run `vault policy write unseal /policy.hcl`. `unseal` here is just a policy name.

Policy itself does not do much. We should somehow authenticate the user. We should create token attached to this policy.
We create a token with renewal because we dont want to restart our nodes every 24h.
```bash
vault token create -orphan -period=24h -policy=unseal
```
This token will be passed to each auto unseal vault node.
We finished setting up the unseal storage.


#### Few words on policies
...

### Vault auto unseal target node
Setup is mostly the same except for the

The config:
```hcl
storage "raft" {
  path = "/vault/data/leader-data"
  node_id = "leader"
}

seal "transit" {
  address         = "http://vault-unseal:8200"
  key_name        = "unseal-key"
  mount_path      = "transit/"
  disable_renewal = "false"
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



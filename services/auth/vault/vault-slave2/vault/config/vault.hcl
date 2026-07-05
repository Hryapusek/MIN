storage "raft" {
  path = "/vault/data/slave2-data"
  node_id = "slave2"

  retry_join {
    leader_api_addr = "http://vault-leader:8200"
  }
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

api_addr     = "http://vault-slave2:8200"
cluster_addr = "http://vault-slave2:8201"
ui = true
disable_mlock = false
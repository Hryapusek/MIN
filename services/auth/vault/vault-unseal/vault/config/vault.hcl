storage "raft" {
  path = "/vault/data/unseal-data"
  node_id = "unseal"
}

listener "tcp" {
  address         = "0.0.0.0:8200"
  cluster_address = "0.0.0.0:8201"
  tls_disable     = true
}

api_addr     = "http://vault-unseal:8200"
cluster_addr = "http://vault-unseal:8201"
ui = true
disable_mlock = false
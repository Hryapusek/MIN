storage "raft" {
  path = "/vault/data/leader-data"
  node_id = "leader"
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
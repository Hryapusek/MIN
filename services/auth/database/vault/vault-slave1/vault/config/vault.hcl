storage "raft" {
  path = "/vault/data/slave1-data"
  node_id = "slave1"

  retry-join {
    leader_api_addr = "http://vault-BADleader:8200"
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
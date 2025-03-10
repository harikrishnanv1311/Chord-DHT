import hashlib
import os

class ChordNode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.node_id = self.hash_ip(ip, port)
        # Read successor info from environment variables
        self.successor = {
            "ip": os.getenv("SUCCESSOR_HOST", ip),
            "port": int(os.getenv("SUCCESSOR_PORT", port))
        }
        self.predecessor = None
        self.data_store = {}

    def hash_ip(self, ip, port):
        hash_val = hashlib.sha1(f"{ip}:{port}".encode()).hexdigest()
        return int(hash_val, 16) % (2**160)

    def store_data(self, key, value):
        self.data_store[key] = value
        print(f"✅ Stored {key} → {value}")

    def get_data(self, key):
        return self.data_store.get(key, "❌ Key not found")

    def is_responsible(self, key_id, successor_node_id):
        """Determine if this node is responsible for key_id,
           given its successor's node_id (handling wrap-around)."""
        if self.node_id < successor_node_id:
            return self.node_id <= key_id < successor_node_id
        else:
            # Wrap-around case: if key is greater than self.node_id or less than successor's id
            return key_id >= self.node_id or key_id < successor_node_id

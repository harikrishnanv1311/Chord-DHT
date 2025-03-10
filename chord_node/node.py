import hashlib

class ChordNode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.node_id = self.hash_ip(ip, port)
        self.successor = None  # Will point to next node in the Chord ring
        self.predecessor = None  # Will point to previous node
        self.data_store = {}  # Key-value storage

    def hash_ip(self, ip, port):
        """Generate a unique ID using SHA-1"""
        hash_val = hashlib.sha1(f"{ip}:{port}".encode()).hexdigest()
        return int(hash_val, 16) % (2**160)

    def store_data(self, key, value):
        """Store a key-value pair in the node"""
        self.data_store[key] = value
        print(f"✅ Stored {key} → {value}")

    def get_data(self, key):
        """Retrieve the value for a given key"""
        return self.data_store.get(key, "❌ Key not found")

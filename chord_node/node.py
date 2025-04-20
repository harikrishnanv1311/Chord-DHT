import hashlib
import os
import requests
import threading
import time


class ChordNode:
    def __init__(self, ip, port, m=160):
        self.ip = ip
        self.port = port
        self.m = m  # number of bits in identifier space
        self.node_id = self.hash_ip(ip, port)
        self.fix_finger_index = 0
        self.successor = {"node_id": self.node_id, "ip": self.ip, "port": self.port}
        self.predecessor = {"node_id": self.node_id, "ip": self.ip, "port": self.port}
        self.data_store = {}
        # Initialize finger table with self as all successors initially
        self.finger_table = [{"start": (self.node_id + (2**i)) % (2**self.m),
                            "successor": {"node_id": self.node_id, "ip": self.ip, "port": self.port}}
                           for i in range(self.m)]
        print(f"Node initialized with ID: {self.node_id}")

    def hash_ip(self, ip, port):
        """Hash the IP:port combination to get a node identifier in the Chord ring."""
        h = hashlib.sha1(f"{ip}:{port}".encode()).hexdigest()
        return int(h, 16) % (2**self.m)

    def hash_key(self, key):
        """Hash a key to determine its position in the Chord ring."""
        h = hashlib.sha1(key.encode()).hexdigest()
        return int(h, 16) % (2**self.m)

    def store_data(self, key, value):
        """Store data in the local key-value store."""
        self.data_store[key] = value
        print(f"Stored key '{key}' -> '{value}' at node {self.node_id}")
        return True

    def get_data(self, key):
        """Retrieve data from the local key-value store."""
        return self.data_store.get(key, None)

    def in_interval(self, x, a, b, inclusive_right=True, inclusive_left=False):
        """Check if x is in the interval (a, b] on a circular space."""
        if inclusive_left:
            if a == x:
                return True
        else:
            if a == x:
                return False
        
        if inclusive_right:
            if x == b:
                return True
        else:
            if x == b:
                return False
            
        if a < b:
            return a < x < b or (inclusive_right and x == b) or (inclusive_left and x == a)
        else:  # Wrap-around
            return x > a or x < b or (inclusive_right and x == b) or (inclusive_left and x == a)

    def is_responsible(self, key_id):
        """Determine if this node is responsible for the given key_id."""
        if self.predecessor is None:
            return True  # Only node in network
        return self.in_interval(key_id, self.predecessor["node_id"], self.node_id, inclusive_right=True)

    def closest_preceding_finger(self, key_id):
        """Find the closest preceding finger for a key_id."""
        for i in range(self.m - 1, -1, -1):
            if self.finger_table[i] is not None:
                candidate = self.finger_table[i]["successor"]
                if self.in_interval(candidate["node_id"], self.node_id, key_id, inclusive_right=False):
                    return candidate
        return {"node_id": self.node_id, "ip": self.ip, "port": self.port}

    def find_successor(self, key_id):
        """Find the successor node for a key_id."""
        # If key_id is in (n, successor], return successor
        if self.in_interval(key_id, self.node_id, self.successor["node_id"], inclusive_right=True):
            return self.successor
        
        # Otherwise, find the closest preceding finger and forward the query
        n_prime = self.closest_preceding_finger(key_id)
        # print(f"Closest Preceding finger for {key_id}: {n_prime}")
        
        # If n_prime is self, return immediate successor
        if n_prime["node_id"] == self.node_id:
            return self.successor
        
        # Forward the query to n_prime
        try:
            url = f"http://{n_prime['ip']}:{n_prime['port']}/find_successor?key_id={key_id}"
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error finding successor via {n_prime}: {e}")
            return self.successor  # Fallback
        
        return self.successor  # Fallback

    def find_predecessor(self, key_id):
        """Find the predecessor node for a key_id."""
        if self.successor["node_id"] == self.node_id:
            return {"node_id": self.node_id, "ip": self.ip, "port": self.port}
            
        # If key_id is in (n, successor], return self
        if self.in_interval(key_id, self.node_id, self.successor["node_id"], inclusive_right=True):
            return {"node_id": self.node_id, "ip": self.ip, "port": self.port}
        
        n_prime = {"node_id": self.node_id, "ip": self.ip, "port": self.port}
        n_succ = self.successor
        
        while not self.in_interval(key_id, n_prime["node_id"], n_succ["node_id"], inclusive_right=True):
            if n_prime["node_id"] == self.node_id:
                n_prime = self.closest_preceding_finger(key_id)
                if n_prime["node_id"] == self.node_id:
                    return {"node_id": self.node_id, "ip": self.ip, "port": self.port}
            else:
                try:
                    url = f"http://{n_prime['ip']}:{n_prime['port']}/closest_preceding_finger?key_id={key_id}"
                    resp = requests.get(url, timeout=300)
                    if resp.status_code == 200:
                        n_prime = resp.json()
                    else:
                        return {"node_id": self.node_id, "ip": self.ip, "port": self.port}
                except Exception as e:
                    print(f"Error finding closest preceding finger: {e}")
                    return {"node_id": self.node_id, "ip": self.ip, "port": self.port}
            
            try:
                url = f"http://{n_prime['ip']}:{n_prime['port']}/successor"
                resp = requests.get(url, timeout=300)
                if resp.status_code == 200:
                    n_succ = resp.json()
                else:
                    return n_prime
            except Exception as e:
                print(f"Error getting successor of {n_prime}: {e}")
                return n_prime
                
        return n_prime

    def join(self, bootstrap_address=None):
        """Join the Chord ring using a bootstrap node."""
        if bootstrap_address is None:
            # First node in the network
            print(f"First node in network with ID {self.node_id}")
            self.predecessor = None
            return True
            
        try:
            # print(f"Joining network via {bootstrap_address}")
            # Find our successor through the bootstrap node
            url = f"http://{bootstrap_address}/find_successor?key_id={self.node_id}"
            resp = requests.get(url, timeout=300)
            if resp.status_code == 200:
                self.successor = resp.json()
                print(f"Set successor to {self.successor}")


                # *** New: Get the old predecessor from our successor ***
                url_pred = f"http://{self.successor['ip']}:{self.successor['port']}/get_predecessor"
                resp_pred = requests.get(url_pred, timeout=300)
                if resp_pred.status_code == 200 and resp_pred.json():
                    old_pred = resp_pred.json()
                    # print(f"Old predecessor obtained: {old_pred}")
                else:
                    old_pred = None
                    print("Failed to get old predecessor from successor")
                
                # Now update our finger table
                self.init_finger_table(bootstrap_address)

                # REMOVE THIS WHEN STABILIZATION ALGORITHM IS IMPLEMENTED
                # Ask our predecessor to update its successor pointer to us
                # self.update_predecessor_successor()
                
                # Notify our successor
                self.notify_successor()
                
                 # Transfer keys using the old predecessor as the lower bound if available
                if old_pred is not None:
                    self.transfer_keys_from_successor(lower_bound=old_pred["node_id"])
                else:
                    self.transfer_keys_from_successor()
                
                return True
            else:
                print(f"Failed to get successor from bootstrap: {resp.status_code}, {resp.text}")
                return False
        except Exception as e:
            print(f"Error joining network: {e}")
            return False

    def init_finger_table(self, bootstrap_address):
        """Initialize the finger table using entries from the bootstrap node."""
        # print(f"Initializing finger table via {bootstrap_address}")
        
        # Set the first finger's successor to our own successor
        self.finger_table[0]["successor"] = self.successor
        
        try:
            # Get predecessor of our successor
            url = f"http://{self.successor['ip']}:{self.successor['port']}/get_predecessor"
            resp = requests.get(url, timeout=300)
            # print(f"Response returned from init_finger_table() while fetching predecessor of successor {resp}")
            if resp.status_code == 200 and resp.json():
                self.predecessor = resp.json()
                # print(f"Set predecessor to {self.predecessor}")
            else:
                print("Failed to get predecessor from successor")
        except Exception as e:
            print(f"Error getting predecessor: {e}")
        
        # For each remaining finger
        for i in range(1, self.m):
            start = (self.node_id + (2**i)) % (2**self.m)
            
            # If start is in [n, finger[i-1].successor)
            if self.in_interval(start, self.node_id, self.finger_table[i-1]["successor"]["node_id"], 
                               inclusive_left=True, inclusive_right=False):
                self.finger_table[i]["successor"] = self.finger_table[i-1]["successor"]
            else:
                # Otherwise, find the successor for this finger through the bootstrap
                try:
                    url = f"http://{bootstrap_address}/find_successor?key_id={start}"
                    resp = requests.get(url, timeout=300)
                    if resp.status_code == 200:
                        self.finger_table[i]["successor"] = resp.json()
                    else:
                        print(f"Failed to find successor for finger {i}")
                except Exception as e:
                    print(f"Error finding successor for finger {i}: {e}")
        
        # print(f"Finger table initialized: {self.finger_table}")
        
        # Update other nodes that should point to us
        self.update_others()

    def update_others(self):
        """Update all nodes whose finger tables should point to us."""
        # print("Updating other nodes' finger tables")
        
        for i in range(self.m):
            # Find the last node p whose i-th finger might be us
            # p = find_predecessor((n - 2^(i-1)) mod 2^m)
            p_id = (self.node_id - (2**i)) % (2**self.m)
            p = self.find_predecessor(p_id)
            
            if p["node_id"] != self.node_id:
                try:
                    # Tell p to update its finger table with us as the i-th finger successor
                    url = f"http://{p['ip']}:{p['port']}/update_finger_table"
                    data = {
                        "i": i,
                        "s": {"node_id": self.node_id, "ip": self.ip, "port": self.port}
                    }
                    resp = requests.post(url, json=data, timeout=300)
                    if resp.status_code == 200:
                        print(f"Updated node {p['node_id']} finger table entry {i}")
                    else:
                        print(f"Failed to update node {p['node_id']} finger table: {resp.status_code}")
                except Exception as e:
                    print(f"Error updating other node's finger table: {e}")

    def update_finger_table(self, s, i):
        """Update the i-th finger table entry to s if appropriate."""
        if (self.finger_table[i]["successor"]["node_id"] == self.node_id or 
            self.in_interval(s["node_id"], self.node_id, self.finger_table[i]["successor"]["node_id"], inclusive_right=False)):
            
            self.finger_table[i]["successor"] = s
            # print(f"Updated finger table entry {i} to node {s['node_id']}")
            
            # Propagate update to predecessor if needed
            if self.predecessor and self.predecessor["node_id"] != s["node_id"]:
                try:
                    url = f"http://{self.predecessor['ip']}:{self.predecessor['port']}/update_finger_table"
                    data = {"i": i, "s": s}
                    requests.post(url, json=data, timeout=300)
                except Exception as e:
                    print(f"Error propagating finger update to predecessor: {e}")
            
            return True
        return False

    def notify_successor(self):
        """Notify our successor that we might be its predecessor."""
        try:
            url = f"http://{self.successor['ip']}:{self.successor['port']}/notify"
            data = {"node_id": self.node_id, "ip": self.ip, "port": self.port}
            resp = requests.post(url, json=data, timeout=300)
            if resp.status_code == 200:
                # print(f"Notified successor {self.successor['node_id']}")
                return True
            else:
                # print(f"Failed to notify successor: {resp.status_code}")
                return False
        except Exception as e:
            print(f"Error notifying successor: {e}")   
            return False

    def notify(self, node):
        """Process notification from another node that it might be our predecessor."""
        if (self.predecessor is None or 
            self.in_interval(node["node_id"], self.predecessor["node_id"], self.node_id, inclusive_right=False)):
            
            self.predecessor = node
            # print(f"Updated predecessor to node {node['node_id']}")
            return True
        return False

    """REMOVE THIS TEMPORARY CODE WHEN IMPLEMENTING THE STABILIZATION ALGORITHM"""
    def update_predecessor_successor(self):
        """Ask our predecessor to set its successor pointer to this node if appropriate."""
        if self.predecessor is None:
            return False
        try:
            url = f"http://{self.predecessor['ip']}:{self.predecessor['port']}/set_successor"
            data = {"node_id": self.node_id, "ip": self.ip, "port": self.port}
            resp = requests.post(url, json=data, timeout=300)
            if resp.status_code == 200:
                # print(f"Predecessor {self.predecessor['node_id']} updated its successor to {self.node_id}")
                return True
            else:
                # print(f"Failed to update predecessor's successor: {resp.status_code}")
                return False
        except Exception as e:
            # print(f"Error updating predecessor's successor: {e}")
            return False

      


    def transfer_keys_from_successor(self, lower_bound=None):
        """Request keys from successor that should now belong to us."""
        if self.successor["node_id"] == self.node_id:
            return  # We are the only node
            
        try:
            url = f"http://{self.successor['ip']}:{self.successor['port']}/transfer_keys"
            data = {"node_id": self.node_id}
            if lower_bound is not None:
                data["lower_bound"] = lower_bound
            resp = requests.post(url, json=data, timeout=300)
            if resp.status_code == 200:
                keys = resp.json().get("keys", {})
                for k, v in keys.items():
                    self.store_data(k, v)
                # print(f"Received {len(keys)} keys from successor")
                return True
            else:
                # print(f"Failed to transfer keys: {resp.status_code}")
                return False
        except Exception as e:
            # print(f"Error transferring keys: {e}")
            return False

    def transfer_keys_to_predecessor(self, new_pred_id, lower_bound=None):
        """Transfer keys that should belong to a new predecessor.
        If lower_bound is provided, use it as the lower bound of the interval;
        otherwise, use the current predecessor's node_id."""
        keys_to_transfer = {}
        keys_to_remove = []
        if lower_bound is None:
            lower_bound = self.predecessor["node_id"] if self.predecessor else self.node_id

        for k, v in self.data_store.items():
            key_id = self.hash_key(k)
            if self.in_interval(key_id, lower_bound, new_pred_id, inclusive_right=True):
                keys_to_transfer[k] = v
                keys_to_remove.append(k)
        
        for k in keys_to_remove:
            del self.data_store[k]
            
        # print(f"Transferring {len(keys_to_transfer)} keys to predecessor using lower bound {lower_bound}")
        return keys_to_transfer

    def as_dict(self):
        return {"node_id": self.node_id, "ip": self.ip, "port": self.port}

    def stabilize(self):
        """Verify your immediate successor and tell it about yourself."""
        try:
            url = f"http://{self.successor['ip']}:{self.successor['port']}/get_predecessor"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                x = response.json()
                if x is not None and self.in_interval(x["node_id"], self.node_id, self.successor["node_id"]):
                    self.successor = x

            url = f"http://{self.successor['ip']}:{self.successor['port']}/notify"
            requests.post(url, json=self.as_dict(), timeout=5)
        except requests.RequestException:
            print(f"[{self.node_id}] Could not contact successor {self.successor['node_id']}, keeping current")

    def fix_fingers(self):
        """Periodically refresh finger table entries."""
        self.fix_finger_index = (self.fix_finger_index + 1) % self.m
        start = (self.node_id + 2 ** self.fix_finger_index) % (2 ** self.m)
        self.finger_table[self.fix_finger_index]["start"] = start
        self.finger_table[self.fix_finger_index]["successor"] = self.find_successor(start)

    def depart(self):
        print(f"[Node {self.node_id}] Leaving the network...")

        try:
            if self.successor:
                print(f"[Node {self.node_id}] Transferring data to successor {self.successor['node_id']}")
                url = f"http://{self.successor['ip']}:{self.successor['port']}/receive_keys"
                requests.post(url, json={"data": self.data_store})
            else:
                print(f"[Node {self.node_id}] No successor to transfer keys to.")

            if self.predecessor:
                print(f"[Node {self.node_id}] Updating predecessor's successor to {self.successor['node_id']}")
                url = f"http://{self.predecessor['ip']}:{self.predecessor['port']}/update_successor"
                requests.post(url, json={"successor": self.successor})
            else:
                print(f"[Node {self.node_id}] No predecessor to update.")

            if self.successor:
                print(f"[Node {self.node_id}] Updating successor's predecessor to {self.predecessor['node_id']}")
                url = f"http://{self.successor['ip']}:{self.successor['port']}/update_predecessor"
                requests.post(url, json={"predecessor": self.predecessor})

            self.successor = None
            self.predecessor = None
            self.data_store = {}

            # print(f"[Node {self.node_id}] Successfully departed from the network.")

            return True

        except Exception as e:
            print(f"[Node {self.node_id}] Error during departure: {e}")
            return False

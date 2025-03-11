import hashlib
import os
import requests

class ChordNode:
    def __init__(self, ip, port, m=160):
        self.ip = ip
        self.port = port
        self.m = m  # number of bits in identifier space
        self.node_id = self.hash_ip(ip, port)
        self.successor = None   # dict: {"node_id": ..., "ip": ..., "port": ...}
        self.predecessor = None # dict: same structure
        self.data_store = {}    # key-value store
        # Finger table: list of m entries, each entry is a dict with "start" and "successor"
        self.finger_table = [None] * self.m

    def hash_ip(self, ip, port):
        h = hashlib.sha1(f"{ip}:{port}".encode()).hexdigest()
        return int(h, 16) % (2**self.m)

    def store_data(self, key, value):
        self.data_store[key] = value
        print(f"Stored key '{key}' -> '{value}' at node {self.node_id}")

    def get_data(self, key):
        return self.data_store.get(key, None)

    def in_interval(self, x, a, b, inclusive_right=True):
        # Checks if x is in (a, b] (if inclusive_right True) on a circular space of size 2**m.
        if a < b:
            return a < x <= b if inclusive_right else a < x < b
        else:
            # Wrap-around: (a, 2**m-1] U [0, b]
            return x > a or x <= b if inclusive_right else x > a or x < b

    def is_responsible(self, key_id):
        # In Chord, node n is responsible for keys in (predecessor, n]
        if self.predecessor is None:
            return True  # Only node in network
        return self.in_interval(key_id, self.predecessor["node_id"], self.node_id, inclusive_right=True)

    def closest_preceding_finger(self, key_id):
        # Scan finger table from highest index to lowest
        for i in range(self.m - 1, -1, -1):
            if self.finger_table[i] is not None:
                candidate = self.finger_table[i]["successor"]
                if self.in_interval(candidate["node_id"], self.node_id, key_id, inclusive_right=False):
                    return candidate
        return {"node_id": self.node_id, "ip": self.ip, "port": self.port}

    def find_successor(self, key_id):
        # If this node is responsible, return self; otherwise, use finger table jumps.
        if self.is_responsible(key_id):
            return {"node_id": self.node_id, "ip": self.ip, "port": self.port}
        cp = self.closest_preceding_finger(key_id)
        if cp["node_id"] == self.node_id:
            return self.successor  # fallback
        try:
            url = f"http://{cp['ip']}:{cp['port']}/find_successor?key_id={key_id}"
            resp = requests.get(url)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error contacting node {cp}: {e}")
        return None

    # --- Node join and update methods as per the paper ---

    def join(self, bootstrap_address):
        """
        Join the network by contacting the bootstrap node.
        Steps:
         1. Find our immediate successor.
         2. Get our predecessor from our successor.
         3. Notify our successor.
         4. (Key transfer happens later.)
        """
        try:
            # Step 1: Find our immediate successor.
            url = f"http://{bootstrap_address}/find_successor?key_id={self.node_id}"
            resp = requests.get(url)
            if resp.status_code == 200:
                self.successor = resp.json()
                print(f"Join: Set successor to {self.successor}")
            else:
                print("Join: Failed to get successor from bootstrap")
        except Exception as e:
            print(f"Join: Exception contacting bootstrap: {e}")

        try:
            # Step 2: Get our predecessor from our successor.
            url = f"http://{self.successor['ip']}:{self.successor['port']}/predecessor"
            resp = requests.get(url)
            if resp.status_code == 200:
                self.predecessor = resp.json()
                print(f"Join: Set predecessor to {self.predecessor}")
            else:
                print("Join: Failed to get predecessor from successor")
        except Exception as e:
            print(f"Join: Exception contacting successor for predecessor: {e}")

        try:
            # Step 3: Notify our successor.
            url = f"http://{self.successor['ip']}:{self.successor['port']}/notify"
            requests.post(url, json={"node_id": self.node_id, "ip": self.ip, "port": self.port})
        except Exception as e:
            print(f"Join: Exception notifying successor: {e}")

    def init_finger_table(self, bootstrap_address):
        # First, join the network.
        self.join(bootstrap_address)
        # Copy finger table from successor.
        try:
            url = f"http://{self.successor['ip']}:{self.successor['port']}/finger_table"
            resp = requests.get(url)
            if resp.status_code == 200:
                succ_ft = resp.json().get("finger_table", [])
                self.finger_table = succ_ft.copy()
                print(f"Copied finger table from successor: {succ_ft}")
            else:
                print("Failed to copy finger table from successor")
        except Exception as e:
            print(f"Error copying finger table: {e}")

        # Adjust finger table entries.
        for i in range(self.m):
            start = (self.node_id + (2**i)) % (2**self.m)
            try:
                url = f"http://{self.successor['ip']}:{self.successor['port']}/find_successor?key_id={start}"
                resp = requests.get(url)
                if resp.status_code == 200:
                    self.finger_table[i] = {"start": start, "successor": resp.json()}
            except Exception as e:
                print(f"Error adjusting finger table entry {i}: {e}")
        print(f"Finger table for node {self.node_id} initialized: {self.finger_table}")
        # Now update other nodes about our presence.
        self.update_others()
        # Transfer keys from our successor.
        self.transfer_keys()

    def update_finger_table(self, candidate, i):
        """
        Update the i-th finger if candidate lies in [self.node_id, finger[i].successor)
        Then, recursively update our predecessor's finger table.
        """
        current = self.finger_table[i]["successor"]
        if self.in_interval(candidate["node_id"], self.node_id, current["node_id"], inclusive_right=False):
            # Update finger table entry.
            self.finger_table[i]["successor"] = candidate
            print(f"Node {self.node_id}: Updated finger[{i}] to candidate {candidate['node_id']}")
            # Find predecessor and update its finger table, unless it's self.
            if self.predecessor and self.predecessor["node_id"] != self.node_id:
                try:
                    url = f"http://{self.predecessor['ip']}:{self.predecessor['port']}/update_finger_table"
                    requests.post(url, json={"candidate": candidate, "i": i})
                except Exception as e:
                    print(f"Error notifying predecessor for finger update: {e}")

    def update_others(self):
        """
        For each finger entry i, find the node p whose finger table might need to be updated to point to self.
        p = find_predecessor( (self.node_id - 2^(i-1)) mod 2^m )
        Then, p.update_finger_table(self, i)
        """
        for i in range(self.m):
            target = (self.node_id - (2**i)) % (2**self.m)
            try:
                p = self.find_predecessor(target)
                if p["node_id"] != self.node_id:
                    url = f"http://{p['ip']}:{p['port']}/update_finger_table"
                    requests.post(url, json={"candidate": {"node_id": self.node_id, "ip": self.ip, "port": self.port}, "i": i})
                    print(f"Updated node {p['node_id']} finger[{i}] with candidate {self.node_id}")
            except Exception as e:
                print(f"Error in update_others for finger {i}: {e}")

    def find_predecessor(self, key_id):
        """
        Iteratively find the predecessor of key_id.
        """
        n_prime = {"node_id": self.node_id, "ip": self.ip, "port": self.port}
        while not self.in_interval(key_id, n_prime["node_id"], self.get_successor(n_prime)["node_id"], inclusive_right=True):
            n_prime = self.get_closest_preceding_finger(n_prime, key_id)
        return n_prime

    def get_successor(self, node_info):
        """
        For a given node_info, retrieve its successor by contacting its /node_id endpoint.
        Here we assume node_info is local if it is self.
        """
        if node_info["node_id"] == self.node_id:
            return self.successor
        try:
            url = f"http://{node_info['ip']}:{node_info['port']}/node_id"
            resp = requests.get(url)
            if resp.status_code == 200:
                # We assume the node responds with its successor pointer as well (or we maintain that separately)
                # For simplicity, here we return the stored successor of the current node.
                return self.successor
        except Exception as e:
            print(f"Error getting successor for node {node_info}: {e}")
        return None

    def get_closest_preceding_finger(self, node_info, key_id):
        """
        For a given node_info, query its finger table to find the closest preceding finger.
        Here we assume we have a local copy of our finger table; in a real implementation,
        we might need to query that node.
        """
        # For simplicity, if node_info is self, use our own finger table.
        if node_info["node_id"] == self.node_id:
            for i in range(self.m - 1, -1, -1):
                if self.finger_table[i] is not None:
                    candidate = self.finger_table[i]["successor"]
                    if self.in_interval(candidate["node_id"], self.node_id, key_id, inclusive_right=False):
                        return candidate
        # Fallback to immediate successor.
        return self.successor

    def transfer_keys(self):
        """
        Request our successor to transfer keys for which we are now responsible.
        That is, keys in (self.predecessor, self]
        """
        try:
            url = f"http://{self.successor['ip']}:{self.successor['port']}/transfer_keys?new_node_id={self.node_id}"
            resp = requests.get(url)
            if resp.status_code == 200:
                keys = resp.json().get("keys", {})
                for k, v in keys.items():
                    self.store_data(k, v)
                print(f"Transferred keys: {list(keys.keys())}")
        except Exception as e:
            print(f"Error transferring keys: {e}")

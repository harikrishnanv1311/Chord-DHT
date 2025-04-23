import time
import random
import string
import hashlib
import requests
import matplotlib.pyplot as plt
import numpy as np

M = 10
KEYSPACE_SIZE = 2 ** M

url_base = "http://localhost:5001/"  # Replace with your entry node
headers = {'Content-Type': 'text/plain'}

def generate_random_key(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def hash_key(key):
    """Hash a key to determine its position in the Chord ring."""
    h = hashlib.sha1(key.encode()).hexdigest()
    return int(h, 16) % (2**M)
def sha256_hash(key):
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % KEYSPACE_SIZE

def verify_distribution(N=10000):
    buckets = [0] * KEYSPACE_SIZE
    keys = [generate_random_key() for _ in range(N)]
    
    for key in keys:
        key_hash = sha256_hash(key)
        buckets[key_hash] += 1
    
    mean = np.mean(buckets)
    std_dev = np.std(buckets)
    cv = std_dev / mean if mean > 0 else 0  # Coefficient of variation
    
    print(f"Distribution statistics for {N} keys:")
    print(f"Mean keys per bucket: {mean:.2f}")
    print(f"Standard deviation: {std_dev:.2f}")
    print(f"Coefficient of variation: {cv:.4f} (lower is better, <0.05 is excellent)")
    
    plt.figure(figsize=(12, 6))
    plt.bar(range(KEYSPACE_SIZE), buckets)
    plt.axhline(y=mean, color='r', linestyle='-', label=f'Mean: {mean:.2f}')
    plt.xlabel('Hash Bucket')
    plt.ylabel('Number of Keys')
    plt.title(f'Key Distribution Across {KEYSPACE_SIZE} Buckets')
    plt.legend()
    plt.show()
    
    return keys, buckets

def insert_keys(N=1000):
    keys, _ = verify_distribution(N)
    
    for key in keys:
        key_hash = sha256_hash(key)
        value = f'value_for_{key}'
        
        url = url_base + "store/" + key
        try:
            response = requests.post(url, headers=headers, data=value)
            if response.status_code == 200:
                print(f"Inserted key={key} (hash={key_hash}) successfully.")
            else:
                print(f"Failed to insert key={key} (hash={key_hash}). Response: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Request error for key={key}: {e}")

def generate_deterministic_keys(N=1000, seed=42):
    random.seed(seed)
    keys = [generate_random_key() for _ in range(N)]
    random.seed()  # Reset the seed
    return keys

new_ports1 = list(range(5001, 5011))
new_ports2 = list(range(5011, 5021))
new_ports3 = list(range(5021, 5031))
new_ports4 = list(range(5031, 5041))
new_ports5 = list(range(5041, 5051))
def join_chord_nodes(new_ports, contact_node_host="chord_node_1", contact_node_port=5000):
    contact_address = f"{contact_node_host}:{contact_node_port}"
    
    for port in new_ports:
        try:
            join_url = f"http://localhost:{port}/join"
            time.sleep(3)
            response = requests.post(join_url, data=contact_address, headers={'Content-Type': 'text/plain'})
            if response.status_code == 200:
                print(f"Node at port {port} successfully joined the ring.")
            else:
                print(f"Failed to join node at port {port}. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            print(f"Error joining node at port {port}: {e}")

if __name__ == "__main__":
    # verify_distribution(10000)
    
    insert_keys(1000)
    join_chord_nodes(new_ports1)
    join_chord_nodes(new_ports2)
    join_chord_nodes(new_ports3)
    join_chord_nodes(new_ports4)
    join_chord_nodes(new_ports5)

import requests
import matplotlib.pyplot as plt
import numpy as np

# List of node endpoints (using host port mappings)
nodes = [
    {"name": "node1", "address": "http://localhost:5001/node_id"},
    {"name": "node2", "address": "http://localhost:5002/node_id"},
    {"name": "node3", "address": "http://localhost:5003/node_id"}
]

node_info = []
for n in nodes:
    try:
        r = requests.get(n["address"])
        data = r.json()
        data["name"] = n["name"]
        node_info.append(data)
    except Exception as e:
        print(f"Error fetching {n['name']}: {e}")

# Sort nodes by node_id
node_info.sort(key=lambda x: x["node_id"])

angles = []
labels = []
for n in node_info:
    angle = 2 * np.pi * (n["node_id"] / (2**160))
    angles.append(angle)
    labels.append(f"{n['name']}\nID: {n['node_id']}")

fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
ax.set_xticks(angles)
ax.set_xticklabels(labels, fontsize=8)
ax.plot(angles, [1]*len(angles), 'o')
plt.title("Chord Ring Visualization")
plt.show()

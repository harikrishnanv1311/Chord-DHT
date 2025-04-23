import yaml
import random
import string

NUM_NODES_TOTAL = 50
START_INDEX = 1
M_BITS = 10
DEBUG_BASE_PORT = 5678
HOST_PORT_START = 5001

services = {}

def random_name(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

random.seed(42)  # Optional: for reproducibility

node_names = []
for i in range(START_INDEX, START_INDEX + NUM_NODES_TOTAL):
    rand_suffix = random_name()
    node_name = f"node_{rand_suffix}"
    container_name = f"chord_node_{rand_suffix}"
    port = HOST_PORT_START + i - 1
    debug_port = DEBUG_BASE_PORT + i - 1
    node_names.append(container_name)

    join_target = node_names[0]  # All nodes join the first one

    services[node_name] = {
        "build": {"context": "./chord_node"},
        "container_name": container_name,
        "environment": [
            f"NODE_IP={container_name}",
            "NODE_PORT=5000",
            f"M_BITS={M_BITS}",
            "DEBUG_MODE=True"
        ],
        "ports": [
            f"{port}:5000",
            f"{debug_port}:5678"
        ],
        "networks": {
            "chord_network": {
                "aliases": [container_name]
            }
        },
        "volumes": ["./chord_node:/app"],
        "command": [
            "sh", "-c",
            f"sleep {5 + i} && python3 -u api.py && curl -X POST -d '{join_target}:5000' http://localhost:5000/join"
        ]
    }

compose = {
    "version": "3",
    "services": services,
    "networks": {
        "chord_network": {
            "driver": "bridge"
        }
    }
}

filename = f"docker-compose-{START_INDEX}-{START_INDEX+NUM_NODES_TOTAL-1}.yml"
with open(filename, "w") as f:
    yaml.dump(compose, f, sort_keys=False)

print(f"Docker Compose file written to {filename}")

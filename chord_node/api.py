from flask import Flask, request, jsonify
from node import ChordNode
import hashlib, os, requests, time

app = Flask(__name__)

NODE_IP = os.getenv("NODE_IP", "0.0.0.0")
NODE_PORT = int(os.getenv("NODE_PORT", "5000"))
M_BITS = int(os.getenv("M_BITS", "7"))  # For simulation, using 7 bits.
node = ChordNode(ip=NODE_IP, port=NODE_PORT, m=M_BITS)

@app.route('/node_id', methods=['GET'])
def get_node_id():
    return jsonify({"node_id": node.node_id, "ip": node.ip, "port": node.port})

@app.route('/predecessor', methods=['GET'])
def get_predecessor():
    if node.predecessor:
        return jsonify(node.predecessor)
    return jsonify({"node_id": None}), 404

@app.route('/finger_table', methods=['GET'])
def get_finger_table():
    return jsonify({"finger_table": node.finger_table})

@app.route('/find_successor', methods=['GET'])
def find_successor_endpoint():
    key_id = int(request.args.get("key_id"))
    succ = node.find_successor(key_id)
    if succ:
        return jsonify(succ)
    return jsonify({"error": "Could not find successor"}), 500

@app.route('/update_finger_table', methods=['POST'])
def update_finger_table_endpoint():
    data = request.get_json()
    candidate = data.get("candidate")
    i = int(data.get("i"))
    node.update_finger_table(candidate, i)
    return jsonify({"message": "Finger table updated", "node_id": node.node_id})

@app.route('/transfer_keys', methods=['GET'])
def transfer_keys_endpoint():
    """
    Called by a joining node. The current node (the successor) transfers all keys
    for which the joining node is now responsible. The new node's id is provided as a query parameter.
    """
    new_node_id = int(request.args.get("new_node_id"))
    transferred = {}
    keys_to_delete = []
    # Transfer keys k where k is in (predecessor, new_node_id]
    if node.predecessor is None:
        # if no predecessor, assume transfer all keys that are less than new_node_id.
        for k, v in node.data_store.items():
            key_id = int(hashlib.sha1(k.encode()).hexdigest(), 16) % (2**node.m)
            if key_id <= new_node_id:
                transferred[k] = v
                keys_to_delete.append(k)
    else:
        for k, v in node.data_store.items():
            key_id = int(hashlib.sha1(k.encode()).hexdigest(), 16) % (2**node.m)
            if node.in_interval(key_id, node.predecessor["node_id"], new_node_id, inclusive_right=True):
                transferred[k] = v
                keys_to_delete.append(k)
    # Remove transferred keys from this node.
    for k in keys_to_delete:
        del node.data_store[k]
    return jsonify({"keys": transferred})

@app.route('/store/<key>', methods=['POST'])
def store_key(key):
    value = request.data.decode()
    key_id = int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**node.m)
    dest = node.find_successor(key_id)
    if dest["node_id"] == node.node_id:
        node.store_data(key, value)
        return jsonify({
            "message": f"Stored at node {node.node_id}",
            "final_node": node.node_id,
            "chain": [node.node_id]
        })
    else:
        forward_url = f"http://{dest['ip']}:{dest['port']}/store/{key}"
        print(f"Forwarding store request for key '{key}' to {dest['ip']}")
        resp = requests.post(forward_url, data=value)
        resp_json = resp.json()
        if "chain" in resp_json:
            resp_json["chain"].append(node.node_id)
        else:
            resp_json["chain"] = [node.node_id]
        return jsonify(resp_json)

@app.route('/lookup/<key>', methods=['GET'])
def lookup_key(key):
    key_id = int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**node.m)
    dest = node.find_successor(key_id)
    if dest["node_id"] == node.node_id:
        value = node.get_data(key)
        if value is None:
            return jsonify({"error": "Key not found"}), 404
        return jsonify({
            "key": key,
            "value": value,
            "final_node": node.node_id,
            "chain": [node.node_id]
        })
    else:
        forward_url = f"http://{dest['ip']}:{dest['port']}/lookup/{key}"
        print(f"Forwarding lookup request for key '{key}' to {dest['ip']}")
        resp = requests.get(forward_url)
        resp_json = resp.json()
        if "chain" in resp_json:
            resp_json["chain"].append(node.node_id)
        else:
            resp_json["chain"] = [node.node_id]
        return jsonify(resp_json)

@app.route('/join', methods=['POST'])
def join():
    # Expect the bootstrap node address (e.g., "chord_node_1:5000") in the request body.
    bootstrap = request.data.decode().strip()
    node.init_finger_table(bootstrap)
    return jsonify({
        "message": "Joined network",
        "node_id": node.node_id,
        "finger_table": node.finger_table
    })

if __name__ == "__main__":
    time.sleep(5)  # Allow time for other nodes to start up
    app.run(host="0.0.0.0", port=NODE_PORT)

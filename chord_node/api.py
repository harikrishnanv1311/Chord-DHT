from flask import Flask, request, jsonify
import hashlib
import os
import requests
import time
from node import ChordNode

app = Flask(__name__)

# Get environment variables
NODE_IP = os.getenv("NODE_IP", "0.0.0.0")
NODE_PORT = int(os.getenv("NODE_PORT", "5000"))
M_BITS = int(os.getenv("M_BITS", "7"))  # 7-bit IDs for simulation

# Initialize the Chord node
node = ChordNode(ip=NODE_IP, port=NODE_PORT, m=M_BITS)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "node_id": node.node_id,
        "successor": node.successor["node_id"] if node.successor else None,
        "predecessor": node.predecessor["node_id"] if node.predecessor else None
    })

@app.route('/node_info', methods=['GET'])
def get_node_info():
    return jsonify({
        "node_id": node.node_id,
        "ip": node.ip,
        "port": node.port,
        "successor": node.successor,
        "predecessor": node.predecessor,
        "finger_table": [{"start": entry["start"], 
                        "successor_id": entry["successor"]["node_id"]} 
                       for entry in node.finger_table],
        "data_count": len(node.data_store)
    })

@app.route('/successor', methods=['GET'])
def get_successor():
    return jsonify(node.successor)

@app.route('/predecessor', methods=['GET'])
def get_predecessor():
    if node.predecessor:
        return jsonify(node.predecessor)
    return jsonify(None)

@app.route('/notify', methods=['POST'])
def notify():
    data = request.get_json()
    result = node.notify(data)
    return jsonify({"success": result})

@app.route('/closest_preceding_finger', methods=['GET'])
def closest_preceding_finger():
    key_id = int(request.args.get("key_id"))
    return jsonify(node.closest_preceding_finger(key_id))

@app.route('/find_successor', methods=['GET'])
def find_successor():
    key_id = int(request.args.get("key_id"))
    successor = node.find_successor(key_id)
    return jsonify(successor)

@app.route('/find_predecessor', methods=['GET'])
def find_predecessor():
    key_id = int(request.args.get("key_id"))
    predecessor = node.find_predecessor(key_id)
    return jsonify(predecessor)

@app.route('/update_finger_table', methods=['POST'])
def update_finger_table():
    data = request.get_json()
    i = data.get("i")
    s = data.get("s")
    result = node.update_finger_table(s, i)
    return jsonify({"success": result})

@app.route('/transfer_keys', methods=['POST'])
def transfer_keys():
    data = request.get_json()
    new_pred_id = data.get("node_id")
    keys = node.transfer_keys_to_predecessor(new_pred_id)
    return jsonify({"keys": keys})

@app.route('/store/<key>', methods=['POST'])
def store_key(key):
    value = request.data.decode()
    key_id = node.hash_key(key)
    
    # Find the node responsible for this key
    successor = node.find_successor(key_id)
    
    # If we're responsible, store locally
    if successor["node_id"] == node.node_id:
        node.store_data(key, value)
        return jsonify({
            "status": "success",
            "message": f"Key '{key}' stored at node {node.node_id}",
            "node_id": node.node_id,
            "path": [node.node_id]
        })
    
    # Otherwise, forward to the responsible node
    try:
        url = f"http://{successor['ip']}:{successor['port']}/store/{key}"
        resp = requests.post(url, data=value, timeout=5)
        resp_data = resp.json()
        
        # Add ourselves to the path
        if "path" in resp_data:
            resp_data["path"].append(node.node_id)
        else:
            resp_data["path"] = [node.node_id]
            
        return jsonify(resp_data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to store key: {str(e)}",
            "node_id": node.node_id
        }), 500

@app.route('/lookup/<key>', methods=['GET'])
def lookup_key(key):
    key_id = node.hash_key(key)
    
    # Find the node responsible for this key
    successor = node.find_successor(key_id)
    
    # If we're responsible, look up locally
    if successor["node_id"] == node.node_id:
        value = node.get_data(key)
        if value is None:
            return jsonify({
                "status": "error",
                "message": f"Key '{key}' not found",
                "node_id": node.node_id,
                "path": [node.node_id]
            }), 404
            
        return jsonify({
            "status": "success",
            "key": key,
            "value": value,
            "node_id": node.node_id,
            "path": [node.node_id]
        })
    
    # Otherwise, forward to the responsible node
    try:
        url = f"http://{successor['ip']}:{successor['port']}/lookup/{key}"
        resp = requests.get(url, timeout=5)
        resp_data = resp.json()
        
        # Add ourselves to the path
        if "path" in resp_data:
            resp_data["path"].append(node.node_id)
        else:
            resp_data["path"] = [node.node_id]
            
        return jsonify(resp_data), resp.status_code
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to lookup key: {str(e)}",
            "node_id": node.node_id
        }), 500

@app.route('/join', methods=['POST'])
def join():
    bootstrap_address = request.data.decode().strip()
    if not bootstrap_address:
        # First node in the network
        result = node.join()
    else:
        result = node.join(bootstrap_address)
        
    if result:
        return jsonify({
            "status": "success",
            "message": f"Node {node.node_id} joined the network",
            "node_id": node.node_id,
            "successor": node.successor,
            "predecessor": node.predecessor
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to join network",
            "node_id": node.node_id
        }), 500

@app.route('/finger_table', methods=['GET'])
def get_finger_table():
    return jsonify({
        "node_id": node.node_id,
        "finger_table": node.finger_table
    })

@app.route('/data_store', methods=['GET'])
def get_data_store():
    return jsonify({
        "node_id": node.node_id,
        "data_count": len(node.data_store),
        "data": node.data_store
    })

if __name__ == "__main__":
    # Wait a bit to ensure all containers in network are up
    time.sleep(2)
    app.run(host="0.0.0.0", port=NODE_PORT, debug=False)
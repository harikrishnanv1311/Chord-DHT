import threading
from flask import Flask, request, jsonify
import hashlib
import os
import requests
import time
import debugpy
from node import ChordNode
from flask_cors import CORS
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


app = Flask(__name__)
CORS(app)

DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

if DEBUG_MODE:
    debugpy.listen(("0.0.0.0", 5678))  # Debugger listens on port 5678
    print("⚡ Waiting for debugger to attach...")

NODE_IP = os.getenv("NODE_IP", "0.0.0.0")
NODE_PORT = int(os.getenv("NODE_PORT", "5000"))
M_BITS = int(os.getenv("M_BITS", "10"))  # 7-bit IDs for simulation

#AUTHOR: Apurv Choudhari 
def stabilization_loop(node):
    while True:
        try:
            node.stabilize()
            node.fix_fingers()
        except Exception as e:
            print(f"[Background Thread Error] {e}")
        time.sleep(2)  # run every 5 seconds

#AUTHOR: Kruthik Jonnagaddala Thyagaraja
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "node_id": node.node_id,
        "successor": node.successor["node_id"] if node.successor else None,
        "predecessor": node.predecessor["node_id"] if node.predecessor else None
    })

#AUTHOR: Apurv Choudhari 
@app.route('/node_info', methods=['GET'])
def get_node_info():
    return jsonify({
        "node_id": node.node_id,
        "ip": node.ip,
        "port": node.port,
        "successor": {
            "node_id": node.successor["node_id"] if node.successor else None,
            "ip": node.successor["ip"] if node.successor else None,
            "port": node.successor["port"] if node.successor else None
        } if node.successor else None,
        "predecessor": {
            "node_id": node.predecessor["node_id"] if node.predecessor else None,
            "ip": node.predecessor["ip"] if node.predecessor else None,
            "port": node.predecessor["port"] if node.predecessor else None
        } if node.predecessor else None,
        "finger_table": [
            {   
                "start": entry["start"], 
                "successor_id": entry["successor"]["node_id"]
            } for entry in node.finger_table
        ],
        "data_count": len(node.data_store),
        "m": node.m
    })

#AUTHOR: Harikrishnan Venkatesh
@app.route('/successor', methods=['GET'])
def get_successor():
    return jsonify(node.successor)

#AUTHOR: Harikrishnan Venkatesh
@app.route('/get_predecessor', methods=['GET'])
def get_predecessor():
    if node.predecessor:
        return jsonify(node.predecessor)
    return jsonify(None)
#AUTHOR: Harikrishnan Venkatesh
@app.route('/notify', methods=['POST'])
def notify():
    data = request.get_json()
    result = node.notify(data)
    return jsonify({"success": result})

#AUTHOR: Harikrishnan Venkatesh
@app.route('/closest_preceding_finger', methods=['GET'])
def closest_preceding_finger():
    key_id = int(request.args.get("key_id"))
    return jsonify(node.closest_preceding_finger(key_id))

#AUTHOR: Harikrishnan Venkatesh
@app.route('/find_successor', methods=['GET'])
def find_successor():
    key_id = int(request.args.get("key_id"))
    successor = node.find_successor(key_id)
    return jsonify(successor)

#AUTHOR: Harikrishnan Venkatesh
@app.route('/find_predecessor', methods=['GET'])
def find_predecessor():
    key_id = int(request.args.get("key_id"))
    predecessor = node.find_predecessor(key_id)
    return jsonify(predecessor)

#AUTHOR: Kruthik Jonnagaddala Thyagaraja
@app.route('/set_successor', methods=['POST'])
def set_successor():
    data = request.get_json()
    new_successor = {"node_id": data.get("node_id"), "ip": data.get("ip"), "port": data.get("port")}
    # You might add additional checks to verify that new_successor
    # falls into the correct interval. For minimal change, we simply update.
    node.successor = new_successor
    # print(f"set_successor: Updated successor to {new_successor['node_id']}")
    return jsonify({"message": f"Successor updated to {new_successor['node_id']}"}), 200

#AUTHOR: Kruthik Jonnagaddala Thyagaraja
@app.route('/update_finger_table', methods=['POST'])
def update_finger_table():
    data = request.get_json()
    i = data.get("i")
    s = data.get("s")
    result = node.update_finger_table(s, i)
    return jsonify({"success": result})

#AUTHOR: Kruthik Jonnagaddala Thyagaraja
@app.route('/transfer_keys', methods=['POST'])
def transfer_keys():
    data = request.get_json()
    new_pred_id = data.get("node_id")
    lower_bound = data.get("lower_bound")  # Optional lower bound
    keys = node.transfer_keys_to_predecessor(new_pred_id, lower_bound)
    return jsonify({"keys": keys})

#AUTHOR: Harikrishnan Venkatesh
@app.route('/store/<key>', methods=['POST'])
def store_key(key):
    value = request.data.decode()
    # Use a query parameter "forwarded" with a default value of "0"
    forwarded = request.args.get("forwarded", "0") == "1"
    key_id = node.hash_key(key)
    if forwarded or node.is_responsible(key_id):
        node.store_data(key, value)
        return jsonify({
            "status": "success",
            "message": f"Key '{key}' stored at node {node.node_id}",
            "node_id": node.node_id,
            "path": [node.node_id]
        })
    
    successor = node.find_successor(key_id)
    try:
        url = f"http://{successor['ip']}:{successor['port']}/store/{key}?forwarded=1"
        resp = requests.post(url, data=value, timeout=300)
        resp_data = resp.json()
        
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

#AUTHOR: Harikrishnan Venkatesh
@app.route('/lookup/<key>', methods=['GET'])
def lookup_key(key):
    forwarded = request.args.get("forwarded", "0") == "1"
    key_id = node.hash_key(key)
    
    if forwarded or node.is_responsible(key_id):
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
    
    successor = node.find_successor(key_id)
    try:
        url = f"http://{successor['ip']}:{successor['port']}/lookup/{key}?forwarded=1"
        resp = requests.get(url, timeout=300)
        resp_data = resp.json()
        
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

#AUTHOR: Kruthik Jonnagaddala Thyagaraja
@app.route('/join', methods=['POST'])
def join():
    bootstrap_address = request.data.decode().strip()
    if not bootstrap_address:
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

#AUTHOR: Apurv Choudhari 
@app.route("/depart", methods=["POST"])
def depart_node():
    success = node.depart()
    if success:
        return jsonify({"status": "success", "message": f"Node {node.node_id} departed."}), 200
    else:
        return jsonify({"status": "error", "message": "Node departure failed."}), 500

#AUTHOR: Apurv Choudhari 
@app.route("/update_successor", methods=["POST"])
def update_successor():
    data = request.get_json()
    node.successor = data.get("successor")
    return jsonify({"status": "success"}), 200

#AUTHOR: Apurv Choudhari 
@app.route("/update_predecessor", methods=["POST"])
def update_predecessor():
    data = request.get_json()
    node.predecessor = data.get("predecessor")
    return jsonify({"status": "success"}), 200

#AUTHOR: Apurv Choudhari 
@app.route("/receive_keys", methods=["POST"])
def receive_keys():
    data = request.get_json()
    keys = data.get("data", {})
    node.data_store.update(keys)
    return jsonify({"status": "received"}), 200


#AUTHOR: Kruthik Jonnagaddala Thyagaraja
@app.route('/finger_table', methods=['GET'])
def get_finger_table():
    return jsonify({
        "node_id": node.node_id,
        "finger_table": node.finger_table
    })

#AUTHOR: Harikrishnan Venkatesh
@app.route('/data_store', methods=['GET'])
def get_data_store():
    return jsonify({
        "node_id": node.node_id,
        "data_count": len(node.data_store),
        "data": node.data_store
    })

#AUTHOR: Apurv Choudhari 
def get_node_state():
    """Return the current state of this node for visualization purposes."""
    node_state = {
        "node_id": node.node_id,
        "data_count":len(node.data_store),
        "ip": node.ip,
        "port": node.port,
        "successor": node.successor,
        "predecessor": node.predecessor,
        "finger_table": [
            {
                "start": entry["start"],
                "successor": entry["successor"]
            } for entry in node.finger_table
        ],
        "m": node.m
    }
    return node_state

#AUTHOR: Apurv Choudhari 
@app.route('/network_state', methods=['GET'])
def get_network_state():
    """Return the current state of all known nodes in the network."""
    visited = set([node.node_id])
    nodes = [get_node_state()]
    current = node.successor
    max_nodes = 100
    count = 0
    
    while current["node_id"] != node.node_id and count < max_nodes:
        if current["node_id"] in visited:
            break
            
        try:
            url = f"http://{current['ip']}:{current['port']}/node_info"
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                node_data = resp.json()
                nodes.append(node_data)
                visited.add(current["node_id"])
                current = node_data["successor"]
        except Exception as e:
            print(f"Error fetching node state: {e}")
            
        count += 1
    res = jsonify({"nodes": nodes})
    return res

if __name__ == "__main__":
    node = ChordNode(ip=NODE_IP, port=NODE_PORT, m=M_BITS)
    # node.join(bootstrap_address="0.0.0.0:5000")

    t = threading.Thread(target=stabilization_loop, args=(node,), daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=NODE_PORT, debug=False)

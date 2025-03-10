from flask import Flask, request, jsonify
from node import ChordNode
import hashlib
import os
import requests

app = Flask(__name__)

NODE_IP = os.getenv("NODE_IP", "0.0.0.0")
NODE_PORT = int(os.getenv("NODE_PORT", "5000"))
node = ChordNode(ip=NODE_IP, port=NODE_PORT)

@app.route('/node_id', methods=['GET'])
def get_node_id():
    return jsonify({"node_id": node.node_id, "ip": node.ip, "port": node.port})

def get_successor_info():
    try:
        url = f"http://{node.successor['ip']}:{node.successor['port']}/node_id"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error contacting successor: {e}")
    return None

@app.route('/store/<key>', methods=['POST'])
def store_key(key):
    value = request.data.decode()
    key_id = int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**160)
    
    successor_info = get_successor_info()
    if successor_info is None:
        responsible = True
    else:
        responsible = node.is_responsible(key_id, successor_info["node_id"])
    
    if responsible:
        node.store_data(key, value)
        return jsonify({
            "message": "✅ Stored",
            "final_node": node.node_id,
            "chain": [node.node_id]
        })
    else:
        forward_url = f"http://{node.successor['ip']}:{node.successor['port']}/store/{key}"
        print(f"🔄 Forwarding store request for key {key} to {node.successor['ip']}")
        response = requests.post(forward_url, data=value)
        resp_json = response.json()
        # Append this node's ID to the forwarding chain
        if "chain" in resp_json:
            resp_json["chain"].append(node.node_id)
        else:
            resp_json["chain"] = [node.node_id]
        return jsonify(resp_json)

@app.route('/lookup/<key>', methods=['GET'])
def lookup_key(key):
    key_id = int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**160)
    
    successor_info = get_successor_info()
    if successor_info is None:
        responsible = True
    else:
        responsible = node.is_responsible(key_id, successor_info["node_id"])
    
    if responsible:
        value = node.get_data(key)
        if value == "❌ Key not found":
            return jsonify({"error": value}), 404
        return jsonify({
            "key": key,
            "value": value,
            "final_node": node.node_id,
            "chain": [node.node_id]
        })
    else:
        forward_url = f"http://{node.successor['ip']}:{node.successor['port']}/lookup/{key}"
        print(f"🔄 Forwarding lookup request for key {key} to {node.successor['ip']}")
        response = requests.get(forward_url)
        resp_json = response.json()
        if "chain" in resp_json:
            resp_json["chain"].append(node.node_id)
        else:
            resp_json["chain"] = [node.node_id]
        return jsonify(resp_json)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=NODE_PORT)

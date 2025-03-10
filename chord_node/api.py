from flask import Flask, request, jsonify
from node import ChordNode

app = Flask(__name__)

# Initialize the Chord node
node = ChordNode(ip="0.0.0.0", port=5000)

@app.route('/store/<key>', methods=['POST'])
def store_key(key):
    """Store a key-value pair in the Chord node"""
    value = request.data.decode()
    node.store_data(key, value)
    return jsonify({"message": "✅ Stored", "node_id": node.node_id})

@app.route('/lookup/<key>', methods=['GET'])
def lookup_key(key):
    """Retrieve a value from the Chord node"""
    value = node.get_data(key)
    if value == "❌ Key not found":
        return jsonify({"error": value}), 404
    return jsonify({"key": key, "value": value, "node_id": node.node_id})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

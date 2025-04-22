#!/bin/bash

set -e

echo ""
echo "🚀 Starting automated test for Chord DHT..."
echo ""

# 1. Join nodes (except node5, which will join later to simulate key shuffling)
echo "🔗 Joining nodes to the Chord ring..."
for port in 5001 5002 5003 5004
do
    echo "Joining node at port $port to the ring..."
    curl -s -X POST -H "Content-Type: text/plain" -d "chord_node_1:5000" http://localhost:$port/join
    sleep 1
done

# Wait for the network to stabilize
echo ""
echo "⏳ Waiting for the network to stabilize..."
sleep 5
echo ""

# 2. Add keys to the network via random nodes (we use node2 here)
declare -a keys=("key1" "key2" "key3" "key4" "key5" "key6" "key7" "key8" "key9" "key10")
declare -a values=("val1" "val2" "val3" "val4" "val5" "val6" "val7" "val8" "val9" "val10")

echo "🔐 Storing keys in the network..."
for i in "${!keys[@]}"
do
    echo "Storing ${keys[$i]} -> ${values[$i]}..."
    curl -s -X POST -H "Content-Type: text/plain" \
        --data "${values[$i]}" \
        http://localhost:5002/store/${keys[$i]}
    sleep 3
done

# 3. Lookup all keys via another node (node3)
echo ""
echo "🔍 Looking up keys in the network..."
for key in "${keys[@]}"
do
    echo "Looking up $key..."
    curl -s http://localhost:5003/lookup/$key
    echo ""
    sleep 3
done

# Call /data_store API for each node after lookup
echo ""
echo "📂 Viewing data store contents for all nodes (after lookup)..."
for port in 5001 5002 5003 5004
do
    echo "Node at port $port:"
    curl -s http://localhost:$port/data_store | jq .
    echo ""
    sleep 1
done

# 4. Join node5 to trigger key shuffling
echo ""
echo "🧩 Joining final node (node5) to trigger key shuffling..."
curl -s -X POST -H "Content-Type: text/plain" -d "chord_node_1:5000" http://localhost:5005/join
sleep 3
echo ""

# 5. Check key distribution (final aggregated view)
echo "📊 Checking updated key distribution across nodes (final view)..."
for port in 5001 5002 5003 5004 5005
do
    echo "Node at port $port:"
    curl -s http://localhost:$port/data_store | jq .
    echo ""
    sleep 3
done

echo ""
echo "✅ Test script completed."

# 6. Depart a node that holds a key
echo ""
echo "🚪 Simulating node departure (node holding key)..."

# Let's assume key1 is at port 5002
echo "➡️ Checking initial key location for key1..."
initial_holder=$(curl -s http://localhost:5002/lookup/key1)
echo "Initial holder of key1 is node: $initial_holder"

# Trigger node departure
echo "🔌 Making node1 (port 5001) leave the network..."
curl -s -X POST http://localhost:5001/depart
sleep 3

# Try looking up key1 from a different node (e.g., node3)
echo "🔍 Attempting to lookup key1 from node3 after departure..."
curl -s http://localhost:5003/lookup/key1
sleep 3

# Check data stores across nodes to verify reassignment
echo ""
echo "📁 Verifying key reallocation across nodes..."
for port in 5002 5003 5004 5005
do
    echo "Node at port $port:"
    curl -s http://localhost:$port/data_store
    echo ""
done

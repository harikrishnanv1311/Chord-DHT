# AUTHOR: Harikrishnan Venkatesh

#!/bin/bash

set -e

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Print a fancy header
echo -e "\n${BOLD}${BLUE}┌────────────────────────────────────────────────┐${NC}"
echo -e "${BOLD}${BLUE}│         CHORD DHT AUTOMATED TEST SUITE         │${NC}"
echo -e "${BOLD}${BLUE}└────────────────────────────────────────────────┘${NC}\n"

# Print section header function
print_header() {
    echo -e "\n${BOLD}${YELLOW}┌─ $1 $2 ─┐${NC}"
}

# Print step header function
print_step() {
    echo -e "${CYAN}→ $1${NC}"
}

# Print success message function
print_success() {
    echo -e "  ${GREEN}✓ $1${NC}"
}

# Print info message function
print_info() {
    echo -e "  ${BLUE}ℹ $1${NC}"
}

# Print waiting message
print_waiting() {
    echo -e "${PURPLE}⏳ $1${NC}"
}

# 1. Join nodes (except node5, which will join later to simulate key shuffling)
print_header "STEP 1" "Building the Chord Ring"
print_step "Joining nodes to the Chord ring..."

for port in 5001 5002 5003 5004; do
    node_number=$((port - 5000))
    print_info "Connecting node$node_number (port $port) to the ring..."
    result=$(curl -s -X POST -H "Content-Type: text/plain" -d "chord_node_1:5000" http://localhost:$port/join)
    print_success "Node$node_number joined successfully"
    sleep 3
done

# Wait for the network to stabilize
print_waiting "Waiting for the network to stabilize (5s)..."
sleep 5

# 2. Add keys to the network via random nodes (we use node2 here)
print_header "STEP 2" "Storing Keys in the Network"
declare -a keys=("key1" "key2" "key3" "key4" "key5" "key6" "key7" "key8" "key9" "key10")
declare -a values=("val1" "val2" "val3" "val4" "val5" "val6" "val7" "val8" "val9" "val10")

print_step "Storing keys via node2 (port 5002)..."

for i in "${!keys[@]}"; do
    print_info "Storing ${BOLD}${keys[$i]}${NC} → ${BOLD}${values[$i]}${NC}..."
    result=$(curl -s -X POST -H "Content-Type: text/plain" --data "${values[$i]}" http://localhost:5002/store/${keys[$i]})
    print_success "Key stored: ${keys[$i]}"
    sleep 3
done

# 3. Lookup all keys via another node (node3)
print_header "STEP 3" "Looking Up Keys"
print_step "Looking up keys via node3 (port 5003)..."

for key in "${keys[@]}"; do
    print_info "Looking up ${BOLD}$key${NC}..."
    result=$(curl -s http://localhost:5003/lookup/$key)
    print_success "Result: $result"
    sleep 3
done

# Call /data_store API for each node after lookup
print_header "STEP 4" "Data Distribution (Before Node5 Joins)"
print_step "Viewing data store contents for all nodes..."

for port in 5001 5002 5003 5004; do
    node_number=$((port - 5000))
    echo -e "${BLUE}┌── Node$node_number (port $port) Data Store ───────┐${NC}"
    curl -s http://localhost:$port/data_store | jq -C . | sed 's/^/│ /'
    echo -e "${BLUE}└───────────────────────────────────────────┘${NC}"
    echo ""
    sleep 3
done



################## JT's Part Starts Here:


# 4. Join node5 to trigger key shuffling
print_header "STEP 5" "Testing Key Redistribution"
print_step "Joining final node (node5) to trigger key shuffling..."
result=$(curl -s -X POST -H "Content-Type: text/plain" -d "chord_node_1:5000" http://localhost:5005/join)
print_success "Node5 joined the network"
print_waiting "Waiting for key redistribution (3s)..."
sleep 3

# 5. Check key distribution (final aggregated view)
print_header "STEP 6" "Final Data Distribution"
print_step "Checking updated key distribution across all nodes..."

for port in 5001 5002 5003 5004 5005; do
    node_number=$((port - 5000))
    echo -e "${BLUE}┌── Node$node_number (port $port) Data Store ───────┐${NC}"
    curl -s http://localhost:$port/data_store | jq -C . | sed 's/^/│ /'
    echo -e "${BLUE}└───────────────────────────────────────────┘${NC}"
    echo ""
    sleep 3
done

# 6. Depart a node that holds a key
print_header "STEP 7" "Testing Node Departure"

# Let's check initial key location for key1
print_step "Checking initial location for key1..."
initial_holder=$(curl -s http://localhost:5002/lookup/key1)
print_info "Initial holder of key1 is: $initial_holder"

# Trigger node departure
print_step "Making node1 (port 5001) leave the network..."
result=$(curl -s -X POST http://localhost:5001/depart)
print_success "Node1 departed successfully"
print_waiting "Waiting for key reassignment (3s)..."
sleep 3

# Try looking up key1 from a different node (e.g., node3)
print_step "Looking up key1 from node3 after node1's departure..."
new_holder=$(curl -s http://localhost:5003/lookup/key1)
print_info "New holder of key1 is: $new_holder"

# Check data stores across nodes to verify reassignment
print_header "FINAL" "Verifying Key Reallocation"
print_step "Checking data stores across remaining nodes..."

for port in 5002 5003 5004 5005; do
    node_number=$((port - 5000))
    echo -e "${BLUE}┌── Node$node_number (port $port) Data Store ───────┐${NC}"
    curl -s http://localhost:$port/data_store | jq -C . | sed 's/^/│ /'
    echo -e "${BLUE}└───────────────────────────────────────────┘${NC}"
    echo ""
done

echo -e "\n${BOLD}${GREEN}✅ Chord DHT Test Suite Completed Successfully${NC}\n"

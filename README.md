
# Distributed Hash Table (DHT) using Chord

This project implements a Distributed Hash Table (DHT) based on the [Chord protocol](http://pdos.lcs.mit.edu/chord/). The system uses consistent hashing with finger tables to achieve efficient \(O(\log N)\) key lookups. We expose a RESTful API for key-value operations and simulate node joins using Docker Compose.

---

## Table of Contents

- [Overview](#overview)
- [Design & Architecture](#design--architecture)
  - [Node Structure](#node-structure)
  - [Routing & Storage](#routing--storage)
  - [Environment & Tools](#environment--tools)
- [Setup & Execution](#setup--execution)
- [API Endpoints](#api-endpoints)
- [Running the Automated Demo](#running-the-automated-demo)
- [Results & Demo](#results--demo)
- [Next Steps](#next-steps)

---

## Overview

Chord is a protocol and algorithm for a peer-to-peer distributed hash table. It provides a scalable, fault-tolerant way to store and retrieve data across a distributed system without central coordination.

## Design & Architecture

### Node Structure

Each node runs as a Docker container with its own IP and port. The `ChordNode` class in `node.py` handles:

- Node ID calculation using SHA-1 hash of `ip:port`.
- Maintaining:
  - Successor and Predecessor
  - Finger table with size m = 10
  - Local key-value store
- Core methods: `find_successor`, `closest_preceding_finger`, `join`, `depart`, `stabilize`.

### Routing & Storage

- A key is hashed using SHA-1 to a circular identifier space.
- Lookup proceeds through the finger table using the Chord routing protocol.
- Key-value pairs are stored on the node responsible for the key.
- Nodes communicate via REST API (Flask).

### Environment & Tools

- **Docker Compose**: to simulate 40+ containerized nodes.
- **Python + Flask**: lightweight web API layer.
- **Shell Scripts**: automated test orchestration.
- **Visualization**: use of `/data_store`, `/network_state` etc. for checking correctness.

---

## Setup & Execution

### Prerequisites

- Docker and Docker Compose installed.

### Steps

```bash
git clone <your-repo>
cd chord_dht_project
docker-compose up --build
```

### Monitor Logs

```bash
docker logs -f chord_node_1
```

---

## API Endpoints

Common endpoints available at each node (default `http://localhost:<PORT>`):

- `/join`: Join node to the network
- `/depart`: Leave the network gracefully
- `/store/<key>`: Store a key
- `/lookup/<key>`: Retrieve value for a key
- `/finger_table`: Show node's finger table
- `/data_store`: Show local key-value store
- `/network_state`: Recursively view all nodes in ring
- `/node_info`, `/successor`, `/get_predecessor`: Debug endpoints

---

## Running the Automated Demo

Run the test script `chord_test1.sh` located in the root project directory:

```bash
chmod +x chord_test1.sh
./chord_test1.sh
```

### What It Demonstrates

- Step-by-step node joins (Node 1–5)
- Storing and retrieving 10 keys (`key1` to `key10`)
- Finger table-based lookup
- Key redistribution after Node 5 joins
- Node 1 departure and automatic rebalancing

### Input / Output Specification

| Input               | Output                                  |
|--------------------|------------------------------------------|
| Node join commands | Node IDs, updated successors/predecessors |
| 10 fixed keys      | Lookup paths, successful retrievals       |
| Node departure     | Re-assignment of keys, updated ring       |

Logs are color-coded and structured for clarity.

---

## Results & Demo

- Finger table is periodically updated via `fix_fingers()`.
- Successor/predecessor correctness is verified using `stabilize()`.
- Key lookups confirm \(O(\log N)\) hops per request on average.
- Node departure results in proper key redistribution.

---

## Next Steps

- Load Balancing through Virtual Nodes.
- Node Failure
-- Successor Chaining
-- Key Replication


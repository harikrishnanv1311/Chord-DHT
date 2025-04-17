# Distributed Hash Table (DHT) using Chord

This project implements a Distributed Hash Table (DHT) based on the [Chord protocol](http://pdos.lcs.mit.edu/chord/). The system uses consistent hashing with finger tables to achieve efficient \(O(log N)\) key lookups. We expose a RESTful API for key-value operations and simulate node joins using Docker Compose.

---

## Table of Contents

- [Distributed Hash Table (DHT) using Chord](#distributed-hash-table-dht-using-chord)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Design \& Architecture](#design--architecture)
    - [Node Structure](#node-structure)
    - [Routing \& Storage](#routing--storage)
    - [Environment \& Tools](#environment--tools)
  - [Setup \& Execution](#setup--execution)
    - [Prerequisites](#prerequisites)
    - [Clone and Build](#clone-and-build)
    - [Start the Network](#start-the-network)
    - [Viewing Logs](#viewing-logs)
  - [API Endpoints](#api-endpoints)
  - [Results \& Demo](#results--demo)
  - [Next Steps](#next-steps)

---

## Overview

- **Problem:**  
  Centralized systems suffer from scalability issues and single points of failure. DHTs offer decentralized storage and lookup for efficient data retrieval.

- **Why Chord?**  
  - Uses consistent hashing to distribute keys evenly.  
  - Maintains finger tables to support \(O(log N)\) lookups.  
  - Provides a simple, robust peer-to-peer lookup service.

- **Project Goal:**  
  Build a Chord-based DHT that supports dynamic node joins and key-based PUT/GET operations via a RESTful API, with simulation using Docker Compose.

---

## Design & Architecture

### Node Structure

Each node is implemented as a `ChordNode` (in `node.py`) and runs a Flask API (in `api.py`) inside a Docker container. Every node:
- Has a unique identifier (using SHA-1 of its `IP:port`).
- Maintains:
  - **Successor**
  - **Predecessor**
  - **Finger Table** (an array of entries calculated as:  
    `start = (node_id + 2^i) mod (2^m)` for `i = 0` to `m-1`)
- Stores key-value pairs locally.

### Routing & Storage

- **Key Lookup:**  
  When a client invokes the `/store/<key>` or `/lookup/<key>` endpoint, the node:
  1. Computes the key’s hash.
  2. Uses `find_successor()` (which consults the finger table) to determine the responsible node.
  3. If the node is responsible (or if the request is forwarded internally), it processes the key locally.
  4. Otherwise, it forwards the request (with a hidden `forwarded` parameter set to true).

- **Node Join:**  
  A new node contacts a known **bootstrap node** using the `/join` endpoint. The bootstrap node helps the joining node determine its correct position, initialize its finger table, and update predecessor/successor pointers.

- **Key Transfer:**  
  After joining, a node retrieves keys from its successor that now fall under its responsibility.

### Environment & Tools

- **Docker Compose:**  
  Simulates multiple nodes in a network. One node acts as the bootstrap node, and other nodes join sequentially.
- **Debugging:**  
  Optionally enabled via `debugpy` (see `DEBUG_MODE`).

---

## Setup & Execution

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/)

### Clone and Build

```bash
git clone <your-repo-url>
cd Advanced-Distributed-Systems
docker-compose build
```

### Start the Network

```bash
docker-compose up
```

*Tip:* Use `docker-compose up -d` to run in detached mode.

### Viewing Logs

To monitor a node’s output (including print statements):

```bash
docker logs -f chord_node_1
# or for another node:
docker logs -f chord_node_2
```

---

## API Endpoints

Each node exposes the following endpoints:

1. **Health Check**  
   - **GET** `/health`  
   Returns basic node info (node ID, successor, predecessor).  
   _Example:_
   ```bash
   curl http://localhost:5001/health
   ```

2. **Node Information**  
   - **GET** `/node_info`  
   Detailed info including finger table and data count.  
   _Example:_
   ```bash
   curl http://localhost:5001/node_info
   ```

3. **Successor & Predecessor**  
   - **GET** `/successor`  
   - **GET** `/predecessor`  
   _Example:_
   ```bash
   curl http://localhost:5001/successor
   curl http://localhost:5001/predecessor
   ```

4. **Finger Table Query**  
   - **GET** `/finger_table`  
   Returns the complete finger table.  
   _Example:_
   ```bash
   curl http://localhost:5001/finger_table
   ```

5. **Find Successor/Predecessor**  
   - **GET** `/find_successor?key_id=<integer>`  
   - **GET** `/find_predecessor?key_id=<integer>`  
   _Example:_
   ```bash
   curl "http://localhost:5001/find_successor?key_id=100"
   ```

6. **Store a Key**  
   - **POST** `/store/<key>`  
   Body: raw value data.  
   _Example:_
   ```bash
   curl -X POST http://localhost:5001/store/my-key -d "my-value"
   ```

7. **Lookup a Key**  
   - **GET** `/lookup/<key>`  
   _Example:_
   ```bash
   curl http://localhost:5001/lookup/my-key
   ```

8. **Node Join**
   - **POST** `/join`
    Body: raw hostname:port.
   _Example:_
   ```bash
   curl -X POST 'http://localhost:5004/join' -d "chord_node_1:5000"
   ```

9. **Node Depart**
   - **POST** `/depart`
    Body: None.
   _Example:_
   ```bash
   curl -X POST 'http://localhost:5004/depart'
   ```

10. **Visualization**
    - You can visualize the ring structure and node details by opening `chord_visualization.html` file in your browser.
---

## Results & Demo

- **Current Achievements:**
  - Nodes join the network using a bootstrap node.
  - Keys are stored and looked up using the correct routing based on the finger table.
  - API endpoints are functional (tested with Postman and cURL).
  - Periodic stabilization loop to update successor/predecessor pointers and finger tables automatically.
  - In case of node departure ring structure is intact and keys are redistributed among the nodes.

---

## Next Steps

1. **Performance Analysis:**  
   Measure lookup latency and generate performance graphs to compare with theoretical \(O(log N)\) behavior.



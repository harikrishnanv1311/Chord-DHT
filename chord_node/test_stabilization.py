# import requests
# import time
# import json
# from prettytable import PrettyTable

# # Define the URL for the node API (assuming the server is running locally and using the default port)
# BASE_URL = "http://localhost"
# PORTS = range(5001, 5005)

# def fetch_finger_table(url):
#     try:
#         response = requests.get(f"{url}/finger_table")
#         if response.status_code == 200:
#             finger_table_data = response.json()
#             if "finger_table" in finger_table_data:
#                 finger_table = finger_table_data["finger_table"]
#                 print("Finger Table:")
                
#                 table = PrettyTable()
#                 table.field_names = ["Index", "Start", "Successor"]
                
#                 for index, entry in enumerate(finger_table):
#                     table.add_row([index, entry['start'], entry['successor']])
                
#                 print(table)
#             else:
#                 print("The response does not contain the 'finger_table' key.")
#         else:
#             print(f"Error fetching finger table: {response.status_code}")
#     except Exception as e:
#         print(f"Error fetching finger table: {e}")

# # Function to fetch and display the key-value store
# def fetch_key_value_store(url):
#     try:
#         response = requests.get(f"{url}/data_store")
#         if response.status_code == 200:
#             data_store = response.json()
#             print("\nKey-Value Store:")
            
#             # Create a PrettyTable for the key-value store
#             table = PrettyTable()
#             table.field_names = ["Key", "Value"]
            
#             for key, value in data_store.items():
#                 table.add_row([key, value])
            
#             print(table)
#         else:
#             print(f"Error fetching data store: {response.status_code}")
#     except Exception as e:
#         print(f"Error fetching data store: {e}")

# # Main loop to periodically fetch and display the finger table and key-value store
# def print_periodic_info(interval=10):
#     while True:
#         print("\nFetching Finger Table and Key-Value Store...")
#         for port in PORTS:
#             url = f"{BASE_URL}:{port}"
#             fetch_finger_table(url)
#             fetch_key_value_store(url)
#             print("\n-------------------------------------\n")
#             time.sleep(interval)

# if __name__ == "__main__":
#     print_periodic_info(interval=10)  # Set the interval to 10 seconds


# import requests
# import time

# # Define the range of ports starting from 5001
# PORTS = range(5001, 5005)  # Adjust the range as needed, for example, 5001-5020
# BASE_URL = "http://localhost"  # Update this to match the base URL of your nodes

# # Function to get node state and print the finger table and data store
# def print_node_state_and_data_store():
#     for port in PORTS:
#         url = f"{BASE_URL}:{port}/finger_table"
#         try:
#             resp = requests.get(url)
#             if resp.status_code == 200:
#                 finger_table = resp.json().get('finger_table', [])
#                 print(f"\nNode at port {port} - Finger Table:")
#                 print(f"{'Index':<10}{'Start':<20}{'Successor ID'}")
#                 for index, entry in enumerate(finger_table):
#                     print(f"{index:<10}{entry.get('start', ''):<20}{entry.get('successor', {}).get('node_id', '')}")
#             else:
#                 print(f"Error fetching finger table from node at port {port}")
#         except Exception as e:
#             print(f"Error fetching finger table from node at port {port}: {e}")

#         url = f"{BASE_URL}:{port}/data_store"
#         try:
#             resp = requests.get(url)
#             if resp.status_code == 200:
#                 data_store = resp.json().get('data', {})
#                 print(f"\nNode at port {port} - Data Store:")
#                 if data_store:
#                     print(f"{'Key':<20}{'Value'}")
#                     for key, value in data_store.items():
#                         print(f"{key:<20}{value}")
#                 else:
#                     print("Data store is empty.")
#             else:
#                 print(f"Error fetching data store from node at port {port}")
#         except Exception as e:
#             print(f"Error fetching data store from node at port {port}: {e}")

# # Periodically print node state and data store for all nodes
# while True:
#     print_node_state_and_data_store()
#     time.sleep(10)  # Delay between periodic prints (adjust as needed)


import requests
import time
import json
from prettytable import PrettyTable

# Define the URL for the node API (assuming the server is running locally and using the default port)
BASE_URL = "http://localhost"
PORTS = range(5001, 5005)

def fetch_finger_table(url):
    try:
        response = requests.get(f"{url}/finger_table")
        if response.status_code == 200:
            finger_table_data = response.json()
            node_id = finger_table_data.get("node_id", "Unknown")

            print(f"\nNode at {url} (Node ID: {node_id}) - Finger Table:")

            finger_table = finger_table_data.get("finger_table", [])
            table = PrettyTable()
            table.field_names = ["Index", "Start", "Successor"]

            for index, entry in enumerate(finger_table):
                successor = entry.get('successor')
                if isinstance(successor, dict):
                    successor_id = successor.get('node_id', 'Unknown')
                else:
                    successor_id = successor
                table.add_row([index, entry.get('start'), successor_id])

            print(table)
        else:
            print(f"Error fetching finger table from {url}: {response.status_code}")
    except Exception as e:
        print(f"Error fetching finger table from {url}: {e}")

# Function to fetch and display the key-value store
def fetch_key_value_store(url):
    try:
        response = requests.get(f"{url}/data_store")
        if response.status_code == 200:
            data_store = response.json()
            print(f"\nNode at {url} - Key-Value Store:")

            table = PrettyTable()
            table.field_names = ["Key", "Value"]

            for key, value in data_store.items():
                table.add_row([key, value])

            print(table)
        else:
            print(f"Error fetching data store from {url}: {response.status_code}")
    except Exception as e:
        print(f"Error fetching data store from {url}: {e}")

# Main loop to periodically fetch and display the finger table and key-value store
def print_periodic_info(interval=10):
    while True:
        print("\n====================== START CYCLE ======================")
        for port in PORTS:
            url = f"{BASE_URL}:{port}"
            fetch_finger_table(url)
            fetch_key_value_store(url)
            print("\n------------------------------------------------------\n")
        print("\n====================== END CYCLE ======================")
        time.sleep(interval)

if __name__ == "__main__":
    print_periodic_info(interval=10)  # Set the interval to 10 seconds

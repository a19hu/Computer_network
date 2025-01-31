import socket
import threading
import random
import json

# List of all available Peer Nodes (Simulated for this example)
peers = []

# Seed Node Class
class SeedNode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen(5)

    def handle_peer_connection(self, client_socket, addr):
        print(f"Peer connected from {addr}")
        # Send the list of known peers (for now, we send empty list)
        peer_list = json.dumps(peers)  # Replace this with actual peer information later
        client_socket.send(peer_list.encode())
        # Add this peer to peers list
        client_socket.close()

    def start(self):
        print(f"Seed Node running on {self.ip}:{self.port}")
        while True:
            client_socket, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_peer_connection, args=(client_socket, addr)).start()

# Creating and starting seed nodes from config
seed_nodes = [
    SeedNode('127.0.0.1', 5000),
    SeedNode('127.0.0.1', 5001),
    SeedNode('127.0.0.1', 5002),
    SeedNode('127.0.0.1', 5003),
    SeedNode('127.0.0.1', 5004)
]

for seed in seed_nodes:
    threading.Thread(target=seed.start).start()

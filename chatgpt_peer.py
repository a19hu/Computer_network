import socket
import random
import json
import threading

# Config to read Seed Nodes from the config file
def load_seeds(config_file="config.txt"):
    seeds = []
    with open(config_file, "r") as f:
        lines = f.readlines()
        for i in range(0, len(lines), 2):
            ip = lines[i].split("=")[1].strip()
            port = int(lines[i + 1].split("=")[1].strip())
            seeds.append((ip, port))
    return seeds

# Peer Node Class
class PeerNode:
    def __init__(self, peer_id, config_file="config.txt"):
        self.peer_id = peer_id
        self.config_file = config_file
        self.peers = []  # List of other peers to connect to
        self.connected_peers = []  # Peers this node is connected to
        self.seed_nodes = load_seeds(config_file)
        self.degree = random.randint(1, 10)  # Random degree for power-law distribution (Can be adjusted)

    def connect_to_seed_nodes(self):
        # Connect to ⌊(n/2)⌋ + 1 seeds where n is number of seeds
        required_seeds = len(self.seed_nodes) // 2 + 1
        for _ in range(required_seeds):
            seed = random.choice(self.seed_nodes)
            print(f"Peer {self.peer_id} connecting to Seed Node: {seed}")
            self.connect_to_seed(seed)

    def connect_to_seed(self, seed):
        # Connect to a seed node
        try:
            seed_ip, seed_port = seed
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((seed_ip, seed_port))
            # Receive peer list from seed node
            peer_list = client_socket.recv(1024).decode()
            self.peers = json.loads(peer_list)  # Update with the list of peers from the seed
            print(f"Peer {self.peer_id} connected to Seed {seed_ip}:{seed_port}")
            client_socket.close()
            self.connect_to_other_peers()
        except Exception as e:
            print(f"Error connecting to Seed {seed}: {e}")

    def connect_to_other_peers(self):
        # Connect to other peers with power-law degree distribution
        if len(self.peers) == 0:
            print(f"Peer {self.peer_id} has no peers to connect to yet.")
            return
        num_connections = min(self.degree, len(self.peers))  # Limit number of connections by degree
        print(f"Peer {self.peer_id} will connect to {num_connections} peers.")
        for _ in range(num_connections):
            peer = random.choice(self.peers)
            if peer != self.peer_id:  # Avoid connecting to self
                print(f"Peer {self.peer_id} connecting to Peer {peer}")
                self.connected_peers.append(peer)

    def start(self):
        print(f"Peer {self.peer_id} starting.")
        self.connect_to_seed_nodes()

# Starting the Peer Node
peer = PeerNode(peer_id="peer_1")
peer.start()

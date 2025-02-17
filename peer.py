import socket
import threading
import json
import time
import logging
import random
import math
import sys
import signal

# Configure logging
logging.basicConfig(
    filename="peer.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(peer_ip)s:%(peer_port)s] - %(message)s",
)
CONFIG_FILE = "./config.txt"
OUTPUT_FILE = "outputfile.txt"

class PeerNode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.seed_nodes = self.read_seed_nodes()
        self.registered_seeds = set()
        self.peers = set()
        self.ping_failures = {}
        self.lock = threading.Lock()
        self.running = True
        self.message_count = 0
        self.message_list = set()  # Message List (ML)

# Function to log and write to output.txt and screen
    def log_message(self, message):
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        log_entry = f"{timestamp} [{self.ip}:{self.port}] {message}"
        print(log_entry)
        with open(OUTPUT_FILE, "a") as file:
            file.write(log_entry + "\n")
        logging.info(log_entry, extra={"peer_ip": self.ip, "peer_port": self.port})

# Function to read seed nodes info from config.txt
    def read_seed_nodes(self):
        seed_nodes = []
        try:
            with open(CONFIG_FILE, "r") as file:
                for line in file:
                    line = line.strip()
                    if line:
                        ip, port = line.split(":")
                        seed_nodes.append((ip, int(port)))
        except Exception as e:
            self.log_message(f"Error reading {CONFIG_FILE}: {e}")
        return seed_nodes

# Function to select n/2 + 1 seed nodes
    def select_seed_nodes(self):
        """Select floor(n/2) + 1 random seed nodes."""
        n = len(self.seed_nodes)
        if n == 0:
            return []
        k = math.floor(n / 2) + 1
        return random.sample(self.seed_nodes, k)

# Function to register with selected seed nodes
    def register_with_seed(self):
        selected_nodes = self.select_seed_nodes()
        for seed_ip, seed_port in selected_nodes:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((seed_ip, seed_port))
                sock.send(json.dumps({"type": "register", "ip": self.ip, "port": self.port}).encode())
                response = json.loads(sock.recv(1024).decode())
                if response.get("status") == "success":
                    self.registered_seeds.add((seed_ip, seed_port))
                    self.log_message(f"Registered with seed node {seed_ip}:{seed_port}")
                sock.close()
            except Exception as e:
                self.log_message(f"Failed to register with seed node {seed_ip}:{seed_port}: {e}")

# Function to get peer lists from the connected seed nodes
    def fetch_peers(self):
        selected_nodes = self.select_seed_nodes()
        all_peers = []
        for seed_ip, seed_port in selected_nodes:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((seed_ip, seed_port))
                sock.send(json.dumps({"type": "get_peers"}).encode())
                response = json.loads(sock.recv(4096).decode())
                sock.close()
                all_peers.extend(response.get("peers", []))
            except Exception as e:
                self.log_message(f"Failed to fetch peers from {seed_ip}:{seed_port}: {e}")
        unique_peers = list({(p[0], p[1]) for p in all_peers})
        self.log_message(f"Fetched peer list from seeds: {unique_peers}")
        if unique_peers:
            selected = self.select_peers_power_law(unique_peers)
            self.connect_to_peers(selected)

# Function to select the peers from complete peer list ensuring power law distribution
    def select_peers_power_law(self, peers, alpha=2.0):
        if not peers:
            return []
        
        degrees = [i + 1 for i in range(len(peers))]
        probabilities = [d ** -alpha for d in degrees]
        total = sum(probabilities)
        probabilities = [p / total for p in probabilities]
        
        num_connections = (len(peers)//2) + 1  # Connect to (no. of peers)/2 + 1 peers to ensure connectivity
        selected_indices = random.choices(range(len(peers)), weights=probabilities, k=num_connections)
        return [peers[i] for i in selected_indices]

# Function to connect to a peer
    def connect_to_peers(self, peers):
        for peer_ip, peer_port in peers:
            if (peer_ip, peer_port) != (self.ip, self.port):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((peer_ip, peer_port))
                    sock.send(json.dumps({"type": "peer_info", "ip": self.ip, "port": self.port}).encode())
                    sock.close()
                    with self.lock:
                        self.peers.add((peer_ip, peer_port))
                    self.log_message(f"Connected to peer {peer_ip}:{peer_port}")
                except Exception as e:
                    self.log_message(f"Failed to connect to peer {peer_ip}:{peer_port}: {e}")

# Function to start listening to incoming messages on port
    def start_listener(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.ip, self.port))
        server.listen(5)
        self.log_message(f"Peer node started at {self.ip}:{self.port}")
        
        while self.running:
            try:
                client_socket, addr = server.accept()
                threading.Thread(target=self.handle_peer, args=(client_socket, addr)).start()
            except Exception as e:
                if self.running:
                    self.log_message(f"Listener error: {e}")

# Function to handle communication with peers, processing incoming messages
    def handle_peer(self, client_socket, address):
        try:
            data = json.loads(client_socket.recv(1024).decode())
            if data["type"] == "peer_info":
                sender_ip, sender_port = data["ip"], data["port"]
                with self.lock:
                    self.peers.add((sender_ip, sender_port))
                self.log_message(f"Updated peer list with new peer: {sender_ip}:{sender_port}")
            
            elif data["type"] == "gossip":
                msg_hash = hash(data["message"])
                if msg_hash not in self.message_list:
                    self.message_list.add(msg_hash)
                    self.log_message(f"Received new message from {address}: {data['message']}")
                    self.broadcast_message(data["message"], exclude=address)
            
            elif data["type"] == "ping":  # ✅ Add this to respond to pings
                client_socket.send(json.dumps({"type": "pong"}).encode())
        
        except Exception as e:
            self.log_message(f"Error handling peer {address}: {e}")
        
        finally:
            client_socket.close()

# Function to broadcast a message to connected peers (excluding sender peer in case of forwarded message)
    def broadcast_message(self, message, exclude=None):
        with self.lock:
            peers_copy = list(self.peers)
        for peer_ip, peer_port in peers_copy:
            if exclude and (peer_ip, peer_port) == exclude:
                continue
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((peer_ip, peer_port))
                sock.send(json.dumps({"type": "gossip", "message": message}).encode())
                sock.close()
                self.log_message(f"Sent message to {peer_ip}:{peer_port}: {message}")
            except Exception as e:
                self.log_message(f"Failed to send message to {peer_ip}:{peer_port}: {e}")

# Funtion to send special ping messages (every 3 sec)
    def ping_peers(self):
        while self.running:
            time.sleep(3)
            with self.lock:
                peers_copy = list(self.peers)

            for peer_ip, peer_port in peers_copy:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    sock.connect((peer_ip, peer_port))
                    sock.send(json.dumps({"type": "ping"}).encode())
                    response = json.loads(sock.recv(1024).decode())
                    if response["type"] == "pong":
                        self.ping_failures[(peer_ip, peer_port)] = 0
                    sock.close()
                except Exception as e:
                    self.log_message(f"Ping failed for {peer_ip}:{peer_port}: {e}")
                    self.handle_dead_peer(peer_ip, peer_port)

# Function to handle a peer detected dead
    def handle_dead_peer(self, peer_ip, peer_port):
        with self.lock:
            self.ping_failures[(peer_ip, peer_port)] = self.ping_failures.get((peer_ip, peer_port), 0) + 1
            if self.ping_failures[(peer_ip, peer_port)] >= 3:
                self.log_message(f"Reporting dead peer {peer_ip}:{peer_port}")
                self.report_dead_node(peer_ip, peer_port)
                self.peers.discard((peer_ip, peer_port))
                del self.ping_failures[(peer_ip, peer_port)]

# Function to report dead peer data to user
    def report_dead_node(self, dead_ip, dead_port):

        dead_message = {
            "type": "dead_node",
            "dead_ip": dead_ip,
            "dead_port": dead_port,
            "reporter_ip": self.ip,
            "reporter_port": self.port
        }
        for seed_ip, seed_port in self.registered_seeds:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((seed_ip, seed_port))
                sock.send(json.dumps(dead_message).encode())
                sock.close()
                self.log_message(f"Successfully reported dead node {dead_ip}:{dead_port} to seed {seed_ip}:{seed_port}")
            except Exception as e:
                self.log_message(f"Failed to report dead node {dead_ip}:{dead_port} to {seed_ip}:{seed_port}: {e}")

# Initialization function to start peer node
    def start(self):
        threading.Thread(target=self.start_listener, daemon=True).start()
        self.register_with_seed()
        self.fetch_peers()
        threading.Thread(target=self.ping_peers, daemon=True).start()
        while self.running and self.message_count < 10:
            message = f"{time.time()}:{self.ip}:{self.message_count}"
            self.broadcast_message(message)
            self.message_count += 1
            time.sleep(5)
        while self.running:
            time.sleep(1)

# Main function:
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python peer.py <IP:PORT>")
        sys.exit(1)
    ip, port = sys.argv[1].split(":")
    port = int(port)
    peer = PeerNode(ip, port)
    signal.signal(signal.SIGINT, lambda sig, frame: (peer.shutdown(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda sig, frame: (peer.shutdown(), sys.exit(0)))

    peer.start()


import socket
import threading
import json
import time
import logging
import random
import math

# Configure logging
logging.basicConfig(
    filename="peer.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

CONFIG_FILE = "D:\IITJ\Academics\TY S2\Computer Networks\Assignment1\Computer_network\config.txt"

class PeerNode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.seed_nodes = self.read_seed_nodes()
        self.peers = set()
        self.lock = threading.Lock()
        self.running = True

    def read_seed_nodes(self):
        """Read seed nodes from config.txt and return a list of (IP, Port) tuples."""
        seed_nodes = []
        try:
            with open(CONFIG_FILE, "r") as file:
                for line in file:
                    line = line.strip()
                    if line:
                        ip, port = line.split(":")
                        seed_nodes.append((ip, int(port)))
        except Exception as e:
            logging.error(f"Error reading {CONFIG_FILE}: {e}")
        
        if not seed_nodes:
            logging.error("No seed nodes available in config.txt.")
        
        return seed_nodes

    def select_seed_nodes(self):
        """Select floor(n/2) + 1 random seed nodes."""
        n = len(self.seed_nodes)
        if n == 0:
            return []
        k = math.floor(n / 2) + 1
        return random.sample(self.seed_nodes, k)

    def register_with_seed(self):
        """Register this peer with selected seed nodes."""
        selected_nodes = self.select_seed_nodes()
        for seed_ip, seed_port in selected_nodes:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((seed_ip, seed_port))
                sock.send(json.dumps({"type": "register", "ip": self.ip, "port": self.port}).encode())
                response = json.loads(sock.recv(1024).decode())

                if response.get("status") == "success":
                    logging.info(f"Registered with seed node {seed_ip}:{seed_port}")
                sock.close()
            except Exception as e:
                logging.error(f"Failed to register with seed node {seed_ip}:{seed_port}: {e}")

    def fetch_peers(self):
        """Fetch a list of peers from selected seed nodes."""
        selected_nodes = self.select_seed_nodes()
        for seed_ip, seed_port in selected_nodes:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((seed_ip, seed_port))
                sock.send(json.dumps({"type": "get_peers"}).encode())
                response = json.loads(sock.recv(1024).decode())
                sock.close()

                with self.lock:
                    for peer in response.get("peers", []):
                        if peer != (self.ip, self.port):
                            self.peers.add(tuple(peer))

                logging.info(f"Received peer list from {seed_ip}:{seed_port} - {self.peers}")
            except Exception as e:
                logging.error(f"Failed to fetch peers from {seed_ip}:{seed_port}: {e}")

    def handle_peer(self, client_socket, address):
        """Handle incoming peer connections and messages."""
        try:
            data = json.loads(client_socket.recv(1024).decode())
            if data["type"] == "gossip":
                logging.info(f"Received message from {address}: {data['message']}")
        except Exception as e:
            logging.error(f"Error handling peer {address}: {e}")
        finally:
            client_socket.close()

    def start_listener(self):
        """Start listening for incoming peer messages."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.ip, self.port))
        server.listen(5)
        logging.info(f"Peer node started at {self.ip}:{self.port}")

        while self.running:
            try:
                client_socket, addr = server.accept()
                threading.Thread(target=self.handle_peer, args=(client_socket, addr)).start()
            except Exception as e:
                logging.error(f"Listener error: {e}")

    def broadcast_message(self, message):
        """Broadcast a gossip message to all connected peers."""
        with self.lock:
            peers_copy = list(self.peers)

        for peer_ip, peer_port in peers_copy:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((peer_ip, peer_port))
                sock.send(json.dumps({"type": "gossip", "message": message}).encode())
                sock.close()
                logging.info(f"Sent message to {peer_ip}:{peer_port}: {message}")
            except Exception as e:
                logging.error(f"Failed to send message to {peer_ip}:{peer_port}: {e}")

    def start(self):
        """Start the peer node."""
        threading.Thread(target=self.start_listener, daemon=True).start()
        self.register_with_seed()
        self.fetch_peers()

        while self.running:
            message = f"{time.time()}:{self.ip}:{self.port}"
            logging.info(f"Broadcasting message: {message}")
            self.broadcast_message(message)
            time.sleep(10)

if __name__ == "__main__":
    peer = PeerNode("127.0.0.4", 6004)
    peer.start()

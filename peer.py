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
OUTPUT_FILE = "output.txt"

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
        self.message_log = set()  # Maintain received message hashes to prevent loops

    def log_message(self, message):
        """Logs messages to console, peer.log, and output.txt."""
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        log_entry = f"{timestamp} [{self.ip}:{self.port}] {message}"
        print(log_entry)
        with open(OUTPUT_FILE, "a") as file:
            file.write(log_entry + "\n")
        logging.info(log_entry, extra={"peer_ip": self.ip, "peer_port": self.port})

    def start_listener(self):
        """Start listening for incoming peer messages."""
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
            self.log_message(f"Error reading {CONFIG_FILE}: {e}")
        return seed_nodes

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
                    self.registered_seeds.add((seed_ip, seed_port))
                    self.log_message(f"Registered with seed node {seed_ip}:{seed_port}")
                sock.close()
            except Exception as e:
                self.log_message(f"Failed to register with seed node {seed_ip}:{seed_port}: {e}")

    def select_seed_nodes(self):
        """Select floor(n/2) + 1 random seed nodes."""
        n = len(self.seed_nodes)
        if n == 0:
            return []
        k = math.floor(n / 2) + 1
        return random.sample(self.seed_nodes, k)

    def ping_peers(self):
        """Periodically ping connected peers to check liveness."""
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

    def handle_dead_peer(self, peer_ip, peer_port):
        """Handle dead peer detection and reporting."""
        with self.lock:
            self.ping_failures[(peer_ip, peer_port)] = self.ping_failures.get((peer_ip, peer_port), 0) + 1
            if self.ping_failures[(peer_ip, peer_port)] >= 3:
                self.log_message(f"Reporting dead peer {peer_ip}:{peer_port}")
                self.report_dead_node(peer_ip, peer_port)
                self.peers.discard((peer_ip, peer_port))
                del self.ping_failures[(peer_ip, peer_port)]

    def report_dead_node(self, dead_ip, dead_port):
        """Notify seed nodes about a dead peer."""
        dead_message = {
            "type": "dead_node",
            "dead_ip": dead_ip,
            "dead_port": dead_port,
            "timestamp": time.time(),
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

    def select_peers_power_law(self, peers, alpha=2.0):
        """Select peers using a power-law distribution."""
        if not peers:
            return []

        degrees = [i + 1 for i in range(len(peers))]
        probabilities = [d ** -alpha for d in degrees]
        total = sum(probabilities)
        probabilities = [p / total for p in probabilities]

        num_connections = min(len(peers), 5)  # Connect to up to 5 peers
        selected_indices = random.choices(range(len(peers)), weights=probabilities, k=num_connections)
        return [peers[i] for i in selected_indices]

    def handle_peer(self, client_socket, address):
        """Handle incoming peer connections and messages."""
        try:
            data = json.loads(client_socket.recv(1024).decode())
            if data["type"] == "peer_info":
                sender_ip, sender_port = data["ip"], data["port"]
                with self.lock:
                    self.peers.add((sender_ip, sender_port))
                self.log_message(f"Updated peer list with new peer: {sender_ip}:{sender_port}")

            elif data["type"] == "gossip":
                msg_hash = hash(data["message"])
                if msg_hash not in self.message_log:
                    self.message_log.add(msg_hash)
                    self.log_message(f"Received new message from {address}: {data['message']}")
                    self.broadcast_message(data["message"], exclude=address)

            elif data["type"] == "ping":  #  Add this to respond to pings
                client_socket.send(json.dumps({"type": "pong"}).encode())

        except Exception as e:
            self.log_message(f"Error handling peer {address}: {e}")

        finally:
            client_socket.close()


    def connect_to_peers(self, peers):
        """Establish connections with selected peers and send peer info."""
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

    def broadcast_message(self, message, exclude=None):
        """Broadcast a gossip message to all connected peers except the sender."""
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

    def fetch_peers(self):
        """Fetch peers from seed nodes and log the result."""
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

    def start(self):
        """Main execution loop."""
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

    # def shutdown(self):
    #     """Graceful shutdown procedure."""
    #     self.running = False
    #     self.log_message("Initiating shutdown sequence...")

    #     # Deregister from seeds
    #     for seed_ip, seed_port in self.registered_seeds:
    #         try:
    #             sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #             sock.connect((seed_ip, seed_port))
    #             sock.send(json.dumps({"type": "deregister", "ip": self.ip, "port": self.port}).encode())
    #             sock.close()
    #             self.log_message(f"Deregistered from seed {seed_ip}:{seed_port}")
    #         except Exception as e:
    #             self.log_message(f"Failed to deregister from seed {seed_ip}:{seed_port}: {e}")

    #     # Close all connections
    #     with self.lock:
    #         self.peers.clear()


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


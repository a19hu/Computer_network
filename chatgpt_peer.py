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
    format="%(asctime)s - %(levelname)s - %(message)s",
)

CONFIG_FILE = "./config.txt"

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
        self.messages_sent = set()

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
                    self.registered_seeds.add((seed_ip, seed_port))
                    logging.info(f"Registered with seed node {seed_ip}:{seed_port}")
                sock.close()
            except Exception as e:
                logging.error(f"Failed to register with seed node {seed_ip}:{seed_port}: {e}")

    def fetch_peers(self):
        """Fetch and connect to peers following power-law distribution."""
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
                logging.error(f"Failed to fetch peers from {seed_ip}:{seed_port}: {e}")

        # Power-law peer selection
        unique_peers = list({(p[0], p[1]) for p in all_peers})
        if unique_peers:
            selected = self.select_peers_power_law(unique_peers)
            self.connect_to_peers(selected)

    def select_peers_power_law(self, peers):
        """Select peers using preferential attachment simulation."""
        weights = [i+1 for i in range(len(peers))]  # Simulate power-law weights
        total_weight = sum(weights)
        selected = []
        for _ in range(min(len(peers), 5)):  # Connect to up to 5 peers
            r = random.uniform(0, total_weight)
            upto = 0
            for i, w in enumerate(weights):
                if upto + w >= r:
                    selected.append(peers[i])
                    total_weight -= w
                    weights.pop(i)
                    peers.pop(i)
                    break
                upto += w
        return selected

    def connect_to_peers(self, peers):
        """Establish connections with selected peers."""
        for peer_ip, peer_port in peers:
            if (peer_ip, peer_port) != (self.ip, self.port):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((peer_ip, peer_port))
                    sock.close()
                    with self.lock:
                        self.peers.add((peer_ip, peer_port))
                    logging.info(f"Connected to peer {peer_ip}:{peer_port}")
                except Exception as e:
                    logging.error(f"Failed to connect to peer {peer_ip}:{peer_port}: {e}")

    def handle_peer(self, client_socket, address):
        """Handle incoming peer connections and messages."""
        try:
            data = json.loads(client_socket.recv(1024).decode())
            if data["type"] == "gossip":
                msg_hash = hash(data["message"])
                if msg_hash not in self.messages_sent:
                    self.messages_sent.add(msg_hash)
                    logging.info(f"Received new message from {address}: {data['message']}")
                    self.broadcast_message(data["message"], exclude=address)
            elif data["type"] == "ping":
                client_socket.send(json.dumps({"type": "pong"}).encode())
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
                if self.running:
                    logging.error(f"Listener error: {e}")

    def broadcast_message(self, message, exclude=None):
        """Broadcast a gossip message to all connected peers."""
        with self.lock:
            peers_copy = list(self.peers)
            print(peers_copy)

        for peer_ip, peer_port in peers_copy:
            if exclude and (peer_ip, peer_port) == exclude:
                continue
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((peer_ip, peer_port))
                sock.send(json.dumps({"type": "gossip", "message": message}).encode())
                sock.close()
                logging.info(f"Sent message to {peer_ip}:{peer_port}: {message}")
            except Exception as e:
                logging.error(f"Failed to send message to {peer_ip}:{peer_port}: {e}")
                self.handle_dead_peer(peer_ip, peer_port)

    def ping_peers(self):
        """Periodically ping connected peers to check liveness."""
        while self.running:
            time.sleep(13)
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
                    logging.warning(f"Ping failed for {peer_ip}:{peer_port}: {e}")
                    self.handle_dead_peer(peer_ip, peer_port)

    def handle_dead_peer(self, peer_ip, peer_port):
        """Handle dead peer detection and reporting."""
        with self.lock:
            self.ping_failures[(peer_ip, peer_port)] = self.ping_failures.get((peer_ip, peer_port), 0) + 1
            if self.ping_failures[(peer_ip, peer_port)] >= 3:
                logging.info(f"Reporting dead peer {peer_ip}:{peer_port}")
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
            except Exception as e:
                logging.error(f"Failed to report dead node to {seed_ip}:{seed_port}: {e}")

    def shutdown(self):
        """Graceful shutdown procedure."""
        self.running = False
        logging.info("Initiating shutdown sequence...")

        # Deregister from seeds
        for seed_ip, seed_port in self.registered_seeds:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((seed_ip, seed_port))
                sock.send(json.dumps({"type": "deregister", "ip": self.ip, "port": self.port}).encode())
                sock.close()
                logging.info(f"Deregistered from seed {seed_ip}:{seed_port}")
            except Exception as e:
                logging.error(f"Failed to deregister from seed {seed_ip}:{seed_port}: {e}")

        # Close all connections
        with self.lock:
            self.peers.clear()

        logging.info("Peer shutdown complete")

    def start(self):
        """Main execution loop."""
        threading.Thread(target=self.start_listener, daemon=True).start()
        self.register_with_seed()
        self.fetch_peers()
        threading.Thread(target=self.ping_peers, daemon=True).start()

        # Generate messages
        while self.running and self.message_count < 10:
            message = f"{time.time()}:{self.ip}:{self.message_count}"
            self.broadcast_message(message)
            self.message_count += 1
            time.sleep(5)

        # Keep running for pings and message handling
        while self.running:
            time.sleep(1)

def signal_handler(sig, frame):
    print("\nGraceful shutdown initiated...")
    peer.shutdown()
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python peer.py <IP:PORT>")
        sys.exit(1)

    ip, port = sys.argv[1].split(":")
    port = int(port)

    peer = PeerNode(ip, port)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        peer.start()
    except Exception as e:
        peer.shutdown()
        raise e
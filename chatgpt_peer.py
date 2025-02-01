import socket
import threading
import json
import time
import random
import hashlib

class PeerNode:
    def __init__(self, ip, port, seeds):
        self.ip = ip
        self.port = port
        self.seeds = seeds  # List of (ip, port) tuples
        self.connected_peers = []  # List of (ip, port) tuples
        self.message_list = {}  # {hash: [sent_to_peers]}
        self.lock = threading.Lock()

    def register_with_seeds(self):
        for seed_ip, seed_port in self.seeds:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((seed_ip, seed_port))
                request = json.dumps({"type": "register", "ip": self.ip, "port": self.port})
                sock.send(request.encode())
                response = json.loads(sock.recv(1024).decode())
                if response["status"] == "success":
                    print(f"Registered with seed: {seed_ip}:{seed_port}")
                sock.close()
            except Exception as e:
                print(f"Failed to register with seed {seed_ip}:{seed_port}: {e}")

    def get_peers_from_seeds(self):
        all_peers = set()
        for seed_ip, seed_port in self.seeds:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((seed_ip, seed_port))
                request = json.dumps({"type": "get_peers"})
                sock.send(request.encode())
                response = json.loads(sock.recv(1024).decode())
                all_peers.update(tuple(peer) for peer in response["peers"])
                sock.close()
            except Exception as e:
                print(f"Failed to get peers from seed {seed_ip}:{seed_port}: {e}")
        return list(all_peers)

    def connect_to_peers(self, peers):
        for peer_ip, peer_port in peers:
            if (peer_ip, peer_port) != (self.ip, self.port):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((peer_ip, peer_port))
                    self.connected_peers.append((peer_ip, peer_port))
                    print(f"Connected to peer: {peer_ip}:{peer_port}")
                except Exception as e:
                    print(f"Failed to connect to peer {peer_ip}:{peer_port}: {e}")

    def start(self):
        self.register_with_seeds()
        peers = self.get_peers_from_seeds()
        self.connect_to_peers(peers)

        threading.Thread(target=self.gossip_messages).start()
        threading.Thread(target=self.check_liveness).start()

    def gossip_messages(self):
        message_count = 0
        while message_count < 10:
            time.sleep(5)
            message = f"{time.time()}:{self.ip}:{message_count}"
            self.broadcast_message(message)
            message_count += 1

    def broadcast_message(self, message):
        message_hash = hashlib.sha256(message.encode()).hexdigest()
        with self.lock:
            if message_hash not in self.message_list:
                self.message_list[message_hash] = []
            for peer_ip, peer_port in self.connected_peers:
                if (peer_ip, peer_port) not in self.message_list[message_hash]:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect((peer_ip, peer_port))
                        sock.send(message.encode())
                        self.message_list[message_hash].append((peer_ip, peer_port))
                        sock.close()
                    except Exception as e:
                        print(f"Failed to send message to {peer_ip}:{peer_port}: {e}")

    def check_liveness(self):
        while True:
            time.sleep(13)
            dead_peers = []
            for peer_ip, peer_port in self.connected_peers:
                try:
                    # Use system ping utility
                    response = os.system(f"ping -c 1 {peer_ip}")
                    if response != 0:
                        dead_peers.append((peer_ip, peer_port))
                except Exception as e:
                    print(f"Failed to ping {peer_ip}:{e}")

            for dead_ip, dead_port in dead_peers:
                self.report_dead_node(dead_ip, dead_port)
                self.connected_peers.remove((dead_ip, dead_port))

    def report_dead_node(self, dead_ip, dead_port):
        for seed_ip, seed_port in self.seeds:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((seed_ip, seed_port))
                request = json.dumps({"type": "dead_node", "dead_ip": dead_ip, "dead_port": dead_port})
                sock.send(request.encode())
                sock.close()
            except Exception as e:
                print(f"Failed to report dead node to seed {seed_ip}:{seed_port}: {e}")

if __name__ == "__main__":
    seeds = [("127.0.0.1", 5001), ("127.0.0.1", 5002), ("127.0.0.1", 5003)]
    peer = PeerNode("127.0.0.1", 6001, seeds)
    peer.start()
import socket
import threading
import json
import time

LOG_FILE = "seed.log"

class SeedNode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.peer_list = []  # List of (ip, port) tuples
        self.lock = threading.Lock()

    def log_message(self, message):
        """Logs messages to both console and a log file."""
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        log_entry = f"{timestamp} {message}"
        print(log_entry)
        with open(LOG_FILE, "a") as log_file:
            log_file.write(log_entry + "\n")

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.ip, self.port))
        server_socket.listen(5)
        self.log_message(f"Seed node started at {self.ip}:{self.port}")

        while True:
            client_socket, addr = server_socket.accept()
            self.log_message(f"Connection from {addr[0]}:{addr[1]}")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        try:
            data = client_socket.recv(1024).decode()
            if not data:
                self.log_message("Received empty request, ignoring.")
                client_socket.close()
                return

            request = json.loads(data)
            self.log_message(f"Received request: {request}")

            if request["type"] == "register":
                peer_ip = request["ip"]
                peer_port = request["port"]
                with self.lock:
                    self.peer_list.append((peer_ip, peer_port))
                self.log_message(f"Registered peer: {peer_ip}:{peer_port}")
                client_socket.send(json.dumps({"status": "success"}).encode())

            elif request["type"] == "get_peers":
                with self.lock:
                    peer_data = json.dumps({"peers": self.peer_list})
                self.log_message(f"Sending peer list to client: {peer_data}")
                client_socket.send(peer_data.encode())

            elif request["type"] == "dead_node":
                dead_ip = request["dead_ip"]
                dead_port = request["dead_port"]
                with self.lock:
                    self.peer_list = [(ip, port) for ip, port in self.peer_list if ip != dead_ip or port != dead_port]
                self.log_message(f"Removed dead node: {dead_ip}:{dead_port}")

        except Exception as e:
            self.log_message(f"Error handling client: {e}")

        # finally:
        #     client_socket.close()
        #     self.log_message("Closed connection with client.")

if __name__ == "__main__":
    seed_nodes = [
        SeedNode('127.0.0.1', 5000),
        SeedNode('127.0.0.1', 5001),
        SeedNode('127.0.0.1', 5002),
        SeedNode('127.0.0.1', 5003),
        SeedNode('127.0.0.1', 5004)
    ]
    
    for seed in seed_nodes:
        seed_thread = threading.Thread(target=seed.start)
        seed_thread.start()

import socket
import threading
import json
import time
import sys

class SeedNode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.peer_list = []
        self.lock = threading.Lock()
        self.output_file = "output.txt"

# Function to log and write to output.txt and screen
    def log_message(self, message):
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        log_entry = f"{timestamp} {message}"
        print(log_entry)
        with open('seed.log', "a") as log_file:
            log_file.write(log_entry + "\n")
        with open(self.output_file, "a") as out_file:
            out_file.write(log_entry + "\n")

# Initialization function to start a seed node
    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.ip, self.port))
        server_socket.listen(5)
        self.log_message(f"Seed node started at {self.ip}:{self.port}")

        while True:
            client_socket, addr = server_socket.accept()
            self.log_message(f"Connection from {addr[0]}:{addr[1]}")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

# Function to listen to incoming messages and process them correctly
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

# Main function:
if __name__ == "__main__":
    ip, port = sys.argv[1].split(':')
    port = int(port)

    with open('config.txt', 'r+') as file:
        lines = file.readlines()
        config = ip + ':' + str(port) + '\n'
        if config not in lines:
            file.seek(0, 2)
            file.write(config)

    SeedNode(ip, port).start()
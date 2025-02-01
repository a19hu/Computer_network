import socket
import threading
import json

class SeedNode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.peer_list = []  # List of (ip, port) tuples
        self.lock = threading.Lock()

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.ip, self.port))
        server_socket.listen(5)
        print(f"Seed node started at {self.ip}:{self.port}")

        while True:
            client_socket, addr = server_socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        data = client_socket.recv(1024).decode()
        request = json.loads(data)

        if request["type"] == "register":
            peer_ip = request["ip"]
            peer_port = request["port"]
            with self.lock:
                self.peer_list.append((peer_ip, peer_port))
            print(f"Registered peer: {peer_ip}:{peer_port}")
            client_socket.send(json.dumps({"status": "success"}).encode())

        elif request["type"] == "get_peers":
            with self.lock:
                client_socket.send(json.dumps({"peers": self.peer_list}).encode())

        elif request["type"] == "dead_node":
            dead_ip = request["dead_ip"]
            dead_port = request["dead_port"]
            with self.lock:
                self.peer_list = [(ip, port) for ip, port in self.peer_list if ip != dead_ip or port != dead_port]
            print(f"Removed dead node: {dead_ip}:{dead_port}")

        client_socket.close()

if __name__ == "__main__":
    seed_nodes = [
        SeedNode('127.0.0.1', 5000),
        SeedNode('127.0.0.1', 5001),
        SeedNode('127.0.0.1', 5002),
        SeedNode('127.0.0.1', 5003),
        SeedNode('127.0.0.1', 5004)
    ]
    for seed in seed_nodes:
        seed_threading=threading.Thread(target=seed.start)
        seed_threading.start()
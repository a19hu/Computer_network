import threading
import socket

class SeedNode:
    def __init__(self,ip,port):
        self.ip=ip
        self.port=port
        self.server_socket = socket.socket()
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen(5)


    # def registration(self):

    # def dead_peer(self):


    # def peer_list(self):


    def start(self):
        print(f"Seed Node running on {self.ip}:{self.port}")
        while True:
            connection, addr = self.server_socket.accept()
            print(addr)
            print(connection)


# https://realpython.com/intro-to-python-threading/

def main():
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

if __name__ == "__main__":
    main()
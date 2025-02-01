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

    def handle_peer_connection(self,conne,addr):
        print(f"peer connected from {addr}")
        connection, address = server_socket.accept()
        # print("[INFO] Connection established with:", address)

        # print("[INFO] Receiving message from client...")
        # received_message = connection.recv(buffer_size).decode('utf-8')
        # print("Message received from client:", received_message)

        # uppercase_message = received_message.upper().encode('utf-8')
        # reverse_message = received_message[::-1].encode('utf-8')

        # print("[INFO] Sending responses to client...")
        # connection.send(uppercase_message)
        conne.send("hii")
        conne.close()


    def start(self):
        print(f"Seed Node running on {self.ip}:{self.port}")
        while True:
            conne, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_peer_connection,args=(conne,addr)).start()


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
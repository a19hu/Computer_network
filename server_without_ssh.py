import socket

server_socket = socket.socket()
server_port = 1672
server_ip = '0.0.0.0'
buffer_size = 1024

print("[INFO] Starting the server...")
server_socket.bind((server_ip, server_port))
print("[INFO] Server started successfully on port:", server_port)

print("[INFO] Waiting for a connection...")
server_socket.listen(5)
connection, address = server_socket.accept()
print("[INFO] Connection established with:", address)

print("[INFO] Receiving message from client...")
received_message = connection.recv(buffer_size).decode('utf-8')
print("Message received from client:", received_message)

uppercase_message = received_message.upper().encode('utf-8')
reverse_message = received_message[::-1].encode('utf-8')

print("[INFO] Sending responses to client...")
connection.send(uppercase_message)
connection.send(reverse_message)
print("[INFO] Responses sent successfully.")

print("[INFO] Closing client connection...")
connection.close()
print("[INFO] Client connection closed.")

print("[INFO] Shutting down the server...")
server_socket.close()
print("[INFO] Server shut down successfully.")


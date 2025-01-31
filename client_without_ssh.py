import socket

client_socket = socket.socket()
server_port = 5002
server_ip = '127.0.0.1'
buffer_size = 1024

print("[INFO] Connecting to the server...")
client_socket.connect((server_ip, server_port))
print("[INFO] Connected to server:", server_ip, "on port:", server_port)

message = input("Enter a message to send to the server: ")
print("[INFO] Sending message to server...")
client_socket.send(message.encode('utf-8'))
print("[INFO] Message sent successfully.")

print("[INFO] Waiting for response from server...")
uppercase_response = client_socket.recv(buffer_size).decode('utf-8')
reverse_response = client_socket.recv(buffer_size).decode('utf-8')

print("Response in Uppercase:", uppercase_response)
print("Response in Reverse:", reverse_response)

print("[INFO] Closing connection to the server...")
client_socket.close()
print("[INFO] Connection closed successfully.")

print("[INFO] Testing connection to Google...")
test_socket = socket.socket()
google_ip = socket.gethostbyname('www.google.com')
google_port = 80
test_socket.connect((google_ip, google_port))
print("[INFO] Successfully connected to Google at", google_ip)
test_socket.close()
print("[INFO] Connection to Google closed.")


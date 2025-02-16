# Gossip Protocol Over a Peer-to-Peer Network





# Setup and Compilation
### Clone the Repository
To get started, clone the repository and navigate to the project directory:
```bash
git clone https://github.com/a19hu/Computer_network
cd Computer_network/
```
## Running Seed and Peer Locally
To run the network locally, start the seed node first. The seed node's IP and port will be automatically added to ```config.txt```.
### 1. Start the Seed Node
Run the following command, replacing ```<port>``` with the desired port number:
```bash
python3 seed.py 127.0.0.1:<port>
```
### 2. Start Peer Nodes
Run peers on different ports as follows:
```bash
python3 peer.py 127.0.0.1:<port>
```
Example: Use ports such as ```5001, 5002, 5003,``` etc., ensuring each peer runs on a different port.


## Running Seed and Peer on Different Servers
To deploy across multiple servers, run the seed node on a remote machine with its own IP and port. This information must be added to config.txt.
### 1. Start the Seed Node
Run the following command on the server, replacing <IP> and <port> with the actual server IP and port:
```bash
python3 seed.py <IP>:<port>
```
Example: python3 seed.py 10.6.0.63:5002

### 2. Configure IP Address and Port

Update the config.txt file by adding the seed node's IP and port in the format:
```bash
10.6.0.63:5000
```
### 3. Start Peer Nodes
Run the peers, ensuring they connect to the correct seed node:
```bash
python3 peer.py <IP>:<port>
```
Example:
```bash
python3 peer.py 172.6.0.63:6000
python3 peer.py 172.6.0.63:6001

python3 peer.py 10.6.0.63:5000
python3 peer.py 10.6.0.63:5003
```

##### Ensure that each peer connects to a valid seed node and runs on a unique port for proper communication.
---
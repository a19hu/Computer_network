# Gossip Protocol Over a Peer-to-Peer Network

### CSL3080:Computer Networks Assignment-1 by Ashutosh Kumar (B22CS015) and Krishna Patil (B22CS078)

# Implementation Details

The implemented P2P network consists of two types of nodes: **Seed Nodes** and **Peer Nodes**.

## Seed Node Functionalities
1. Maintain a list of connected peers (**Peer List <PL>**).
2. Connect to peers and send them the peer list.
3. Receive dead node reports from peers and remove dead nodes from the peer list.

## Peer Node Functionalities
1. Read the `config.txt` file to get information about seed nodes.
2. Connect to `n/2 + 1` of the available seed nodes and request their peer lists.
3. Take the union of all peer lists received from seeds and connect to random peers, ensuring a **power law distribution**.
4. Inform connected nodes by sending them its own IP address and port.
5. Every **5 seconds**, broadcast a message in the given format to all connected peers. A total of **10 messages** will be broadcast.
6. Forward any received message to all connected peers, except the sender.
7. Maintain a **Message List (ML)** to prevent forwarding messages multiple times.
8. Periodically (**every 3 seconds**), ping all connected peers to check if they are active.
9. If **three consecutive pings** go unanswered, the connected peer is reported as dead to all connected seed nodes.

## Notes
- **Power Law Distribution** is simulated using a weighted random distribution of probabilities for selecting a particular peer node.
- **Network Connectivity**: A new peer connects to `1` existing peers to ensure connectivity just as it joins the network. (Further connections might be made my newer peers according to power law distribution)
- **Ping Mechanism**: Implemented as a special type of message instead of using the standard ping function, since multiple nodes run on the same machine.
- **Message Format**: Messages generated by peers are represented as a simple counter `(0,1,2...9)`, to maintain simplicity and track the number of messages generated.
- **power_law_simulation.py** file gives a simulation code which plots the distribution of peers vs their no. of connections in the network. It shows that the implementation correctly approximates a power law distribution in the P2P topology.



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

###### Also checkout <a href="https://github.com/a19hu/Computer_network">Repo</a>.
---
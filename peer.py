import socket
import threading
import sys
import json
from peer_heartbeat import PeerHeartbeat

class Peer:
    def __init__(self, settings):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_address = settings["tracker-address"]
        self.tracker_port = settings["tracker-port"]
        self.port = settings["port"]
        print ("Socket created")

    def register_as_peer(self):
        server_address = (self.tracker_address, self.tracker_port)
        self.listening_socket.connect(server_address)
        try:
            message = {}
            message["msg_type"] = "JOIN"
            message["port"] = self.port
            message["files"] = ["test.txt"]
            self.listening_socket.sendall(json.dumps(message))
            data = self.listening_socket.recv(1024)
            received_data = json.loads(data)
            self.peer_id = received_data["peer_id"]
            self.neighboring_peers = received_data["neighboring_peers"]
        except:
            print("Unable to register as peer")
            exit()
        finally:
            print("Registered as peer")
            self.listening_socket.close()

    def heartbeat_func(self):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self.tracker_address, self.tracker_port)
        self.listening_socket.connect(server_address)
        self.listening_socket.sendall("{ \"msg_type\": \"HEARTBEAT\", \"port\": 2345, \"files\": [\"test.txt\", \"test1.txt\"]}")

    def start_peer(self):
        self.register_as_peer()
        # self.heartbeat = PeerHeartbeat(5, self.heartbeat_func)

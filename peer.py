import socket
import threading
import sys
import json
import os

from peer_heartbeat import PeerHeartbeat

class Peer:
    def __init__(self, settings):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_address = settings["tracker-address"]
        self.tracker_port = settings["tracker-port"]
        self.port = settings["port"]
        self.directory = settings["peer-directory"]
        print ("Socket created")

    def get_directory_files(self):
        # Returns a list of files in self.directory
        files = []
        for pack in os.walk(self.directory):
            for filename in pack[2]:
                full_path = os.path.join(self.directory, filename)
                if os.path.isfile(full_path):
                    files.append(filename)
        return files

    def register_as_peer(self):
        server_address = (self.tracker_address, self.tracker_port)
        self.listening_socket.connect(server_address)
        try:
            message = {}
            message["msg_type"] = "JOIN"
            message["port"] = self.port
            message["files"] = self.get_directory_files()
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
        try:
            message = {}
            message["msg_type"] = "HEARTBEAT"
            message["peer_id"] = self.peer_id
            self.listening_socket.sendall(json.dumps(message))
            print("Sent heartbeat message")
        except:
            print("Unable to send heartbeat message")
        finally:
            self.listening_socket.close()

    def start_peer(self):
        self.register_as_peer()
        self.heartbeat = PeerHeartbeat(5, self.heartbeat_func)

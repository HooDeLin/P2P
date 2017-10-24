import socket
import sys

class Peer:
    def __init__(self, settings):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_address = settings["tracker-address"]
        self.tracker_port = settings["tracker-port"]
        print ("Socket created")

    def start_peer(self):
        server_address = (self.tracker_address, self.tracker_port)
        self.listening_socket.connect(server_address)

        try:
            self.listening_socket.sendall("{ \"msg_type\": \"JOIN\", \"port\": 2345, \"files\": [\"test.txt\", \"test1.txt\"]}")
            data = self.listening_socket.recv(1024)
            print(data)
        finally:
            self.listening_socket.close()

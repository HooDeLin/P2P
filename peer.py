import socket
import sys

def start_peer(settings):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print ("Socket created")
    server_address = (settings["tracker-address"], settings["tracker-port"])
    s.connect(server_address)

    try:
        s.sendall("{ \"msg_type\": \"JOIN\", \"port\": 2345, \"files\": [\"test.txt\", \"test1.txt\"]}")
        data = s.recv(1024)
        print(data)
    finally:
        s.close()

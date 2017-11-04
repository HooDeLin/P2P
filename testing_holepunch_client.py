import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
msg = "This is a test message"
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("0.0.0.0", 12345))
s.sendto(msg, (host, port))
s.close()

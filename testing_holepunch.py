import socket
import stun
import sys
nat_type, external_ip, external_port = stun.get_ip_info(source_port=12345)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print("Nat Type: " + nat_type)
print("External IP: " + external_ip)
print("External Port: " + str(external_port))

s.bind(("0.0.0.0", 12345))
msg = "This is a test message"
s.sendto(msg, ("128.199.72.2", 12345))
s.sendto(msg, ("74.125.68.101", 12345))
while 1:
    data, addr = s.recvfrom(1024)
    print data

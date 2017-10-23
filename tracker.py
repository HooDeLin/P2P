import socket
import sys

def start_tracker(settings):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print ("Socket created")
    try:
        s.bind(("", settings["port"]))
    except socket.error as msg:
        print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()
    print 'Socket bind complete'
    s.listen(10)
    print 'Socket now listening'
    while 1:
        conn, addr = s.accept()
        print 'Connected with ' + addr[0] + ':' + str(addr[1])
    s.close()

import socket
import json
import sys
import random
import hashlib

def create_join_entry(msg, peer_table, addr):
    print(addr[0] + ":" + str(msg["port"]))
    peer_key = hashlib.md5(addr[0] + ":" + str(msg["port"])).hexdigest()
    peer_table[peer_key] = {"address": addr[0], "port": msg["port"]}
    return peer_key

def create_file_entries(peer_key, msg, file_table):
    for filename in msg["files"]:
        file_key = hashlib.md5(filename).hexdigest()
        if file_key in file_table.keys() and peer_key not in file_table[file_key]:
            file_table[file_key].append(peer_key)
        else:
            file_table[file_key] = [peer_key]

def create_join_reply_message(peer_key, peer_table):
    msg = {}
    msg["msg_type"] = "JOIN_REPLY"
    msg["peer_id"] = peer_key
    msg["neighboring_peers"] = []
    for key, value in peer_table.iteritems():
        if key != peer_key:
            msg["neighboring_peers"].append(value)
    return json.dumps(msg)


def parse_message(data, peer_table, file_table, addr):
    print(data)
    msg = json.loads(data)
    if "msg_type" not in msg:
        return
    if msg["msg_type"] == "JOIN":
        peer_key = create_join_entry(msg, peer_table, addr)
        create_file_entries(peer_key, msg, file_table)
        return create_join_reply_message(peer_key, peer_table)

def start_tracker(settings):
    peer_table = {};
    file_table = {};
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
        # try:
        data = conn.recv(1024)
        print 'Received data'
        print data
        if data:
            return_data = parse_message(data, peer_table, file_table, addr)
            conn.sendall(return_data)
        print peer_table
        print file_table
        conn.close()
        # except:
        #     break
        # print 'Connected with ' + addr[0] + ':' + str(addr[1])
    s.close()

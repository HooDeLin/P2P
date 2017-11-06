import socket
import json
import sys
import random
import hashlib
from threading import Thread
from sets import Set
from runner import Runner
from threading import Lock

class Tracker(Runner):

    def __init__(self, settings):
        self.peer_set = Set()
        self.file_details = {}
        self.file_owners = {}
        self.chunk_owners = {}
        self.lock = Lock()
        self.port = settings["port"]
        self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.signal_port = settings["signal-port"]
        self.signal_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print ("Socket created")
        try:
            self.peer_socket.bind(("", settings["port"]))
            self.signal_socket.bind(("", settings["signal-port"]))
        except socket.error as msg:
            print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
            sys.exit()
        print 'Socket bind complete'
        self.peer_socket.listen(10)
        print 'Socket now listening'

    def create_not_yet_implemented_reply(self):
        msg = {}
        msg["message_type"] = "NOT_YET_IMPLEMENTED"
        return json.dumps(msg)

    def create_ack_reply(self):
        msg = {}
        msg["message_type"] = "ACK"
        return json.dumps(msg)

    def create_list_of_files_reply(self):
        msg = {}
        msg["message_type"] = "QUERY_LIST_OF_FILES_REPLY"
        msg["files"] = list(set(self.chunk_owners.keys() + self.file_details.keys()))
        return json.dumps(msg)

    def handle_inform_and_update_message(self, msg, addr):
        peer_id = ""
        if "source_ip" in msg:
            peer_id = msg["source_ip"] + ":" + str(msg["source_port"])
        else:
            peer_id = addr[0] + ":" + str(msg["source_port"])
        self.peer_set.add(peer_id)
        for peer_files in msg["files"]:
            file_name = peer_files["filename"]
            # Add files into file details if this is the first time appearing
            if file_name not in self.file_details:
                file_checksum = peer_files["filechecksum"]
                num_of_chunks = peer_files["num_of_chunks"]
                self.file_details[file_name] = {}
                self.file_details[file_name]["filechecksum"] = file_checksum
                self.file_details[file_name]["num_of_chunks"] = num_of_chunks
            # Add the owner to file owners
            if file_name not in self.file_owners:
                self.file_owners[file_name] = [peer_id]
            elif peer_id not in self.file_owners[file_name]:
                self.file_owners[file_name].append(peer_id)

        for peer_file_chunks in msg["chunks"]:
            file_name = peer_file_chunks["filename"]
            if file_name not in self.chunk_owners:
                self.chunk_owners[file_name] = {peer_id: peer_file_chunks["chunks"]}
            elif peer_id not in self.chunk_owners[file_name]:
                self.chunk_owners[file_name][peer_id] = peer_file_chunks["chunks"]
            else:
                updated_file_chunk_owns = list(set(self.chunk_owners[file_name][peer_id] + peer_file_chunks["chunks"]))
                self.chunk_owners[file_name][peer_id] = updated_file_chunk_owns
        return

    def create_file_reply(self, file_name):
        if file_name not in self.file_details:
            msg = {"message_type": "QUERY_FILE_ERROR", "error": "File does not exists"}
            return json.dumps(msg)
        checksum = self.file_details[file_name]["filechecksum"]
        num_of_chunks = self.file_details[file_name]["num_of_chunks"]
        owners = self.file_owners[file_name]
        chunks = {}
        if file_name in self.chunk_owners:
            peer_id_with_chunks = self.chunk_owners[file_name]
            for peer_id in peer_id_with_chunks.keys():
                peer_chunks = peer_id_with_chunks[peer_id]
                for chunk_num in peer_chunks:
                    if str(chunk_num) in chunks:
                        chunks[str(chunk_num)].append(peer_id)
                    else:
                        chunks[str(chunk_num)] = [peer_id]
        for owner in owners:
            for i in range(num_of_chunks):
                if str(i) in chunks:
                    chunks[str(i)].append(owner)
                else:
                    chunks[str(i)] = [owner]
        msg = {"message_type": "QUERY_FILE_REPLY",
               "filename": file_name,
               "checksum": checksum,
               "chunks": chunks,
               "num_of_chunks": num_of_chunks,
        }
        return json.dumps(msg)

    def handle_exit_message(self, msg):
        peer_id = msg["source_ip"] + ":" + str(msg["source_port"])
        self.peer_set.discard(peer_id)
        file_that_has_peer_as_solo_owners = []
        file_owner_that_needs_to_be_removed = []
        for file_name in self.file_owners:
            if len(self.file_owners[file_name]) == 1 and self.file_owners[file_name][0] == peer_id:
                file_that_has_peer_as_solo_owners.append(file_name)
                file_owner_that_needs_to_be_removed.append(file_name)
            elif peer_id in self.file_owners[file_name]:
                file_owner_that_needs_to_be_removed.append(file_name)
        for file_name in file_owner_that_needs_to_be_removed:
            self.file_owners.pop(file_name)
        for file_name in file_that_has_peer_as_solo_owners:
            if file_name in self.file_details:
                self.file_details.pop(file_name)
        return

    def send_signal(self, msg):
        signal_msg = {}
        dst_addr = msg["owner_address"].split(":")
        signal_msg["message_type"] = "REQUEST_FILE_CHUNK_SIGNAL"
        signal_msg["receiver_address"] = msg["self_address"]
        signal_msg["filename"] = msg["filename"]
        signal_msg["chunk_number"] = msg["chunk_number"]
        self.signal_socket.sendto(json.dumps(signal_msg), (dst_addr[0], int(dst_addr[1])))

    def parse_msg(self, data, addr):
        msg = json.loads(data)
        if "message_type" not in msg:
            print("Not yet implemented")
            return self.create_not_yet_implemented_reply()
        if msg["message_type"] == "INFORM_AND_UPDATE":
            self.lock.acquire()
            self.handle_inform_and_update_message(msg, addr)
            self.lock.release()
            return self.create_ack_reply()
        elif msg["message_type"] == "QUERY_LIST_OF_FILES":
            return self.create_list_of_files_reply()
        elif msg["message_type"] == "QUERY_FILE":
            return self.create_file_reply(msg["filename"])
        elif msg["message_type"] == "REQUEST_FILE_CHUNK_NAT":
            self.send_signal(msg)
            return self.create_ack_reply()
        elif msg["message_type"] == "EXIT":
            self.lock.acquire()
            self.handle_exit_message(msg)
            self.lock.release()
            return self.create_ack_reply()

    def handle_connection(self, conn, addr):
        data = conn.recv(1048576) # recv 1MB
        print 'Received data: ' + data
        if data:
            return_data = self.parse_msg(data, addr)
            print 'Returning data: ' + return_data
            conn.sendall(return_data)
        conn.close()

    def start_tracker(self):
        while 1:
            conn, addr = self.peer_socket.accept()
            t = Thread(target=self.handle_connection, args=(conn, addr))
            t.start()
        self.peer_socket.close()

    def stop(self):
        print("Stopping tracker")
        self.peer_socket.close()

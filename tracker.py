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
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print ("Socket created")
        try:
            self.listening_socket.bind(("", settings["port"]))
        except socket.error as msg:
            print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
            sys.exit()
        print 'Socket bind complete'
        self.listening_socket.listen(10)
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
        checksum = self.file_details[file_name]["filechecksum"]
        num_of_chunks = self.file_details[file_name]["num_of_chunks"]
        owners = self.file_owners[file_name]
        chunks = {}
        if file_name in self.chunk_owners:
            chunks = self.chunk_owners[file_name]
        msg = {"message_type": "QUERY_FILE_REPLY",
               "filename": file_name,
               "checksum": checksum,
               "owners": owners,
               "chunks": chunks,
               "num_of_chunks": num_of_chunks,
        }
        return json.dumps(msg)

    def handle_exit_message(self, msg, addr):
        peer_id = addr[0] + ":" + str(msg["source_port"])
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
        elif msg["message_type"] == "EXIT":
            self.lock.acquire()
            self.handle_exit_message(msg, addr)
            self.lock.release()
            return self.create_ack_reply()

    def handle_connection(self, conn, addr):
        data = conn.recv(1024)
        print 'Received data: ' + data
        if data:
            return_data = self.parse_msg(data, addr)
            print 'Returning data: ' + return_data
            conn.sendall(return_data)
        conn.close()

    def start_tracker(self):
        while 1:
            conn, addr = self.listening_socket.accept()
            t = Thread(target=self.handle_connection, args=(conn, addr))
            t.start()
        self.listening_socket.close()

    def stop(self):
        print("Stopping tracker")
        self.listening_socket.close()

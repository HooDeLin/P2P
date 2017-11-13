import socket
import json
import sys
import random
import hashlib
import logger
from threading import Thread
from sets import Set
from runner import Runner
from threading import Lock
from constants import *

class Tracker(Runner):

    def __init__(self, settings):
        self.public_peer_set = Set()
        self.public_peer_signal = {}
        self.peer_set = Set()
        self.file_details = {}
        self.file_owners = {}
        self.chunk_owners = {}
        self.lock = Lock()
        self.port = settings[SETTINGS_PORT_KEY]
        self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.signal_port = settings[SETTINGS_SIGNAL_PORT_KEY]
        self.signal_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logger.print_socket_created_message()
        try:
            self.peer_socket.bind(("", self.port))
            self.signal_socket.bind(("", self.signal_port))
        except socket.error as msg:
            logger.print_socket_error_message(msg)
            sys.exit()
        logger.print_socket_bind_message()
        self.peer_socket.listen(1000)

    def create_not_yet_implemented_reply(self):
        # Format: {"message_type": "NOT_YET_IMPLEMENTED"}
        msg = {}
        msg[MESSAGE_TYPE_KEY] = NOT_YET_IMPLEMENTED_MESSAGE_TYPE
        return json.dumps(msg)

    def create_ack_reply(self):
        # Format: {"message_type": "ACK"}
        msg = {}
        msg[MESSAGE_TYPE_KEY] = ACK_MESSAGE_TYPE
        return json.dumps(msg)

    def create_list_of_files_reply(self):
        # Format: {"message_type": "QUERY_LIST_OF_FILES_REPLY", "files": ["file1", "file2", ...]}
        msg = {}
        msg[MESSAGE_TYPE_KEY] = QUERY_LIST_OF_FILES_REPLY_MESSAGE_TYPE
        msg[MSG_FILES_KEY] = list(set(self.chunk_owners.keys() + self.file_details.keys()))
        return json.dumps(msg)

    def get_peer_id_from_message(self, msg, addr):
        if MSG_SOURCE_IP_KEY in msg:
            return msg[MSG_SOURCE_IP_KEY] + IP_PORT_DELIMITER + str(msg[MSG_SOURCE_PORT_KEY])
        else:
            return addr[0] + IP_PORT_DELIMITER + str(addr[1])

    def handle_inform_and_update_message(self, msg, addr):
        peer_id = self.get_peer_id_from_message(msg, addr)
        if MSG_SIGNAL_PORT_KEY in msg: # If you send a signal port, you are behind NAT
            self.public_peer_set.add(peer_id)
            self.public_peer_signal[peer_id] = msg[MSG_SIGNAL_PORT_KEY]
        self.peer_set.add(peer_id)
        for peer_files in msg[MSG_FILES_KEY]:
            file_name = peer_files[MSG_FILENAME_KEY]
            # Add files into file details if this is the first time appearing
            if file_name not in self.file_details:
                file_checksum = peer_files[MSG_CHECKSUM_KEY]
                num_of_chunks = peer_files[MSG_NUM_OF_CHUNKS_KEY]
                self.file_details[file_name] = {}
                self.file_details[file_name][MSG_CHECKSUM_KEY] = file_checksum
                self.file_details[file_name][MSG_NUM_OF_CHUNKS_KEY] = num_of_chunks
            # Add the owner to file owners
            if file_name not in self.file_owners:
                self.file_owners[file_name] = [peer_id]
            elif peer_id not in self.file_owners[file_name]:
                self.file_owners[file_name].append(peer_id)

        for peer_file_chunks in msg[MSG_CHUNKS_KEY]:
            file_name = peer_file_chunks[MSG_FILENAME_KEY]
            if file_name not in self.chunk_owners:
                self.chunk_owners[file_name] = {peer_id: peer_file_chunks[MSG_CHUNKS_KEY]}
            elif peer_id not in self.chunk_owners[file_name]:
                self.chunk_owners[file_name][peer_id] = peer_file_chunks[MSG_CHUNKS_KEY]
            else:
                updated_file_chunk_owns = list(set(self.chunk_owners[file_name][peer_id] + peer_file_chunks[MSG_CHUNKS_KEY]))
                self.chunk_owners[file_name][peer_id] = updated_file_chunk_owns
        return

    def create_file_reply(self, file_name):
        if file_name not in self.file_details:
            msg = {MESSAGE_TYPE_KEY: QUERY_FILE_ERROR_MESSAGE_TYPE, "error": "File does not exists"}
            return json.dumps(msg)
        checksum = self.file_details[file_name][MSG_CHECKSUM_KEY]
        num_of_chunks = self.file_details[file_name][MSG_NUM_OF_CHUNKS_KEY]
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
        msg = {MESSAGE_TYPE_KEY: QUERY_FILE_REPLY_MESSAGE_TYPE,
               MSG_FILENAME_KEY: file_name,
               MSG_CHECKSUM_KEY: checksum,
               MSG_CHUNKS_KEY: chunks,
               MSG_NUM_OF_CHUNKS_KEY: num_of_chunks,
               MSG_PEER_BEHIND_NAT_KEY: list(self.public_peer_set)
        }
        return json.dumps(msg)

    def handle_exit_message(self, msg, addr):
        peer_id = self.get_peer_id_from_message(msg, addr)
        if peer_id in self.public_peer_signal:
            self.public_peer_signal.pop(peer_id)
        self.public_peer_set.discard(peer_id)
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

    def send_signal(self, msg, addr):
        signal_msg = {}
        dst_addr = msg[MSG_OWNER_ADDRESS_KEY].split(IP_PORT_DELIMITER)
        signal_msg[MESSAGE_TYPE_KEY] = REQUEST_FILE_CHUNK_SIGNAL_MESSAGE_TYPE
        if MSG_RECEIVER_ADDRESS_KEY in msg:
            signal_msg[MSG_RECEIVER_ADDRESS_KEY] = msg[MSG_RECEIVER_ADDRESS_KEY]
        else:
            signal_msg[MSG_RECEIVER_ADDRESS_KEY] = addr[0] + IP_PORT_DELIMITER + str(addr[1])
        signal_msg[MSG_FILENAME_KEY] = msg[MSG_FILENAME_KEY]
        signal_msg[MSG_FILE_DOWNLOAD_PROCESS_ID_KEY] = msg[MSG_FILE_DOWNLOAD_PROCESS_ID_KEY]
        signal_msg[MSG_CHUNK_NUMBER_KEY] = msg[MSG_CHUNK_NUMBER_KEY]
        logger.print_returning_data(signal_msg)
        self.signal_socket.sendto(json.dumps(signal_msg), (dst_addr[0], int(self.public_peer_signal[msg[MSG_OWNER_ADDRESS_KEY]])))

    def parse_msg(self, data, addr):
        msg = json.loads(data)
        if MESSAGE_TYPE_KEY not in msg:
            logger.print_not_yet_implemented_message()
            return self.create_not_yet_implemented_reply()
        if msg[MESSAGE_TYPE_KEY] == INFORM_AND_UPDATE_MESSAGE_TYPE:
            self.lock.acquire()
            self.handle_inform_and_update_message(msg, addr)
            self.lock.release()
            return self.create_ack_reply()
        elif msg[MESSAGE_TYPE_KEY] == QUERY_LIST_OF_FILES_MESSAGE_TYPE:
            return self.create_list_of_files_reply()
        elif msg[MESSAGE_TYPE_KEY] == QUERY_FILE_MESSAGE_TYPE:
            return self.create_file_reply(msg[MSG_FILENAME_KEY])
        elif msg[MESSAGE_TYPE_KEY] == REQUEST_FILE_CHUNK_NAT_MESSAGE_TYPE:
            self.send_signal(msg, addr)
            return self.create_ack_reply()
        elif msg[MESSAGE_TYPE_KEY] == EXIT_MESSAGE_TYPE:
            self.lock.acquire()
            self.handle_exit_message(msg)
            self.lock.release()
            return self.create_ack_reply()

    def handle_connection(self, conn, addr):
        data = conn.recv(1024)
        logger.print_received_data(data)
        if data:
            return_data = self.parse_msg(data, addr)
            logger.print_returning_data(return_data)
            conn.sendall(return_data)
        conn.close()

    def start_tracker(self):
        while 1:
            conn, addr = self.peer_socket.accept()
            t = Thread(target=self.handle_connection, args=(conn, addr))
            t.start()
        self.peer_socket.close()

    def stop(self):
        logger.print_tracker_stopping_message()
        self.peer_socket.close()
        self.signal_socket.close()

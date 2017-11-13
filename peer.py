from __future__ import print_function
import socket
import threading
# import multiprocessing
import sys
import json
import os, glob
import hashlib
import stun
import file_utils
import logger

from constants import *
from runner import Runner
from random import randint

class Peer(Runner):
    def __init__(self, settings):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.signal_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tracker_address = settings[SETTINGS_TRACKER_ADDRESS_KEY]
        self.tracker_port = settings[SETTINGS_TRACKER_PORT_KEY]
        self.port = settings[SETTINGS_PORT_KEY]
        self.directory = settings[SETTINGS_PEER_DIRECTORY_KEY]
        self.hole_punch = SETTINGS_HOLE_PUNCHING_KEY in settings
        self.tracker_signal_port = settings[SETTINGS_TRACKER_SIGNAL_PORT_KEY]
        self.signal_port = settings[SETTINGS_SIGNAL_PORT_KEY]
        self.external_ip = None
        self.external_port = None
        self.external_signal_port = None
        self.chunk_size = 1014 #byte
        self.socket_listening_thread = None
        self.signal_listening_thread = None
        # List of (formatted) files that the Peer is sharing
        self.files = []
        # List of (formatted) incomplete files that the Peer is sharing
        self.chunks = []
        self.file_download_process_info = []
        self.connect = None
        self.known_peers_behind_nat = []

    def get_directory_files(self):
        # Returns a list of filenames in self.directory
        # Note: filenames do not contain the full path!
        files = []
        for pack in os.walk(self.directory):
            for filename in pack[2]:
                # Need the full path to check properly
                full_path = os.path.join(self.directory, filename)
                if os.path.isfile(full_path):
                    files.append(filename)
        return files

    def format_complete_file(self, filename):
        # Change "filename" to
        # {"checksum": "checksum", "num_of_chunks": 1, "filename": "test_c"}
        ret = {}
        full_path = os.path.join(self.directory, filename)
        # Warning: Memory inefficient! Refer to
        # https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
        file_checksum = hashlib.md5(open(full_path, 'rb').read()).hexdigest()
        file_size = os.stat(full_path).st_size  # in bytes
        leftover_bytes = file_size % self.chunk_size
        if leftover_bytes == 0:
            num_chunks = file_size / self.chunk_size
        else:
            num_chunks = file_size / self.chunk_size + 1
        ret[MSG_CHECKSUM_KEY] = file_checksum
        ret[MSG_NUM_OF_CHUNKS_KEY] = num_chunks
        ret[MSG_FILENAME_KEY] = filename
        return ret

    def format_chunks(self, chunks):
        # Change "chunk"
        # {"chunks": [1, 2, 3, 4, 5], "filename": "test_b"}
        # Returns: [{"chunks": [list of chunks owned], "filename": filename}, ... ]
        mapping = {}
        # chunk naming convention: <filename>.<chunk_num>.chunk
        for chunk in chunks:
            split = chunk.split(".")
            chunk_num = split[-2]
            filename = ".".join(split[:-2])
            if filename in mapping:
                mapping[filename].append(chunk_num)
            else:
                mapping[filename] = [chunk_num]
        ret = []
        for filename, chunks in mapping.items():
            ret.append({MSG_FILENAME_KEY: filename, MSG_CHUNKS_KEY: chunks})
        return ret

    def process_dir_listing(self):
        # Process the files in self.directory, and sets the result in
        # self.files and self.chunks
        all_filenames = self.get_directory_files()
        files = [i for i in all_filenames if i[-6:] != CHUNK_EXTENSION]
        chunks = [i for i in all_filenames if i[-6:] == CHUNK_EXTENSION]
        self.files = [self.format_complete_file(i) for i in files]
        self.chunks = self.format_chunks(chunks)

    def create_info_for_tracker(self):
        # Informs tracker of files in directory, checksum of each file, owned
        # chunks of each file, source port of Peer
        # {
        #     "source_port": port_num,
        #     "files": [{"checksum": "checksum", "num_of_chunks": 1, "filename": "test_c"}, ...],
        #     "chunks": [{"chunks": [1, 2, 3, 4, 5], "filename": "test_b"}, ...]
        #     "message_type": "INFORM_AND_UPDATE",
        # }
        info = {}
        if self.hole_punch:
            info[MSG_SOURCE_IP_KEY] = self.external_ip
            info[MSG_SOURCE_PORT_KEY] = self.external_port
            info[MSG_SIGNAL_PORT_KEY] = self.external_signal_port
        else:
            info[MSG_SOURCE_PORT_KEY] = self.port
        info[MSG_FILES_KEY] = self.files
        info[MSG_CHUNKS_KEY] = self.chunks
        info[MESSAGE_TYPE_KEY] = INFORM_AND_UPDATE_MESSAGE_TYPE
        return info

    def send_message_to_tracker(self, message, success_msg="", failure_msg="",
                                should_exit=False):
        # Helper function whenever Peer needs to send a message to Tracker
        server_address = (self.tracker_address, self.tracker_port)
        sending_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sending_socket.connect(server_address)
        try:
            sending_socket.sendall(json.dumps(message))

            # increamentally receiving the JSON data from the tracker
            data = ''
            while True:
                new_bytes = sending_socket.recv(1024)
                if not new_bytes:
                    break
                data += new_bytes

            received_data = json.loads(data)
            if success_msg:
                print(success_msg)
            sending_socket.close()
            return received_data
        except:
            sending_socket.close()
            if failure_msg:
                print(failure_msg)
            if should_exit:
                exit()

    def register_as_peer(self):
        # Informs the Tracker of the files and chunks that you are sharing
        # Does this by opening a socket to the Tracker and sending the data
        self.process_dir_listing()
        message = self.create_info_for_tracker()
        self.send_message_to_tracker(
            message=message,
            success_msg=REGISTER_PEER_SUCCESS_MESSAGE,
            failure_msg=REGISTER_PEER_FAILED_MESSAGE,
            should_exit=True
        )

    def get_available_files(self):
        """
        Asks the Tracker for a list of all files in this network
        """
        message = { MESSAGE_TYPE_KEY: QUERY_LIST_OF_FILES_MESSAGE_TYPE }
        reply = self.send_message_to_tracker(message)
        # Format the replies and display to user
        filenames = sorted(reply[MSG_FILES_KEY])
        logger.print_available_files(filenames)

    # def get_peers_with_file(self, filename): # TODO: Remove this? Tracker doesn't reply who has the file
    #     """
    #     Asks the Tracker for a list of peers containing a file with this filename
    #     """
    #     message = {}
    #     message[MESSAGE_TYPE_KEY] = QUERY_FILE_MESSAGE_TYPE
    #     message[MSG_FILENAME_KEY] = filename
    #     reply = self.send_message_to_tracker(message)
    #     # Handle "file not found"
    #     if reply[MESSAGE_TYPE_KEY] == QUERY_FILE_ERROR_MESSAGE_TYPE:
    #         print(reply["error"])
    #         return
    #     # Format the replies and display to user
    #     logger.print_users_that_has_file(reply["owners"])
    #     reply.pop("owners", None)  # remove the "owner" key
    #     reply.pop(MESSAGE_TYPE_KEY, None)  # remove the "message_type" key
    #     print("")
    #     print("File information: ")
    #     for k, v in reply.items():
    #         print("{}: {}".format(k, v))

    def signal_listening(self):
        logger.print_setup_signal_message(self.tracker_address, self.tracker_signal_port)
        self.signal_socket.sendto(json.dumps({MESSAGE_TYPE_KEY: ACK_MESSAGE_TYPE}), (self.tracker_address, int(self.tracker_signal_port)))
        while True:
            data_received, _ = self.signal_socket.recvfrom(1024)
            # try:
            message = json.loads(data_received)
            if message[MESSAGE_TYPE_KEY] == REQUEST_FILE_CHUNK_SIGNAL_MESSAGE_TYPE:
                logger.print_receive_signal_message()
                filename = message[MSG_FILENAME_KEY]
                chunk_number = message[MSG_CHUNK_NUMBER_KEY]
                requester_addr = message[MSG_RECEIVER_ADDRESS_KEY].split(IP_PORT_DELIMITER)
                requester_addr[1] = int(requester_addr[1])
                file_id = message[MSG_FILE_DOWNLOAD_PROCESS_ID_KEY]
                self.send_a_file_chunk_to_a_peer(filename, file_id, chunk_number, requester_addr)
            # except:
            #     print("There is an error listening to tracker signal")

    def hole_punch_to_peer(self, owner_address):
        # Called when self is behind NAT
        # Sends a blank JSON to allow peer to connect to self.external_port
        # Essentially creates a mapping in the NAT-enabled router
        message = {MESSAGE_TYPE_KEY: ACK_MESSAGE_TYPE}
        self.listening_socket.sendto(json.dumps(message), owner_address)

    def listen_func(self):
        while True:
            # receive the request info fileInfo{ "fileName": "", "chunkFileName": "", "chunkNumber": int  }
            ## data_from_requester = self.connect.recv(1024) [TCP]
            data_received, requester_addr = self.listening_socket.recvfrom(1024) #[UDP]
            try:
                message = json.loads(data_received)
                if message[MESSAGE_TYPE_KEY] == REQUEST_FILE_CHUNK_MESSAGE_TYPE:
                    filename = message[MSG_FILENAME_KEY]
                    chunk_number = message[MSG_CHUNK_NUMBER_KEY]
                    file_id = message[MSG_FILE_DOWNLOAD_PROCESS_ID_KEY]
                    self.send_a_file_chunk_to_a_peer(filename, file_id, chunk_number,requester_addr)
            except: # This is a file chunk that you are receiving
                file_process_id = data_received[0:10].split(ID_DELIMITER)
                file_download_process = self.file_download_process_info[int(file_process_id[0])]
                file_name = file_download_process[MSG_FILENAME_KEY]
                chunk_number = int(file_process_id[1])
                chunk_file_directory = os.path.join(self.directory, file_name+ "." +str(chunk_number)+CHUNK_EXTENSION)
                actual_data = data_received[10:]
                with open(chunk_file_directory, 'wb') as new_chunk_file:
                    new_chunk_file.write(actual_data)
                file_download_process[CHUNKS_NEEDED].pop(file_process_id[1])
                self.file_download_process_info[int(file_process_id[0])] = file_download_process
                if len(file_download_process[CHUNKS_NEEDED]) == 0:
                    self.combine_chunks(file_name)
                else:
                    chunk_numbers = []
                    for key in file_download_process[CHUNKS_NEEDED]:
                        chunk_numbers.append(key)
                    chunk_owners = file_download_process[CHUNKS_NEEDED][chunk_numbers[0]]
                    self.download_chunk_from_a_random_peer(chunk_owners, file_name, int(file_process_id[0]), int(chunk_numbers[0]))

    def send_a_file_chunk_to_a_peer(self, filename, file_id, chunk_number, requester_addr):
        chunk_file_bytes = None
        if file_utils.has_file(self.directory, filename):
            with open(os.path.join(self.directory, filename), "rb") as chunk_file:
                chunk_file.seek(chunk_number * self.chunk_size)
                chunk_file_bytes = chunk_file.read(self.chunk_size)
        else:
            with open(os.path.join(self.directory, filename + "." + str(chunk_number) + CHUNK_EXTENSION)) as chunk_file:
                chunk_file_bytes = chunk_file.read(self.chunk_size)
        bytes_array = bytearray(str(file_id) + ID_DELIMITER + str(chunk_number))
        padding = 10 - len(bytes_array)
        for _ in range(padding):
            bytes_array.append(ID_DELIMITER)
        self.listening_socket.sendto(bytes_array + chunk_file_bytes, requester_addr)

    def initiate_download(self, filename):
        """
        Downloads the file with this filename from other Peers in the network

        Process is transparent to the user. Peer program decides which other
        Peer to download from, as well as the chunks to request.
        """
        # check if I already have the full file. IF YES: quit downloading.
        if file_utils.has_file(self.directory, filename):
            logger.print_file_exists()
            return;

        # query the tracker on who has the chucks to the file by supplying the filename / checksum
        message = {}
        message[MESSAGE_TYPE_KEY] = QUERY_FILE_MESSAGE_TYPE
        message[MSG_FILENAME_KEY] = filename
        reply = self.send_message_to_tracker(message)

        # Handle "file not found"
        if reply[MESSAGE_TYPE_KEY] == QUERY_FILE_ERROR_MESSAGE_TYPE:
            print(reply["error"])
            return

        # Update list of peers known to be behind NAT
        self.known_peers_behind_nat = reply[MSG_PEER_BEHIND_NAT_KEY]

        # Create process info for the file downloading
        available_chunks = file_utils.get_all_chunk_number_available(self.directory, filename)
        chunks_needed = {}
        chunk_numbers = []
        for key, chunkOwners in reply[MSG_CHUNKS_KEY].items():
            if int(key) not in available_chunks:
                chunks_needed[key] = chunkOwners # { chunk#: [ (ip:port), (ip:port), ... ], chunk#: [ ... ], ... }
                chunk_numbers.append(key)

        if not chunk_numbers: # if all the chunks are available in our directory, just assemble them and Done!
            self.combine_chunks(filename)
            return

        file_download_info = {CHUNKS_NEEDED: chunks_needed, MSG_FILENAME_KEY: reply[MSG_FILENAME_KEY]}
        file_id = len(self.file_download_process_info)
        self.file_download_process_info.append(file_download_info)
        chunk_owners = chunks_needed[chunk_numbers[0]]
        # Kick off the first chunk download
        self.download_chunk_from_a_random_peer(chunk_owners, filename, file_id, int(chunk_numbers[0]))

    def download_chunk_from_a_random_peer(self, chunk_owners, filename, file_id, chunk_number):
        random_host_index = randint(0, len(chunk_owners) - 1)
        random_host_ip_and_port = chunk_owners[random_host_index].split(IP_PORT_DELIMITER)
        owner_address = (random_host_ip_and_port[0], int(random_host_ip_and_port[1]))
        if self.hole_punch:
            self.hole_punch_to_peer(owner_address)
        if chunk_owners[random_host_index] in self.known_peers_behind_nat: # The peer you wanted to get the file chunk from is behind NAT
            logger.print_peer_behind_nat_message()
            self.send_signal_to_tracker_for_file_chunk(owner_address, filename, file_id, chunk_number)
        else: # The peer you wanted to get the file chunk from is not behind NAT
            self.request_file_chunk_from_peer(owner_address, filename, file_id, chunk_number)

    def send_signal_to_tracker_for_file_chunk(self, owner_address, filename, file_download_process_id, chunk_number):
        message = {}
        message[MESSAGE_TYPE_KEY] = REQUEST_FILE_CHUNK_NAT_MESSAGE_TYPE
        message[MSG_FILENAME_KEY] = filename
        message[MSG_FILE_DOWNLOAD_PROCESS_ID_KEY] = file_download_process_id
        message[MSG_CHUNK_NUMBER_KEY] = chunk_number
        if self.hole_punch:
            message[MSG_RECEIVER_ADDRESS_KEY] = self.external_ip + IP_PORT_DELIMITER + str(self.external_port)
        message[MSG_OWNER_ADDRESS_KEY] = owner_address[0] + IP_PORT_DELIMITER + str(owner_address[1])
        self.send_message_to_tracker(message)

    def request_file_chunk_from_peer(self, owner_address, filename, file_download_process_id, chunk_number):
        print("Requesting from " + str(owner_address))
        message = {}
        message[MESSAGE_TYPE_KEY] = REQUEST_FILE_CHUNK_MESSAGE_TYPE
        message[MSG_FILE_DOWNLOAD_PROCESS_ID_KEY] = file_download_process_id
        message[MSG_FILENAME_KEY] = filename
        message[MSG_CHUNK_NUMBER_KEY] = chunk_number
        self.listening_socket.sendto(json.dumps(message), owner_address)

    def combine_chunks(self, filename):
        """
        Check if we have all the files, combine them, and remove all the chunks
        """
        message = {}
        message[MESSAGE_TYPE_KEY] = QUERY_FILE_MESSAGE_TYPE
        message[MSG_FILENAME_KEY] = filename
        reply = self.send_message_to_tracker(message)

        # Handle "file not found"
        if reply[MESSAGE_TYPE_KEY] == QUERY_FILE_ERROR_MESSAGE_TYPE:
            print(reply["error"])
            return

        num_of_keys = len(reply[MSG_CHUNKS_KEY].keys())
        file_utils.combine_chunks(self.directory, filename, num_of_keys, self.chunk_size)

    def hole_punching(self):
        """
        Punch a hole to advertise our public IP and port
        """
        logger.print_hole_punching_message()
        nat_type, external_ip, external_port = stun.get_ip_info("0.0.0.0", self.port)
        if nat_type == SYMMETRIC_NAT_TYPE:
            logger.print_symmetric_nat_message()
            exit()
        self.external_ip = external_ip
        self.external_port = external_port
        logger.print_hole_punch_result(self.external_ip, self.external_port)

    def tracker_hole_punching(self):
        """
        Punch a hole so that tracker can contact us
        """
        logger.print_hole_punching_message(tracker=True)
        nat_type, external_ip, external_port = stun.get_ip_info("0.0.0.0", self.signal_port)
        if nat_type == SYMMETRIC_NAT_TYPE:
            logger.print_symmetric_nat_message()
            exit()
        self.external_signal_port = external_port
        logger.print_hole_punch_result(self.external_ip, self.external_signal_port)

    def listen_for_request(self):
        """
        Create the main thread for sending and receiving file chunks
        """
    	try:
            self.listening_socket.bind(('', self.port))
        except socket.error as msg:
            logger.print_socket_error_message(msg)
            sys.exit()
        logger.print_socket_bind_message()
        self.socket_listening_thread = threading.Thread(target=self.listen_func, args=())
        self.socket_listening_thread.start()

    def listen_for_tracker_signal(self):
        """
        Create a thread to listen for tracker signals to send a file chunk
        """
        try:
            self.signal_socket.bind(('', self.signal_port))
        except socket.error as msg:
            logger.print_socket_error_message(msg)
            sys.exit()
        logger.print_socket_bind_message()
        self.signal_listening_thread = threading.Thread(target=self.signal_listening, args=())
        self.signal_listening_thread.start()

    def update_tracker_new_files(self):
        """
        Informs the Tracker of the additional files and chunks that you are sharing
        """
        self.process_dir_listing()
        message = self.create_info_for_tracker()
        self.send_message_to_tracker(
            message=message,
            success_msg=UPDATE_PEER_INFO_SUCCESS_MESSAGE,
            failure_msg=UPDATE_PEER_INFO_FAIL_MESSAGE
        )

    def exit_network(self):
        """
        Tells the Tracker that you are exiting the network
        """
        message = {}
        if self.hole_punch:
            message[MSG_SOURCE_IP_KEY] = self.external_ip
            message[MSG_SOURCE_PORT_KEY] = self.external_port
        else:
            message[MSG_SOURCE_PORT_KEY] = self.port
        message[MESSAGE_TYPE_KEY] = EXIT_MESSAGE_TYPE
        self.send_message_to_tracker(message)
        logger.print_peer_exiting()
        exit()

    def start_tui(self):
        """
        Displays commands to the user, and dispatches to the relevant methods
        """
        logger.print_peer_tui()
        while True:
            try:
                print("# > ", end="")
                user_input = raw_input()
                input_lst = user_input.split(" ")
                if len(input_lst) > 2:
                    logger.print_invalid_command(msg)
                    continue
                if not input_lst[0].isdigit():
                    logger.print_invalid_command(msg)
                    continue
                command = int(input_lst[0])
                filename = input_lst[1] if len(input_lst) > 1 else None
                if command == 1:
                    self.get_available_files()
                # elif command == 2: # TODO: We should remove this entirely
                #     self.get_peers_with_file(filename) if filename else print("Please provide a filename")
                elif command == 3:
                    self.initiate_download(filename) if filename else logger.print_provide_filename()
                elif command == 4:
                    self.update_tracker_new_files()
                elif command == 5:
                    self.exit_network()
                else:
                    logger.print_invalid_command(msg)
                    continue
            except KeyboardInterrupt:
                self.exit_network()
                self.stop()
                exit()

    def start_peer(self):
        # Punch a hole
        if self.hole_punch:
            self.hole_punching()
            self.tracker_hole_punching()
        # Start a listening socket thread
        self.listen_for_request()

        if self.hole_punch:
            self.listen_for_tracker_signal()

        # Register as peer
        self.register_as_peer()
        # Start the Text UI
        self.start_tui()

    def stop(self):
        logger.print_peer_stopping_message()
        self.listening_socket.close()

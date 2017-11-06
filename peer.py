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

from runner import Runner
from random import randint

class Peer(Runner):
    def __init__(self, settings):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.signal_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tracker_address = settings["tracker-address"]
        self.tracker_port = settings["tracker-port"]
        self.port = settings["port"]
        self.directory = settings["peer-directory"]
        self.hole_punch = "hole-punching" in settings
        self.tracker_signal_port = settings["tracker-signal-port"]
        self.signal_port = settings["signal-port"]
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
        # {"filechecksum": "checksum", "num_of_chunks": 1, "filename": "test_c"}
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
        ret["filechecksum"] = file_checksum
        ret["num_of_chunks"] = num_chunks
        ret["filename"] = filename
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
            ret.append({"filename": filename, "chunks": chunks})
        return ret

    def process_dir_listing(self):
        # Process the files in self.directory, and sets the result in
        # self.files and self.chunks
        all_filenames = self.get_directory_files()
        files = [i for i in all_filenames if i[-6:] != ".chunk"]
        chunks = [i for i in all_filenames if i[-6:] == ".chunk"]
        self.files = [self.format_complete_file(i) for i in files]
        self.chunks = self.format_chunks(chunks)

    def create_info_for_tracker(self):
        # Informs tracker of files in directory, checksum of each file, owned
        # chunks of each file, source port of Peer
        # {
        #     "source_port": port_num,
        #     "files": [{"filechecksum": "checksum", "num_of_chunks": 1, "filename": "test_c"}, ...],
        #     "chunks": [{"chunks": [1, 2, 3, 4, 5], "filename": "test_b"}, ...]
        #     "message_type": "INFORM_AND_UPDATE",
        # }
        info = {}
        if self.hole_punch:
            info["source_ip"] = self.external_ip
            info["source_port"] = self.external_port
            info["signal_port"] = self.external_signal_port
        else:
            info["source_port"] = self.port
        info["files"] = self.files
        info["chunks"] = self.chunks
        info["message_type"] = "INFORM_AND_UPDATE"
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
            success_msg="Successfully registered as Peer",
            failure_msg="Unable to register as Peer. Exiting...",
            should_exit=True
        )

    def get_available_files(self):
        """
        Asks the Tracker for a list of all files in this network
        """
        message = { "message_type": "QUERY_LIST_OF_FILES" }
        reply = self.send_message_to_tracker(message)
        # Format the replies and display to user
        filenames = sorted(reply['files'])
        print("These are the available files on the network: ")
        for idx, filename in enumerate(filenames, start=1):
            print("{}: {}".format(idx, filename))

    def get_peers_with_file(self, filename):
        """
        Asks the Tracker for a list of peers containing a file with this filename
        """
        message = {}
        message['message_type'] = "QUERY_FILE"
        message['filename'] = filename
        reply = self.send_message_to_tracker(message)
        # Handle "file not found"
        if reply["message_type"] == "QUERY_FILE_ERROR":
            print(reply["error"])
            return
        # Format the replies and display to user
        print("These are the Peers who currently have the file: ")
        owners = sorted(reply['owners'])
        for idx, owner in enumerate(owners, start=1):
            print("{}: {}".format(idx, owner))
        reply.pop("owners", None)  # remove the "owner" key
        reply.pop("message_type", None)  # remove the "message_type" key
        print("")
        print("File information: ")
        for k, v in reply.items():
            print("{}: {}".format(k, v))

    def signal_listening(self):
        while True:
            data_received, _ = self.signal_socket.recvfrom(1024)
            try:
                message = json.loads(data_received)
                if message["message_type"] == "REQUEST_FILE_CHUNK_SIGNAL":
                    filename = message["filename"]
                    chunk_number = message["chunk_number"]
                    receiver_address = message["receiver_address"].split(":")
                    if file_utils.has_file(self.directory, filename): # Has full file
                        with open(os.path.join(self.directory, filename), "rb") as chunk_file:
                            chunk_file.seek(chunk_number * self.chunk_size)
                            chunk_file_bytes = chunk_file.read(self.chunk_size)
                            bytes_array = bytearray(str(message["file_download_process_id"]) + ","+ str(message["chunk_number"]))
                            padding = 10 - len(bytes_array)
                            for _ in range(padding): # Heck it works
                                bytes_array.append(",")
                            self.listening_socket.sendto(bytes_array + chunk_file_bytes, requesterAddr)
                    else:
                        with open(os.path.join(self.directory, filename + "." + str(chunk_number) + ".chunk")) as chunk_file:
                            chunk_file_bytes = chunk_file.read(self.chunk_size)
                            bytes_array = bytearray(str(message["file_download_process_id"]) + ","+ str(message["chunk_number"]))
                            padding = 10 - len(bytes_array)
                            for _ in range(padding): # Heck it works
                                bytes_array.append(",")
                            self.listening_socket.sendto(bytes_array + chunk_file_bytes, requesterAddr)
            except:
                print("There is an error listening to tracker signal")

    def hole_punch_to_peer(self, owner_address):
        # Called when self is behind NAT
        # Sends a blank JSON to allow peer to connect to self.external_port
        # Essentially creates a mapping in the NAT-enabled router
        message = {}
        self.listening_socket.sendto(json.dumps(message), owner_address)

    def upload(self): #  TODO: If the peer is behind NAT, tell the tracker that we want the file, and punch a hole to recieve file chunk, else do normally
        while True:
            # receive the request info fileInfo{ "fileName": "", "chunkFileName": "", "chunkNumber": int  }
            ## data_from_requester = self.connect.recv(1024) [TCP]
            data_received, requesterAddr = self.listening_socket.recvfrom(1024) #[UDP]
            try:
                message = json.loads(data_received)
                if message["message_type"] == "REQUEST_FILE_CHUNK":
                    filename = message["file_name"]
                    chunk_number = message["chunk_number"]
                    if file_utils.has_file(self.directory, filename): # Has full file
                        with open(os.path.join(self.directory, filename), "rb") as chunk_file:
                            chunk_file.seek(chunk_number * self.chunk_size)
                            chunk_file_bytes = chunk_file.read(self.chunk_size)
                            bytes_array = bytearray(str(message["file_download_process_id"]) + ","+ str(message["chunk_number"]))
                            padding = 10 - len(bytes_array)
                            for _ in range(padding): # Heck it works
                                bytes_array.append(",")
                            self.listening_socket.sendto(bytes_array + chunk_file_bytes, requesterAddr)
                    else:
                        with open(os.path.join(self.directory, filename + "." + str(chunk_number) + ".chunk")) as chunk_file:
                            chunk_file_bytes = chunk_file.read(self.chunk_size)
                            bytes_array = bytearray(str(message["file_download_process_id"]) + ","+ str(message["chunk_number"]))
                            padding = 10 - len(bytes_array)
                            for _ in range(padding): # Heck it works
                                bytes_array.append(",")
                            self.listening_socket.sendto(bytes_array + chunk_file_bytes, requesterAddr)
            except: # This is a file chunk that you are receiving
                file_process_id = data_received[0:10].split(",")
                file_download_process = self.file_download_process_info[int(file_process_id[0])]
                file_name = file_download_process["filename"]
                chunk_number = int(file_process_id[1])
                chunk_file_directory = os.path.join(self.directory, file_name+ "." +str(chunk_number)+".chunk")
                actual_data = data_received[10:]
                with open(chunk_file_directory, 'wb') as new_chunk_file:
                    new_chunk_file.write(actual_data)
                file_download_process["chunks_needed"].pop(file_process_id[1])
                self.file_download_process_info[int(file_process_id[0])] = file_download_process
                print(file_download_process)
                if len(file_download_process["chunks_needed"]) == 0:
                    self.combine_chunks(file_name)
                else:
                    chunk_numbers = []
                    for key in file_download_process["chunks_needed"]:
                        chunk_numbers.append(key)
                    chunk_owners = file_download_process["chunks_needed"][chunk_numbers[0]]
                    random_host_index = randint(0, len(chunk_owners)-1)
                    randomHostIPandPort = chunk_owners[random_host_index].split(":")
                    owner_address = (randomHostIPandPort[0], int(randomHostIPandPort[1])) # generate a tuple of (ip, port) of the owner of the chunk
                    if self.hole_punch:
                        hole_punch_to_peer(owner_address)
                    if owner_address in self.known_peers_behind_nat:
                        print("Peer is behind NAT...")
                        message["message_type"] = "REQUEST_FILE_CHUNK_NAT"
                        message["filename"] = str(filename)
                        message["file_download_process_id"] = file_id
                        message["file_name"] = str(filename)
                        message["chunk_number"] = int(chunk_numbers[0])
                        message["owner_address"] = chunk_owners[random_host_index]
                        self.send_message_to_tracker(message)
                    else:
                        print("Requesting from " + str(owner_address))
                        message = {}
                        message["message_type"] = "REQUEST_FILE_CHUNK"
                        message["file_download_process_id"] = int(file_process_id[0])
                        message["file_name"] = str(file_name)
                        message["chunk_number"] = int(chunk_numbers[0])
                        self.listening_socket.sendto(json.dumps(message), owner_address)


    def download(self, filename): #  TODO: If the peer is behind NAT, tell the tracker that we want the file, and punch a hole to recieve file chunk, else do normally
        """
        Downloads the file with this filename from other Peers in the network

        Process is transparent to the user. Peer program decides which other
        Peer to download from, as well as the chunks to request.
        """
        # check if I already have the full file. IF YES: quit downloading.
        if file_utils.has_file(self.directory, filename):
            print("File already exists in your directory")
            return;

        # query the tracker on who has the chucks to the file by supplying the filename / checksum
        message = {}
        message["message_type"] = "QUERY_FILE"
        message["filename"] = filename
        reply = self.send_message_to_tracker(message)

        # Handle "file not found"
        if reply["message_type"] == "QUERY_FILE_ERROR":
            print(reply["error"])
            return

        # Update list of peers known to be behind NAT
        self.known_peers_behind_nat = reply["peer_behind_nat"]

        # Create process info for the file downloading
        available_chunks = file_utils.get_all_chunk_number_available(self.directory, filename)
        chunks_needed = {}
        chunk_numbers = []
        for key, chunkOwners in reply["chunks"].items():
            if int(key) not in available_chunks:
                chunks_needed[key] = chunkOwners # { chunk#: [ (ip:port), (ip:port), ... ], chunk#: [ ... ], ... }
                chunk_numbers.append(key)

        if not chunk_numbers: # if all the chunks are available in our directory, just assemble them and Done!
            self.combine_chunks(filename)
            return

        file_download_info = {"chunks_needed": chunks_needed, "filename": reply["filename"]}
        file_id = len(self.file_download_process_info)
        self.file_download_process_info.append(file_download_info)
        # Kick off the first chunk download
        chunk_owners = chunks_needed[chunk_numbers[0]]
        random_host_index = randint(0, len(chunk_owners)-1)
        randomHostIPandPort = chunk_owners[random_host_index].split(":")
        owner_address = (randomHostIPandPort[0], int(randomHostIPandPort[1])) # generate a tuple of (ip, port) of the owner of the chunk
        if self.hole_punch:
            hole_punch_to_peer(owner_address)
        if owner_address in self.known_peers_behind_nat:
            print("Peer is behind NAT...")
            message["message_type"] = "REQUEST_FILE_CHUNK_NAT"
            message["filename"] = str(filename)
            message["file_download_process_id"] = file_id
            message["file_name"] = str(filename)
            message["chunk_number"] = int(chunk_numbers[0])
            message["owner_address"] = chunk_owners[random_host_index]
            self.send_message_to_tracker(message)
        else:
            print("Requesting from " + str(owner_address))
            message = {}
            message["message_type"] = "REQUEST_FILE_CHUNK"
            message["file_download_process_id"] = file_id
            message["file_name"] = str(filename)
            message["chunk_number"] = int(chunk_numbers[0])
            self.listening_socket.sendto(json.dumps(message), owner_address)

    def combine_chunks(self, filename):
        message = {}
        message["message_type"] = "QUERY_FILE"
        message["filename"] = filename
        reply = self.send_message_to_tracker(message)

        # Handle "file not found"
        if reply["message_type"] == "QUERY_FILE_ERROR":
            print(reply["error"])
            return

        numberOfKeys = len(reply["chunks"].keys())
        chunkIndex = 0

        new_file_directory = os.path.join(self.directory, filename)

        while(chunkIndex < numberOfKeys):
            if str(chunkIndex) in reply["chunks"]:
                chunk_file_name = filename + "." + str(chunkIndex) + ".chunk"
                chunk_file_directory = os.path.join(self.directory, chunk_file_name)

                with open(new_file_directory, 'ab') as new_file:
                    with open(chunk_file_directory, 'rb') as chunk_file:
                        new_file.write(chunk_file.read(self.chunk_size))

                chunkIndex+=1

                if(chunkIndex == numberOfKeys):
                    self.removeAllAssociatedChunks(filename)

            else:
                break
        return

    def removeAllAssociatedChunks(self, filename):
        path = os.path.join(self.directory, filename+".*"+".chunk")
        for filename in glob.glob(path):
            os.remove(filename)
        return

    def hole_punching(self):
        print("Punching a hole...")
        nat_type, external_ip, external_port = stun.get_ip_info("0.0.0.0", self.port)
        if nat_type == "Symmetric NAT":
            print("You are using Symmetric NAT, not handling that")
            exit()
        self.external_ip = external_ip
        self.external_port = external_port
        print("Hole punched: Your IP is " + str(self.external_ip) + " and your port number is " + str(self.external_port))

    def tracker_hole_punching(self):
        print("Punching a hole for tracker signal...")
        nat_type, external_ip, external_port = stun.get_ip_info("0.0.0.0", self.signal_port)
        if nat_type == "Symmetric NAT":
            print("You are using Symmetric NAT, not handling that")
            exit()
        self.external_signal_port = external_port
        print("Hole punched: Your IP is " + str(self.external_ip) + " and your port number is " + str(self.external_signal_port))

    def listen_for_request(self):
    	try:
            # self.listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listening_socket.bind(('', self.port))
        except socket.error as msg:
            print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            sys.exit()
        print('Socket bind complete')
        self.socket_listening_thread = threading.Thread(target=self.upload, args=())
        self.socket_listening_thread.start()

    def listen_for_tracker_signal(self):
        try:
            self.signal_socket.bind(('', self.signal_port))
        except socket.error as msg:
            print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            sys.exit()
        print('Socket bind complete')
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
            success_msg="Update successful",
            failure_msg="Update unsuccessful"
        )

    def exit_network(self):
        """
        Tells the Tracker that you are exiting the network
        """
        message = {}
        if self.hole_punch:
            message['source_ip'] = self.external_ip
            message['source_port'] = self.external_port
        else:
            message["source_port"] = self.port
        message["message_type"] = "EXIT"
        self.send_message_to_tracker(message)
        print("Exiting...")
        exit()

    def start_tui(self):
        """
        Displays commands to the user, and dispatches to the relevant methods
        """
        msg = """
/////////////////////////////////////////////////////////////////////

Welcome to P2P Client. Please choose one of the following commands:

/////////////////////////////////////////////////////////////////////

1. List all available files, along with their checksums
   Usage: 1

2. List all Peers possessing a file
   Usage: 2 <file>

3. Download file
   Usage: 3 <file>

4. Update Tracker of your new files and chunks
   Usage: 4

5. Exit P2P Client
   Usage: 5
        """
        print(msg)
        while True:
            print("# > ", end="")
            user_input = raw_input()
            input_lst = user_input.split(" ")
            if len(input_lst) > 2:
                print(msg)
                print("Invalid command")
                continue
            if not input_lst[0].isdigit():
                print(msg)
                print("Invalid command")
                continue
            command = int(input_lst[0])
            filename = input_lst[1] if len(input_lst) > 1 else None
            if command == 1:
                self.get_available_files()
            elif command == 2:
                self.get_peers_with_file(filename) if filename else print("Please provide a filename")
            elif command == 3:
                self.download(filename) if filename else print("Please provide a filename")
            elif command == 4:
                self.update_tracker_new_files()
            elif command == 5:
                self.exit_network()
            else:
                print(msg)
                print("Invalid command")
                continue

    def start_peer(self):
        # Punch a hole
        if self.hole_punch:
            self.hole_punching()
            self.tracker_hole_punching()
        # # Start a listening socket thread
        self.listen_for_request()

        if self.hole_punch:
            # listen from signal port TODO
            self.listen_for_tracker_signal()
        # # Register as peer
        self.register_as_peer() # Tell the tracker if we are behind a NAT, add signal port TODO
        # # Start the Text UI
        self.start_tui()

    def stop(self):
        print("Stopping peer")
        # self.socket_listening_thread.terminate()
        self.listening_socket.close()

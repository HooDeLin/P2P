from __future__ import print_function
import socket
import threading
import sys
import json
import os
import hashlib
import stun

from recurring_thread import RecurringThread
from runner import Runner
from random import randint

class Peer(Runner):
    def __init__(self, settings):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_address = settings["tracker-address"]
        self.tracker_port = settings["tracker-port"]
        self.port = settings["port"]
        self.directory = settings["peer-directory"]
        self.external_ip = None
        self.external_port = None
        self.chunk_size = 256 * 1024
        # List of (formatted) files that the Peer is sharing
        self.files = []
        # List of (formatted) incomplete files that the Peer is sharing
        self.chunks = []
        # array of threads
        self.thread_array = []
        self.connect = None

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
        info["source_ip"] = self.external_ip
        info["source_port"] = self.external_port
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
            data = sending_socket.recv(1024)
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

    def upload(self):
        # receive the request info fileInfo["chunkFileName"] (the chunk name)
        data_from_requester = self.connect.recv(1024)

        if data_from_requester:
            fileInfo = json.loads(data_from_requester)
            print ("Requesting following chunk: " + fileInfo["chunkFileName"])

            main_file_name = fileInfo["fileName"]
            chunk_file_name = fileInfo["chunkFileName"];
            chunk_number = int(fileInfo["chunkNumber"]);

            print(main_file_name)

            path_directory = os.path.join(self.directory, chunk_file_name)
            file_path_directory = os.path.join(self.directory, main_file_name)

            if os.path.isfile(file_path_directory):
            	message = {}
                message["message_type"] = "FULL_FILE_EXISTS"
                message["chunkFileSize"] = os.path.getsize(file_path_directory)

                self.connect.send(json.dumps(message))

                response_data_from_requester = self.connect.recv(1024)
                requester_response = json.loads(response_data_from_requester)

                if requester_response["message_type"] == "OK":
                    with open(file_path_directory, 'rb') as file_name:
                    	print("sending...")
                        file_name.seek(0)
                        bytesToSend = file_name.read(256)

                        self.connect.send(bytesToSend)

                        while bytesToSend != "":
                            bytesToSend = file_name.read(256)
                            self.connect.send(bytesToSend)

                        file_name.close()
                        print("Done.")

            elif os.path.isfile(path_directory):
                message = {}
                message["message_type"] = "FILE_EXISTS"
                message["chunkFileSize"] = os.path.getsize(path_directory)

                self.connect.send(json.dumps(message))

                response_data_from_requester = self.connect.recv(1024)
                requester_response = json.loads(response_data_from_requester)
                if requester_response["message_type"] == "OK":
                    with open(path_directory, 'rb') as file_name:
                    	print("sending...")
                    	bytesToSend = file_name.read(256)
                        self.connect.send(bytesToSend)

                        while bytesToSend != "":
                            bytesToSend = file_name.read(256)
                            self.connect.send(bytesToSend)

                        file_name.close()
                        print("Done")
            else:
                self.connect.send(json.dumps({"message_type":"NO_EXISTS"}))


    def download(self, filename):
        """
        Downloads the file with this checksum from other Peers in the network

        Process is transparent to the user. Peer program decides which other
        Peer to download from, as well as the chunks to request.
        """

        full_file_directory = os.path.join(self.directory, filename)

        requested_from_owner_index = []

        sending_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # query the tracker who has the chucks to the file by supplying the filename / checksum
        # message = { "message_type": "QUERY_FILE", "filename": filename }
        # reply = self.send_message_to_tracker(message)
        message = {}
        message["message_type"] = "QUERY_FILE"
        message["filename"] = filename
        reply = self.send_message_to_tracker(message)

        print(reply)

        # Handle "file not found"
        if reply["message_type"] == "QUERY_FILE_ERROR":
            print(reply["error"])
            return

        # chunks = {chunk#: ["ip:port", "ip:port"], chunk#: ["ip:port"]}
        for key, chunkOwners in reply["chunks"].items():
            chunk_file_name = filename + "." + key + ".chunk"
            number_of_owners = len(chunkOwners)

            if os.path.isfile(full_file_directory):
                continue;

            else:
                for owner in chunkOwners:

                    #randomly choosing host
                    randomHostIndex = randint(0, number_of_owners-1)
                    while randomHostIndex in requested_from_owner_index:
                        randomHostIndex = randint(0, number_of_owners-1)

                    requested_from_owner_index.append(randomHostIndex) # already chosen this owner for this chunk

                    randomHostIPandPort = chunkOwners[randomHostIndex].split(":")

                    owner_address = (randomHostIPandPort[0], int(randomHostIPandPort[1]))
                    print("Requesting from " + str(owner_address))
                    sending_socket.connect(owner_address)

                    try:
                        message = {}
                        message["fileName"] = str(filename)
                        message["chunkFileName"] = chunk_file_name
                        message["chunkNumber"] = int(key)

                        sending_socket.send(json.dumps(message)) # send the file info message to the owner
                        ownerResponse = sending_socket.recv(1024)
                        received_data_from_owner = json.loads(ownerResponse)

                        # received_data_from_owner['message_type']:string, received_data_from_owner['chunkFileSize']:int
                        if received_data_from_owner["message_type"] == "FULL_FILE_EXISTS":
                            chunk_file_size = received_data_from_owner["chunkFileSize"]

                            reply_message = {}
                            reply_message["message_type"] = "OK"
                            sending_socket.send(json.dumps(reply_message)) #aight! send it over

                            new_chunk_file = open(full_file_directory, 'wb')
                            chunk_data_from_owner = sending_socket.recv(256)
                            total_received = len(chunk_data_from_owner)

                            new_chunk_file.write(chunk_data_from_owner)

                            while total_received < chunk_file_size:
                                chunk_data_from_owner = sending_socket.recv(256)
                                total_received += len(chunk_data_from_owner)
                                new_chunk_file.write(chunk_data_from_owner)

                            new_chunk_file.close()

                            # update tracker
                            self.register_as_peer()

                        elif received_data_from_owner["message_type"] == "FILE_EXISTS":
                            chunk_file_size = received_data_from_owner["chunkFileSize"]

                            reply_message = {}
                            reply_message["message_type"] = "OK"
                            sending_socket.send(json.dumps(reply_message)) #aight! send it over

                            chunk_file_directory = os.path.join(self.directory, chunk_file_name)

                            new_chunk_file = open(chunk_file_directory, 'wb')
                            chunk_data_from_owner = sending_socket.recv(256)
                            total_received = len(chunk_data_from_owner)

                            new_chunk_file.write(chunk_data_from_owner)

                            while total_received < chunk_file_size:
                                chunk_data_from_owner = sending_socket.recv(256)
                                total_received += len(chunk_data_from_owner)
                                new_chunk_file.write(chunk_data_from_owner)

                            new_chunk_file.close()

                            # update tracker
                            self.register_as_peer()

                        else:
                            continue


                    except:
                        sending_socket.close()

        sending_socket.close()

    def hole_punching(self):
        print("Punching a hole...")
        nat_type, external_ip, external_port = stun.get_ip_info("0.0.0.0", self.port)
        if nat_type == "Symmetric NAT":
            print("You are using Symmetric NAT, not handling that")
            exit()
        print("Hole punched: Your IP is " + str(self.external_ip) + " and your port number is " + str(self.external_port))
        self.external_ip = external_ip
        self.external_port = external_port

    def listen_for_request(self):
    	try:
        	self.listening_socket.bind(("", self.port))
        except socket.error as msg:
            print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            sys.exit()
        print('Socket bind complete')

        self.listening_socket.listen(10)
        print("Socket now listening to any incoming request")

        thread = threading.Thread(target=self.process_thread, args=())
        self.thread_array.append(thread)
        thread.start()

    def process_thread(self):
    	while True:
            self.connect, neighbor_addr = self.listening_socket.accept()
            print("neighbor connedted ip:<" + str(neighbor_addr) + ">")
            thread = threading.Thread(target=self.upload)
            self.thread_array.append(thread)
            thread.start()

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
   Usage: 2 <file checksum>

3. Download file
   Usage: 3 <file checksum>

4. Update Tracker of your new files and chunks
   Usage: 4

5. Exit P2P Client
   Usage: 5
        """
        print(msg)
        while True:
            print("# > ", end="")
            user_input = raw_input()
            # try:
            input_lst = user_input.split(" ")
            if len(input_lst) > 2:
                print(msg)
                print("Invalid command")
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
            # except:
            #     print(msg)
            #     print("Invalid selection")

    def start_peer(self):
        # Punch a hole
        self.hole_punching()
        # # Start a listening socket thread
        self.listen_for_request()
        # # Register as peer
        self.register_as_peer()
        # # Start the Text UI
        self.start_tui()

    def stop(self):
        print("Stopping peer")

        for thread in thread_array:
        	thread.exit()
        # self.listening_socket.close()

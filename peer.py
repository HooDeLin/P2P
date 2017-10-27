from __future__ import print_function
import socket
import threading
import sys
import json
import os
import hashlib

from recurring_thread import RecurringThread
from runner import Runner

class Peer(Runner):
    def __init__(self, settings):
        # self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_address = settings["tracker-address"]
        self.tracker_port = settings["tracker-port"]
        self.port = settings["port"]
        self.directory = settings["peer-directory"]
        self.chunk_size = 256 * 1024
        # List of (formatted) files that the Peer is sharing
        self.files = []
        # List of (formatted) incomplete files that the Peer is sharing
        self.chunks = []

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

    def download_file(self, checksum):
        """
        Downloads the file with this checksum from other Peers in the network

        Process is transparent to the user. Peer program decides which other
        Peer to download from, as well as the chunks to request.
        """
        return 0

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
                self.download_file(filename) if filename else print("Please provide a filename")
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
        # Start a listening socket thread
        # Register as peer
        self.register_as_peer()
        # Start the Text UI
        self.start_tui()

    def stop(self):
        print("Stopping peer")
        # self.listening_socket.close()

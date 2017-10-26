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
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_address = settings["tracker-address"]
        self.tracker_port = settings["tracker-port"]
        self.port = settings["port"]
        self.directory = settings["peer-directory"]
        self.chunk_size = 256 * 1024
        # List of (formatted) files that the Peer is sharing
        self.files = []
        # List of (formatted) incomplete files that the Peer is sharing
        self.chunks = []
        print ("Socket created")

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

    def register_as_peer(self):
        """
        Informs the Tracker of the files and chunks that you are sharing
        Does this by opening a socket to the Tracker and sending the data
        """
        server_address = (self.tracker_address, self.tracker_port)
        # Important to call this before trying to create the message to send
        self.process_dir_listing()
        self.listening_socket.connect(server_address)
        try:
            message = self.create_info_for_tracker()
            self.listening_socket.sendall(json.dumps(message))
            data = self.listening_socket.recv(1024)
            received_data = json.loads(data)
        except:
            print("Unable to register as peer")
            exit()
        finally:
            print("Registered as peer")
            self.listening_socket.close()

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
            command = raw_input()
            try:
                command = int(command)
                if command == 1:
                    return 0
                elif command == 2:
                    return 0
                elif command == 3:
                    return 0
                elif command == 4:
                    return 0
                elif command == 5:
                    return 0
                else:
                    print(msg)
                    print("Invalid selection")
            except:
                print(msg)
                print("Invalid selection")


    # def heartbeat_func(self):
    #     self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     server_address = (self.tracker_address, self.tracker_port)
    #     self.listening_socket.connect(server_address)
    #     try:
    #         message = {}
    #         message["msg_type"] = "HEARTBEAT"
    #         message["peer_id"] = self.peer_id
    #         self.listening_socket.sendall(json.dumps(message))
    #         print("Sent heartbeat message")
    #     except:
    #         print("Unable to send heartbeat message")
    #     finally:
    #         self.listening_socket.close()

    def start_peer(self):
        self.register_as_peer()
        # self.heartbeat = RecurringThread(5, self.heartbeat_func)
<<<<<<< HEAD
        # Start the Text UI
        self.start_tui()
=======

    def stop(self):
        print("Stopping peer")
        self.listening_socket.close()
>>>>>>> ff2528f4063b5bc1bb62ba1cc2f32745d452ca11

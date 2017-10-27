import socket
import threading
import os
import json

class Talk:
    def __init__(self, settings):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.neighbor_address = settings["neighbor-address"]
        self.neighbor_port = settings["neighbor-port"]
        self.address = settings[""]
        self.port = settings["port"]
        self.directory = settings["peer-directory"]
        print ("Socket created")

    def Upload(self, connect):
        path_directory = Path(self.directory)

        # receive the request info fileinfo["chunkFileName"] (the chunk name)
        data_from_requester = connect.recv(1024)

        if data_from_requester:
            fileInfo = json.loads(data) 
            print 'Requesting following chunk: ' + fileInfo["chunkFileName"]

            chunk_file_name = fileinfo["chunkFileName"];

            if path_directory.isfile(chunk_file_name):
                message = {}
                message["message_type"] = "FILE_EXISTS"
                message["chunkFileSize"] = os.path.getsize(self.directory + "/" + chunk_file_name)

                connect.send(json.dumps(message))

                response_data_from_requester = connect.recv(1024)
                requester_response = json.loads(response_data_from_requester)
                if requester_response['message_type'] == 'OK':
                    with open(chunk_file_name, 'rb') as file_name:
                        bytesToSend = file_name.read(1024)
                        connect.send(bytesToSend)

                        while bytesToSend != "":
                            bytesToSend = file_name.read(1024)
                            sock.send(bytesToSend)
            else:
                connect.send(json.dumps({"message_type":"NO_EXISTS"}))


    def Download(self, filename):
        path_directory = Path(self.directory)
        requested_from_owner_index = []

        sending_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    	# query the tracker who has the chucks to the file by supplying the filename / checksum
    	# message = { "message_type": "QUERY_FILE", "filename": filename }
        # reply = self.send_message_to_tracker(message)
        message = {}
        message['message_type'] = "QUERY_FILE"
        message['filename'] = filename
        reply = self.send_message_to_tracker(message)
        
        # Handle "file not found"
        if reply["message_type"] == "QUERY_FILE_ERROR":
            print(reply["error"])
            return 

        # chunks = {chunk#: ["ip:port", "ip:port"], chunk#: ["ip:port"]}
        for key, chunkOwners in reply['chunks'].items():
            chunk_file_name = filename + "." + key + ".chunk"
            number_of_owners = len(chunkOwners)

            if path_directory.isfile(chunk_file_name) 
                continue;

            else:
                for owner in chunkOwners:
                    
                    #randomly choosing host
                    randomHostIndex = randint(0, number_of_owners-1)
                    while randomHostIndex in requested_from_owner_index:
                        randomHostIndex = randint(0, number_of_owners-1)

                    requested_from_owner_index.append(randomHostIndex) # already chosen this owner for this chunk

                    randomHostIPandPort = chunkOwners[randomHostIndex].split(":")

                    owner_address = (randomHostIPandPort[0], randomHostIPandPort[1])
                    sending_socket.connect(owner_address)

                    try:
                        message = {}
                        message['chunkFileName'] = chunk_file_name

                        sending_socket.send(json.dumps(message)) # send the file info message to the owner
                        ownerResponse = sending_socket.recv(1024)
                        received_data_from_owner = json.loads(ownerResponse)
                        
                        # received_data_from_owner['message_type']:string, received_data_from_owner['chunkFileSize']:int
                        if received_data_from_owner['message_type'] == 'FILE_EXISTS':
                            chunk_file_size = received_data_from_owner['chunkFileSize']

                            reply_message = {}
                            reply_message['message_type'] = "OK"
                            sending_socket.send(json.dumps(reply_message)) #aight! send it over

                            new_chunk_file = open(chunk_file_name, 'wb')
                            chunk_data_from_owner = sending_socket.recv(1024)
                            total_received = len(chunk_data_from_owner)

                            new_chunk_file.write(chunk_data_from_owner)

                            while total_received < chunk_file_size:
                                chunk_data_from_owner = sending_socket.recv(1024)
                                total_received += len(chunk_data_from_owner)
                                new_chunk_file.write(chunk_data_from_owner)
                            new_chunk_file.close()

                            # update tracker
                            self.register_as_peer()

                        else:
                            continue


                    except:
                        sending_socket.close()

    def listen_for_request():
        self.listening_socket.bind("", self.port)
        
        print "listening to any incoming request"
        
        while True:
            connect, neighbor_addr = self.listening_socket.accept()
            print "neighbor connedted ip:<" + str(neighbor_addr) + ">"
            thread = threading.Thread(target=self.Upload, args=(connect))
            thread.start()

    if __name__ == '__main__':
        Main()
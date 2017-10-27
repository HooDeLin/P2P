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

        # receive the request info fileinfo["filename"], fileinfo["chunk"] (the chunk name), fileinfo["chunkSize"]
        data = connect.recv(1024)
        if data:
            fileInfoMessage = json.loads(data) 
            print 'Requesting file with the following info: ' + fileInfoMessage

            file_name = fileInfoMessage["filename"];
            chunk_name = fileinfo["chunkNumber"];
            chunk_size = fileInfoMessage["chunkSize"];

            chunk_file_name = chunk_name

            if path_directory.isfile(chunk_file_name):
                connect.send(json.dumps({"message_type":"FILE_EXISTS"}))
                response_data = connect.recv(1024)
                userResponse = json.loads(response_data)
                if userResponse['message_type'] == 'OK':
                    with open(file_name, 'rb') as f:
                        bytesToSend = file_name.read(1024)
                        connect.send(bytesToSend)

                        while bytesToSend != "":
                            bytesToSend = file_name.read(1024)
                            sock.send(bytesToSend)
            else:
                connect.send(json.dumps({"message_type":"NO_EXISTS"}))


    def Download(self, filename):
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

        for index, owner in enumerate(reply['owners'], start=1): 
            socket = socket.socket()
            socket.connect(owner)

            for chunkIndex, chunk in enumerate(reply['chunks'], start=1):
                message = {}
                message['filename'] = filename
                message['chunk'] = chunk
                message['chunkSize'] = 0

                socket.send(json.dumps(message)) # send the file info message
                
                response_data = connect.recv(1024)
                peerResponse = json.loads(response_data) #recieve the peer response whether it has the file

                if peerResponse['message_type'] == 'FILE_EXISTS':
                    socket.send(json.dumps({"message_type":"OK"})) #aight! send it over
                    newFile = open(chunk, 'wb')
                    data = socket.recv(1024)
                    totalRecv = len(data)
                    newFile.write(data)
                    while totalRecv < filesize: # TODO: I NEED TO KNOW THE FILE SIZE
                        data = socket.recv(1024)
                        totalRecv += len(data)
                        newFile.write(data)
                    newFile.close() # chunk download completed

                    #TODO: send message to the tracker (update the tracker with your new update info)

                #continue with another chunk asking the current owner

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
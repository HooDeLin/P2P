import socket
import threading
import os

class Talk:
    def __init__(self, settings):
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.neighbor_address = settings["neighbor-address"]
        self.neighbor_port = settings["neighbor-port"]
        self.address = settings[""]
        self.port = settings["port"]
        self.directory = settings["peer-directory"]
        print ("Socket created")

    def Upload(name, socket):
        path_directory = Path(self.directory)

        # receive the request info fileinfo["filename"], fileinfo["chunkNumber"] (array of chunk number), fileinfo["chunkSize"]
        data = socket.recv(1024)
        if data:
            fileInfoMessage = json.loads(data) 
            print 'Requesting file with the following info: ' + fileInfoMessage

            file_name = fileInfoMessage["filename"];
            chunk_number_array = fileinfo["chunkNumber"];
            chunk_size = fileInfoMessage["chunkSize"];

            for i in range(len(chunk_number_array)):
                chunk_file_name = file_name + "." + chunk_number_array[i] + ".chunk"

                if path_directory.isfile(chunk_file_name):
                    socket.send("Chunk " + chunk_number_array[i] + " exists")
                    userResponse = socket.recv(1024)
                    if userResponse[:2] == 'OK':
                        with open(file_name, 'rb') as f:
                            bytesToSend = f.read(1024)
                            socket.send(bytesToSend)

                            while bytesToSend != "":
                                bytesToSend = f.read(1024)
                                sock.send(bytesToSend)
                else:
                    sock.send("No " + "Chunk " + chunk_number_array[i] + " exists")

            socket.send("Done Upload")

    def Download():

    def listen_for_request():
        # neighbor_addr = (self.neighbor_address, self.neighbor_port)
        self.listening_socket.bind("", self.port)
        
        print "listening to any incoming request"
        
        while True:
            socket, neighbor_addr = self.listening_socket.accept()
            print "neighbor connedted ip:<" + str(neighbor_addr) + ">"
            thread = threading.Thread(target=Upload, args=("Upload", socket))
            thread.start()
             
        socket.close()

    if __name__ == '__main__':
        Main()
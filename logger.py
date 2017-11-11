from constants import *
def print_starting_message():
    print(P2P_STARTING_MESSAGE)

def print_settings(settings):
    print("These are your settings: " + str(settings))

def print_socket_created_message():
    print (SOCKET_CREATED_MESSAGE)

def print_socket_error_message(msg):
    print ('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])

def print_socket_bind_message():
    print ('Socket bind complete')

def print_not_yet_implemented_message():
    print ("Not yet implemented")

def print_tracker_stopping_message():
    print ("Stopping tracker")

def print_received_data(data):
    print ('Received data: ' + str(data))

def print_returning_data(data):
    print ('Returning data: ' + str(return_data))

def print_peer_stopping_message():
    print ("Stopping peer")

def print_available_files(filenames):
    print ("These are the available files on the network: ")
    for idx, filename in enumerate(filenames, start=1):
        print ("{}: {}".format(idx, filename))

def print_setup_signal_message(tracker_address, tracker_signal_port):
    print ("Sending bogus packet for tracker: " + tracker_address + ":" + str(tracker_signal_port))

def print_invalid_command(msg):
    print(msg)
    print("Invalid command")

def print_provide_filename():
    print("Please provide a filename")

def print_peer_tui():
    print(TUI_STARTING_MESSAGE)

# def print_peer_tui_start():
#     print("# > ", end="")

def print_peer_exiting():
    print("Exiting...")

def print_symmetric_nat_message():
    print("You are using Symmetric NAT, not handling that")

def print_hole_punching_message(tracker=False):
    if tracker:
        print("Punching a hole...")
    else:
        print("Punching a hole for tracker signal...")

def print_hole_punch_result(ip, port):
    print("Hole punched: Your IP is " + str(ip) + " and your port number is " + str(port))

def print_peer_behind_nat_message():
    print("Peer is behind NAT...")

def print_receive_signal_message():
    print("Received request file chunk signal")

def print_file_exists():
    print("File already exists in your directory")

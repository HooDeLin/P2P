# Standard Debug/Error Messages
P2P_STARTING_MESSAGE = "Starting P2P Application..."
SETTINGS_INVALID_MESSAGE = "Settings invalid"
PORT_INVALID_MESSAGE = "Port invalid"
UNSUPPORTED_FLAG_MESSAGE = "Unsupported flag: "
DIRECTORY_DOES_NOT_EXIST_MESSAGE = "Directory does not exist"
ROLE_INVALID_MESSAGE = "Role invalid"
REGISTER_PEER_SUCCESS_MESSAGE = "Successfully registered as Peer"
REGISTER_PEER_FAILED_MESSAGE = "Unable to register as Peer. Exiting..."
UPDATE_PEER_INFO_SUCCESS_MESSAGE = "Updated info successfully"
UPDATE_PEER_INFO_FAIL_MESSAGE = "Update info unsuccessful"

# Arguments flags
ROLE_FLAG = "--role"
PORT_FLAG = "--port"
TRACKER_ADDRESS_FLAG = "--tracker-address"
TRACKER_PORT_FLAG = "--tracker-port"
PEER_DIRECTORY_FLAG = "--peer-directory"
HOLE_PUNCHING_FLAG = "--hole-punching"
SIGNAL_PORT_FLAG = "--signal-port"
TRACKER_SIGNAL_PORT_FLAG = "--tracker-signal-port"
SUPPORTED_FLAGS = [ROLE_FLAG, PORT_FLAG, TRACKER_ADDRESS_FLAG, TRACKER_PORT_FLAG, PEER_DIRECTORY_FLAG, HOLE_PUNCHING_FLAG, SIGNAL_PORT_FLAG, TRACKER_SIGNAL_PORT_FLAG]
TRACKER_ROLE_NAME = "tracker"
PEER_ROLE_NAME = "peer"

# Settings keys
SETTINGS_ROLE_KEY = "role"
SETTINGS_PORT_KEY = "port"
SETTINGS_TRACKER_ADDRESS_KEY = "tracker-address"
SETTINGS_TRACKER_PORT_KEY = "tracker-port"
SETTINGS_PEER_DIRECTORY_KEY = "peer-directory"
SETTINGS_HOLE_PUNCHING_KEY = "hole-punching"
SETTINGS_SIGNAL_PORT_KEY = "signal-port"
SETTINGS_TRACKER_SIGNAL_PORT_KEY = "tracker-signal-port"
TRACKER_SETTINGS = [SETTINGS_ROLE_KEY, SETTINGS_PORT_KEY, SETTINGS_SIGNAL_PORT_KEY]
PEER_SETTINGS = [SETTINGS_ROLE_KEY, SETTINGS_PORT_KEY, SETTINGS_TRACKER_ADDRESS_KEY, SETTINGS_TRACKER_PORT_KEY, SETTINGS_PEER_DIRECTORY_KEY, SETTINGS_SIGNAL_PORT_KEY, SETTINGS_TRACKER_SIGNAL_PORT_KEY]

# Common
SOCKET_CREATED_MESSAGE = "Socket created"

# Message formats
MESSAGE_TYPE_KEY = "message_type"
INFORM_AND_UPDATE_MESSAGE_TYPE = "INFORM_AND_UPDATE"
QUERY_LIST_OF_FILES_MESSAGE_TYPE = "QUERY_LIST_OF_FILES"
QUERY_FILE_MESSAGE_TYPE = "QUERY_FILE"
REQUEST_FILE_CHUNK_NAT_MESSAGE_TYPE = "REQUEST_FILE_CHUNK_NAT"
EXIT_MESSAGE_TYPE = "EXIT"
QUERY_FILE_ERROR_MESSAGE_TYPE = "QUERY_FILE_ERROR"
REQUEST_FILE_CHUNK_SIGNAL_MESSAGE_TYPE = "REQUEST_FILE_CHUNK_SIGNAL"
NOT_YET_IMPLEMENTED_MESSAGE_TYPE = "NOT_YET_IMPLEMENTED"
ACK_MESSAGE_TYPE = "ACK"
QUERY_LIST_OF_FILES_REPLY_MESSAGE_TYPE = "QUERY_LIST_OF_FILES_REPLY"
QUERY_FILE_REPLY_MESSAGE_TYPE = "QUERY_FILE_REPLY"
REQUEST_FILE_CHUNK_MESSAGE_TYPE = "REQUEST_FILE_CHUNK"

MSG_FILENAME_KEY = "filename"
MSG_CHECKSUM_KEY = "checksum"
MSG_CHUNKS_KEY = "chunks"
MSG_NUM_OF_CHUNKS_KEY = "num_of_chunks"
MSG_PEER_BEHIND_NAT_KEY = "peer_behind_nat"

MSG_SOURCE_IP_KEY = "source_ip"
MSG_SOURCE_PORT_KEY = "source_port"
MSG_FILES_KEY = "files"

MSG_SIGNAL_PORT_KEY = "signal_port"
MSG_OWNER_ADDRESS_KEY = "owner_address"
MSG_RECEIVER_ADDRESS_KEY = "receiver_address"
MSG_FILE_DOWNLOAD_PROCESS_ID_KEY = "file_download_process_id"
MSG_CHUNK_NUMBER_KEY = "chunk_number"
# Tracker

SYMMETRIC_NAT_TYPE = "Symmetric NAT"
CHUNK_EXTENSION = ".chunk"
CHUNKS_NEEDED = "chunks_needed"
# Peer
TUI_STARTING_MESSAGE = """
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

# P2P
CS3103 P2P Project

# Peer

## What the Peer does when joining
1. Calculate checksums of each file in `directory`. If it's not our custom extension, we treat that as a **complete file** (i.e. Peer has all the chunks). If it's in our `.chunk` format, we know that it is an incomplete file. We have to parse the set of `.chunk` files we have rather than just `md5`ing the files and report to them to the Tracker as individual files.

2. Send to Tracker the files you are willing to share, the chunk numbers for each of the files, as well as the checksum of each of these files. If it's a complete file, tell the Tracker how many chunks this file has. If it's an incomplete file, tell the Tracker which chunks of the original file you have.

## Random stuff
- Peer supplies only 1 `directory` for download and upload. Whatever you download from others **must** be shared with other peers.
- Listening socket to accept incoming connections from other Peers. Used for download requests.
- Downloading of chunks is automatic i.e. User cannot, and does not, specify who to download from.
- After a download of a chunk is successful, report to `Tracker` that you own that chunk.

## `.chunk` format
- `<file digest>.<chunk number>.chunk`
- Every time a chunk is downloaded, check if the total number of chunks have been downloaded. If yes, combine the chunks into the full file

## Text UI
- Command to query server for list of files
- Command to query server for the list of Peers having a specific file (supply the file digest, rather than file name)
- Command to inform server of quitting (supplementary to our heartbeat)

# Tracker / Server
- Will advertise to Peers the **full list of files, together with the number of chunks of each file**. Also contains the **file digest** of each of these files.
- Only tell the Peer the **list of Peers who own the file** after the Peer specifically requests for a particular file

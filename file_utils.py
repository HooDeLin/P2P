import os
import glob


def get_chunk_number_from_chunk_filename(filename):
    return int(filename.split(".")[len(filename) - 2])

def get_all_chunk_number_available(directory, filename):
    path = os.path.join(directory, filename+".*"+".chunk")
    list_of_chunks = glob.glob(path)
    return map(lambda chunk: get_chunk_number_from_chunk_filename(chunk), [chunk for chunk in list_of_chunks])

def has_file(directory, filename):
    return os.path.isfile(os.path.join(directory, filename))

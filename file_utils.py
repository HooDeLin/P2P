import os
import glob


def get_chunk_number_from_chunk_filename(filename):
	splitNames = filename.split(".")
	totalSplits = len(splitNames)
	return int(splitNames[totalSplits - 2])

def get_all_chunk_number_available(directory, filename):
    path = os.path.join(directory, filename+".*"+".chunk")
    list_of_chunks = glob.glob(path)
    return [get_chunk_number_from_chunk_filename(chunk) for chunk in list_of_chunks]

def has_file(directory, filename):
    return os.path.isfile(os.path.join(directory, filename))

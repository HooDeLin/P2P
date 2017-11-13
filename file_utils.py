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

def remove_all_associated_chunks(directory, filename):
	path = os.path.join(directory, filename+".*"+".chunk")
	for filename in glob.glob(path):
		os.remove(filename)
	return

def combine_chunks(directory, filename, num_of_keys, chunk_size):
	chunk_index = 0
	new_file_directory = os.path.join(directory, filename)
	while(chunk_index < num_of_keys):
		chunk_file_name = filename + "." + str(chunk_index) + ".chunk"
		chunk_file_directory = os.path.join(directory, chunk_file_name)

		with open(new_file_directory, 'ab') as new_file:
			with open(chunk_file_directory, 'rb') as chunk_file:
				new_file.write(chunk_file.read(chunk_size))

		chunkIndex+=1

		if(chunkIndex == num_of_keys):
			remove_all_associated_chunks(directory, filename)

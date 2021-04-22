import tkinter as tk
import io, os, sys
import errno
import requests

REQUIRED_FILES_LOCS = "required.txt"

def download(filename, onlinefile, outstream=sys.stdout):
    # download raw file and make directory if needed
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise exc
    with open(filename, "wb") as f:
        data = requests.get(onlinefile).content
        f.write(data)
    outstream.write("File {:s} downloaded to {:s}\n".format(onlinefile, filename))

def download_to_folder(required_file, location, outstream=sys.stdout):
    # download all files specified to specific location
    with io.open(required_file, "r") as rf:
        filelist = [l.strip().split("\t") for l in rf.readlines()] # should be trueloc\tdownloc
        print(filelist)
    for f, o in filelist:
        truepath = os.path.join(location, f)
        download(truepath, o, outstream=outstream)
    outstream.write("Downloaded a total of {:d} files\n".format(len(filelist)))

if __name__ == "__main__":
    download_to_folder(REQUIRED_FILES_LOCS, "test")
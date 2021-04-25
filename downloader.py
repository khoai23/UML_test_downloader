import tkinter as tk
import io, os, sys, time
import errno
import requests
import zipfile36 as zipfile
REQUIRED_FILES_LOCS = "required.txt"

GITHUB_PATTERN = "https://raw.githubusercontent.com/{:s}/master/{:s}" # first is repo, second is 
def generate_download_links(dfile, repo="khoai23/UML_test_downloader", src_dir="src", outstream=sys.stdout):
    # generate paths using the pattern specified above
    with open(dfile, "w") as df:
        filelist = []
        for root, folders, files in os.walk(src_dir):
            for f in files:
                truepath = os.path.join(root, f)
                onlinepath = GITHUB_PATTERN.format(repo, truepath.replace("\\", "/"))
                filelist.append( (truepath, onlinepath) )
        lines = ("\t".join(paths) for paths in filelist)
        df.write("\n".join(lines))
    outstream.write("{:d} Entries written to file {:s}.\n".format(len(filelist), dfile))

def download(filename, onlinefile, retry=3, wait=1.0, outstream=sys.stdout):
    # download raw file and make directory if needed
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise exc
    with open(filename, "wb") as f:
        while(retry > 0):
            try:
                data = requests.get(onlinefile).content
                retry = 0
            except Exception as e:
                retry -= 1
                if(retry == 0): # if pass n-times retries, raise the exception
                    outstream.write("Out of retries for downloading {:s} -> {:s}, exiting.".format(onlinefile, filename))
                    raise e
                else:
                    outstream.write("The last attempt failed, retries left: {:d}, waiting {:.2f} before retrying.\n".format(retry, wait))
                    outstream.write(str(e) + "\n")
                    if(wait > 0.0):
                        time.sleep(wait * 1000)
        f.write(data)
    outstream.write("File {:s} downloaded to {:s}\n".format(onlinefile, filename))

def download_to_folder(required_file, location, outstream=sys.stdout):
    # download all files specified to specific location
    with io.open(required_file, "r") as rf:
        filelist = [l.strip().split("\t") for l in rf.readlines()] # should be trueloc\tdownloc
        #print(filelist)
    for f, o in filelist:
        truepath = os.path.join(location, f)
        download(truepath, o, outstream=outstream)
    outstream.write("Downloaded a total of {:d} files\n".format(len(filelist)))

def extractZip(zf_path, extract_location, outstream=sys.stdout):
    with ZipFile(zf_path, 'r') as zf:
        zf.extractall(path=extract_location)
    outstream.write("Extracted file {:s} in directory {:s}".format(zf_path, extract_location))

if __name__ == "__main__":
    #generate_download_links(REQUIRED_FILES_LOCS)
    #download_to_folder(REQUIRED_FILES_LOCS, "test")
    download("src.zip", GITHUB_PATTERN.format("khoai23/UML_test_downloader", "src.zip"))
    
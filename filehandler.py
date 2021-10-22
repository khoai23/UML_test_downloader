import io, os, sys, time
import zipfile36 as zipfile
import shutil
import errno
import requests

GITHUB_PATTERN = "https://raw.githubusercontent.com/{:s}/master/{:s}" # first is repo, second is file location
REQUIRED_FILES_LOCS = "required.txt"
DRIVE_FILE_LOCATION = "https://drive.google.com/uc?export=download&id=1Tp7JTzelEQvlxO3KbICSO1yuEeIsriqj" # UML file on GoogleDrive.

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

def download(filepath, onlinefile, retry=3, wait=1.0, cacheloc=None, outstream=sys.stdout):
    # download raw file and make directory if needed
    if not os.path.exists(os.path.dirname(filepath)):
        try:
            os.makedirs(os.path.dirname(filepath))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise exc
                
    # if the file already exist, skip
    if(os.path.exists(filepath)):
        outstream.write("Found file {:s} already in directory.\n".format(filepath))
        return
    
    # if the file is found in cacheloc, copy over
    if(cacheloc is not None and os.path.exists(os.path.join(cacheloc, os.path.basename(filepath)))):
        cachepath = os.path.join(cacheloc, os.path.basename(filepath))
        shutil.copyfile(cachepath, filepath)
        outstream.write("Found file in cache directory, copying {:s} -> {:s}\n".format(cachepath, filepath))
        return
    
    while(retry > 0):
        try:
            response = requests.get(onlinefile)
            if(response.status_code == 200):
                data = response.content # only this get out of the function and go to f.write
                retry = 0
            elif(response.status_code == 404):
                # no file to download
                outstream.write("Request received 404 code, please recheck the online path {:s}\n.".format(onlinefile))
                return
            else:
                outstream.write("Request received unusual status code {:d}\n".format(response.status_code))
                retry -= 1
        except Exception as e:
            retry -= 1
            if(retry == 0): # if pass n-times retries, raise the exception
                outstream.write("Out of retries for downloading {:s} -> {:s}, exiting.\n".format(onlinefile, filepath))
                raise e
            else:
                outstream.write("The last attempt failed, retries left: {:d}, waiting {:.2f} before retrying.\n".format(retry, wait))
                outstream.write(str(e) + "\n")
                if(wait > 0.0):
                    time.sleep(wait * 1000)
    with open(filepath, "wb") as f:
        f.write(data)
    outstream.write("File {:s} downloaded to {:s}\n".format(onlinefile, filepath))

def download_to_folder(required_file, location, outstream=sys.stdout):
    # download all files specified to specific location
    with io.open(required_file, "r") as rf:
        filelist = [l.strip().split("\t") for l in rf.readlines()] # should be trueloc\tdownloc
        #print(filelist)
    for f, o in filelist:
        truepath = os.path.join(location, f)
        download(truepath, o, outstream=outstream)
    outstream.write("Downloaded a total of {:d} files\n".format(len(filelist)))

def extractZip(zf_path, extract_location, rollback=False, outstream=sys.stdout):
    # attempt to record the files created; if encounter an error and enabled rollback, remove all files found in the namelist
    with zipfile.ZipFile(zf_path, 'r') as zf:
        namelist = zf.namelist()
        try:
            zf.extractall(path=extract_location)
        except ValueError:
            if(rollback):
                [ os.path.exists(os.path.join(extract_location, f)) and os.remove(os.path.join(extract_location, f))
                    for f in namelist] # might be a ridiculous one liner
        #print(namelist)
    outstream.write("Extracted file {:s} in directory {:s}\n".format(zf_path, extract_location))
    return namelist

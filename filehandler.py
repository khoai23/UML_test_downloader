import io, os, sys, time
import zipfile36 as zipfile
import shutil
import errno
import requests

GITHUB_PATTERN_DEFAULT = "https://raw.githubusercontent.com/{:s}/master/{:s}" # first is repo, second is file location
GITHUB_PATTERN_LFS = "https://media.githubusercontent.com/media/{:s}/master/{:s}"
REQUIRED_FILES_LOCS = "required.txt"
DRIVE_FILE_PATTERN = "https://drive.google.com/uc?export=download&id={:s}"
DRIVE_FILE_LOCATION = "https://drive.google.com/uc?export=download&id=1Tp7JTzelEQvlxO3KbICSO1yuEeIsriqj" # UML file on GoogleDrive.
DEFAULT_REPO = "khoai23/UML_test_downloader"

def generate_download_links(dfile, repo=DEFAULT_REPO, src_dir="src", outstream=sys.stdout):
    # generate paths using the pattern specified above
    with io.open(dfile, "w") as df:
        filelist = []
        for root, folders, files in os.walk(src_dir):
            for f in files:
                truepath = os.path.join(root, f)
                onlinepath = (GITHUB_PATTERN_DEFAULT if truepath not in lfs_filelist else GITHUB_PATTERN_LFS).format(repo, truepath.replace("\\", "/"))
                filelist.append( (truepath, onlinepath) )
        lines = ("\t".join(paths) for paths in filelist)
        df.write("\n".join(lines))
    outstream.write("{:d} Entries written to file {:s}.\n".format(len(filelist), dfile))

def check_googledrive_cookie(cookies):
    for k, v in cookies.items():
        if k.startswith('download_warning'):
            return v
    return None
    
def download(filepath, onlinefile, stream=True, chunk_size=4096, retry=3, wait=1.0, cache_loc=None, progressbar=None, outstream=sys.stdout, session=None):
    # make directory if needed
    if not os.path.exists(os.path.dirname(filepath)):
        try:
            os.makedirs(os.path.dirname(filepath))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise exc
    # if specified, use session; if not, use requests
    session = session or requests
                
    # print(onlinefile, type(onlinefile), isinstance(onlinefile, tuple))
    if(isinstance(onlinefile, tuple)):
        # onlinefile can be a string or a tuple of {repo} {filepath}
        # try the lfs format first
        lfs_path = GITHUB_PATTERN_LFS.format(*onlinefile)
        response = session.get(lfs_path, allow_redirects=True, stream=stream)
        if(response.status_code == 404):
            # not lfs, use the other format
            onlinefile = GITHUB_PATTERN_DEFAULT.format(*onlinefile)
        else:
            onlinefile = lfs_path
        response.close()
        print("Chosen web path generated: {:s}".format(onlinefile))

    while(retry > 0):
        try:
            response = session.get(onlinefile, allow_redirects=True, stream=stream)
                
            if("drive.google.com" in onlinefile):
                # perform check, replacing the response with the correct token if needed
                token = check_googledrive_cookie(response.cookies)
                if(token):
                    newonlinefile = "{:s}&confirm={:s}".format(onlinefile, token)
                    outstream.write("GoogleDrive large file link detected; using token {:s}(becoming {:s})\n".format(token, newonlinefile))
                    response.close()
                    response = session.get(newonlinefile, allow_redirects=True, stream=stream)
                if("text" in response.headers["content-type"]):
                    # in some event, this return text/html page with confirm=t
                    if("scan this file for viruses." in response.text):
                        print("Google Drive virus scan detected; adding confirm=t tp to response.")
                        response.close()
                        response = session.get("{:s}&confirm=t".format(onlinefile), allow_redirects=True, stream=stream)
                    
            if(stream):
                # if not stream, the response already contain the file anyway; why bother
                # get filesize
                is_chunked = response.headers.get('transfer-encoding', '') == 'chunked' # sometime this happens with a CDN
                content_length_s = response.headers.get('content-length')
                if not is_chunked and content_length_s.isdigit():
                    correct_filesize = int(content_length_s)
                else:
                    correct_filesize = -1 # (always reset if content_length is not retrievable)
                # if the file already exist, skip
                if(os.path.exists(filepath) and os.stat(filepath).st_size == correct_filesize):
                    outstream.write("Found file {:s} already in directory with correct size, ignoring.\n".format(filepath))
                    return
                
                # if the file is found in cache_loc, copy over
                if(cache_loc is not None and os.path.exists(os.path.join(cache_loc, os.path.basename(filepath)))):
                    cachepath = os.path.join(cache_loc, os.path.basename(filepath))
                    if(os.stat(cachepath).st_size == correct_filesize):
                        shutil.copyfile(cachepath, filepath)
                        outstream.write("Found file in cache directory with correct size, copying {:s} -> {:s}\n".format(cachepath, filepath))
                        return

            # check header for content length
            if(response.status_code == 200):
                data = response.iter_content(chunk_size=chunk_size) if stream else response.content # only this get out of the function and go to f.write
                # print(response.content)
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
                outstream.write(str(type(e)) + ":" + str(e) + "\n")
                if(wait > 0.0):
                    time.sleep(wait)
    # write the received file
    with io.open(filepath, "wb") as f:
        if(stream):
            if(progressbar):
                progressbar["value"] = 0
            for chunk in data: # stream writing
                f.write(chunk)
                if(progressbar): # attempt to add % to progress value basing on the chunks downloaded
                    # print(len(chunk))
                    progressbar["value"] += float(chunk_size) / correct_filesize * 100.0
        else:
            f.write(data) # wholesale writing
    if(cache_loc is not None):
        # attempt to write a cached copy as well
        cachepath = os.path.join(cache_loc, os.path.basename(filepath))
        shutil.copyfile(filepath, cachepath)
    # close down the request once everything is done and verified.
    response.close()
        
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

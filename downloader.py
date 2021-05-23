import tkinter as tk
from tkinter import filedialog, font
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

def search_location(strvar, failvar=None, cond=None, failvalue="Select a valid location..", outstream=sys.stdout):
    # open a filedialog and select a location
    if(failvar is None):
        failvar = strvar
    directory = filedialog.askdirectory()
    if(directory is not None):
        if(cond(directory)):
            # both check passed
            strvar.set(directory)
        else:
            failvar.set(failvalue)
            outstream.write("Selected directory is invalid.\n")
    
location_cond = lambda path: os.path.isdir(os.path.join(path, "res_mod"))
def check_location(strvar, failvar=None, cond=location_cond, failvalue="Select a valid location..", outstream=sys.stdout):
    # check if location is valid using condition. If fail, set the variable to failvalue
    if(failvar is None):
        failvar = strvar
    if(not cond(strvar.get())):
        failvar.set(failvalue)
        outstream.write("Selected directory is invalid.\n")
        return False
    else:
        return True

def checkbox_frame(header, list_links, download_set=None, outstream=sys.stdout, **kwargs):
    # create a tk.Frame allowing user to check the mod they want to download.
    frame = tk.Frame(highlightbackground="black", highlightthickness=1, **kwargs)
    framelabel = tk.Label(master=frame, text=header, font=font.Font(family='Helvetica', size=14))
    framelabel.grid(column=0, row=0, columnspan=2)
    # function to handle download_set changes
    def update_set(checkvar, entry=None):
        # if checkvar is 0, remove the loc from download set; else add into the download set
        checkvar = checkvar.get()
        if(checkvar == 1):
            download_set.add(entry)
        else:
            download_set.discard(entry)
        outstream.write("Handled set with trigger {:d}, link {:s}, set result {}\n".format(checkvar, entry[1], download_set))
    
    for i, (repo, filepath, description) in enumerate(list_links):
        # build for every options
        fileloc = GITHUB_PATTERN.format(repo, requests.utils.quote(filepath))
        filename = os.path.basename(filepath)
        checkvar = tk.IntVar()
        checkbox = tk.Checkbutton(master=frame, variable=checkvar, onvalue=1, offvalue=0, command=lambda var=checkvar, entry=(filename, fileloc): update_set(var, entry=entry))
        # checkvar.trace("w", lambda *args: update_set(checkvar.get(), fileloc)) # on change value, update/remove the download_set with the fileloc
        desclabel = tk.Label(master=frame, anchor="w", text=description)
        checkbox.grid(column=0, row=i+2)
        desclabel.grid(column=1, row=i+2)
    
    return frame

def install(directoryvar, additional_set, wait=1.0, outstream=sys.stdout):
    if(not check_location(directoryvar, outstream=outstream)):
        return
    directory = directoryvar.get()
    # first, download and extract the UML base to correct location (res_mod/vernumber/)
    # download("./src.zip", GITHUB_PATTERN.format("khoai23/UML_test_downloader", "src.zip"))
    resmod_folder = os.path.join(directory, "res_mod")
    subfolders = [ os.path.basename(os.path.normpath(f.path)) for f in os.scandir(resmod_folder) if f.is_dir()]
    valid = sorted([pth for pth in subfolders if all(c in "1234567890." for c in pth)], reverse=True) # hack to search for game version
    if(len(valid) > 0):
        outstream.write("Multiple game versions found, using the highest({:s} in {})\n".format(valid[0], valid))
    UML_loc = os.path.join(resmod_folder, valid[0])
    extractZip("./src.zip", UML_loc)
    # TODO: delete the file after extraction
    # download all the data recorded in additional_set into the mods folder
    for filename, link in additional_set:
        fileloc = os.path.join(directory, "mods", valid[0], "UML", filename)
        start = time.time()
        download(fileloc, link, wait=wait)
    outstream.write("Finish installation.\n")

def read_sections_from_pkg(filepath, section_delim="\n\n", entry_delim="\n", internal_delim="\t"):
    # read a list of sections in a file. Sections have the first line being header and all next line entries.
    # conform with checkbox_frame
    with io.open(filepath, "r", encoding="utf-8") as pkgs:
        data = pkgs.read()
        sections = data.split(section_delim) if section_delim in data else [data]
        formed = [s.strip().split(entry_delim) for s in sections]
        # return (header, formatted entries) for each section
        formatted = [ (s[0], [l.strip().split(internal_delim) for l in s[1:]]) 
            for s in formed]
    return formatted

def tk_interface(title="UML_downloader", outstream=sys.stdout):
    # create an installation interface to install mod
    window = tk.Tk()
    window.title(title) 
    # entry: Install location (WoT main directory). Check by res_mod folder
    location = tk.StringVar()
    loclabel = tk.Label(master=window, text="WoT directory: ")
    locentry = tk.Entry(master=window, textvariable=location, validate="focusout", validatecommand=lambda: check_location(location, cond=location_cond) )
    locbtn = tk.Button(master=window, text="Browse", command=lambda: search_location(location, cond=location_cond, outstream=outstream))
    loclabel.grid(column=0, row=0)
    locentry.grid(column=1, row=0)
    locbtn.grid(column=2, row=0)
    # Additional mods from external source
    sections = read_sections_from_pkg("other_packages.txt")
    additional_set = set()
    for i,(header, entries) in enumerate(sections):
        adtframe = checkbox_frame(header, entries, additional_set, outstream=outstream, master=window)
        adtframe.grid(column=0, row=1+i, columnspan=4)
    # start installation btn
    instbtn = tk.Button(master=window, text="Install", command=lambda: install(location, additional_set))
    instbtn.grid(column=0, row=1+len(sections), columnspan=4)
    return window
    

if __name__ == "__main__":
    #generate_download_links(REQUIRED_FILES_LOCS)
    #download_to_folder(REQUIRED_FILES_LOCS, "test")
    # download("./src.zip", GITHUB_PATTERN.format("khoai23/UML_test_downloader", "src.zip"))
    # extractZip("./src.zip", "test")
    # make sure the online file is a link
    onlinefile = requests.utils.quote("UUP/German HTs/TheFalkonett's_UUP_Maus.wotmod")
    #download("./test.wotmod", GITHUB_PATTERN.format("TheFalkonett/UUP-Germany", onlinefile))
    window = tk_interface()
    window.mainloop()
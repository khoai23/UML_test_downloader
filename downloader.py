import tkinter as tk
from tkinter import filedialog, font
import io, os, sys, time
import requests

import filehandler
from filehandler import GITHUB_PATTERN
import cache
 
def search_location(strvar, failvar=None, cond=None, failvalue="Select a valid location..", outstream=sys.stdout):
    # open a filedialog and select a location
    if(failvar is None):
        failvar = strvar
    directory = filedialog.askdirectory()
    if(directory is not None):
        if(cond is None or cond(directory)):
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

def install(directoryvar, additional_set, cache_obj, cache_obj_path=cache.DEFAULT_CACHE, cache_loc=cache.DEFAULT_CACHE_LOC, wait=1.0, outstream=sys.stdout):
    if(not check_location(directoryvar, outstream=outstream)):
        return
    directory = directoryvar.get()
    # first, download and extract the UML base to correct location (res_mod/vernumber/)
    resmod_folder = os.path.join(directory, "res_mod")
    subfolders = [ os.path.basename(os.path.normpath(f.path)) for f in os.scandir(resmod_folder) if f.is_dir()]
    valid = sorted([pth for pth in subfolders if all(c in "1234567890." for c in pth)], reverse=True) # hack to search for game version
    if(len(valid) > 0):
        outstream.write("Multiple game versions found, using the highest({:s} in {})\n".format(valid[0], valid))
    UML_loc = os.path.join(resmod_folder, valid[0])
    #zip_loc = os.path.join(UML_loc, "src.zip")
    uml_filepath = os.path.join(cache_loc, "src.zip")
    filehandler.download(uml_filepath, GITHUB_PATTERN.format("khoai23/UML_test_downloader", "src.zip"))
    filehandler.extractZip(uml_filepath, UML_loc)
    # TODO: delete the file after extraction
    # download all the data recorded in additional_set into the mods folder
    for filename, link in additional_set:
        fileloc = os.path.join(directory, "mods", valid[0], "UML", filename)
        start = time.time()
        filehandler.download(fileloc, link, cache_loc=cache_loc, wait=wait) # check for file in specific locations as well
    # after finished installing, update the cache_obj and write it to disk
    cache_obj["WOT_location"] = directory
    cache.write_cache(cache_obj, cache_obj_path)
    # done
    outstream.write("Finish installation.\n")

def read_sections_from_pkg(filepath, section_delim="\n\n", entry_delim="\n", internal_delim="\t"):
    # read a list of sections in a file. Sections have the first line being header and all next line entries.
    # conform with checkbox_frame requirement (tuple of 3)
    with io.open(filepath, "r", encoding="utf-8") as pkgs:
        data = pkgs.read()
        sections = data.split(section_delim) if section_delim in data else [data]
        formed = [s.strip().split(entry_delim) for s in sections]
        # return (header, formatted entries) for each section
        formatted = [ (s[0], [l.strip().split(internal_delim) for l in s[1:]]) 
            for s in formed]
    return formatted
    
def control_frame(cache_obj, additional_set, cache_obj_path=cache.DEFAULT_CACHE, cache_loc=cache.DEFAULT_CACHE_LOC, master=None, outstream=sys.stdout, **kwargs):
    # create a tk.Frame concerning configurations.
    frame = tk.Frame(master=master, **kwargs)
    # the location will persists between runs if properly used
    location = tk.StringVar()
    location.set(cache_obj.get("WOT_location", ""))
    loclabel = tk.Label(master=frame, text="WoT directory: ")
    # entry: Install location (WoT main directory). Check by res_mod folder
    locentry = tk.Entry(master=frame, textvariable=location, validate="focusout", validatecommand=lambda: check_location(location, cond=location_cond) )
    locbtn = tk.Button(master=frame, text="Browse", command=lambda: search_location(location, outstream=outstream))
    loclabel.grid(column=0, row=0, sticky="w")
    locentry.grid(column=1, row=0, sticky="w")
    locbtn.grid(column=2, row=0, sticky="w")
    # Install button, receive location and all the extra packages
    instbtn = tk.Button(master=frame, text="Install", command=lambda: install(location, additional_set, cache_obj_path=cache_obj_path, cache_loc=cache_loc, outstream=outstream))
    instbtn.grid(column=0, row=2, columnspan=3)
    return frame, location

def checkbox_frame(header, list_links, download_set=None, frame_cols=2, outstream=sys.stdout, **kwargs):
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
        truerow, truecol = (i // frame_cols + 1, i % frame_cols)
        #subframe = tk.Frame(master=frame)
        #subframe.grid(column=truecol, row=truerow, sticky="w")
        # build for every options, loaded into packs
        fileloc = GITHUB_PATTERN.format(repo, requests.utils.quote(filepath))
        filename = os.path.basename(filepath)
        checkvar = tk.IntVar()
        checkbox = tk.Checkbutton(master=frame, text=description, variable=checkvar, onvalue=1, offvalue=0, command=lambda var=checkvar, entry=(filename, fileloc): update_set(var, entry=entry))
        checkbox.grid(column=truecol, row=truerow, sticky="w")
        #desclabel = tk.Label(master=subframe, anchor="w", text=description)
        #checkbox.pack(side="left")
        #desclabel.pack(side="left")
    
    return frame

def tk_interface(title="UML_downloader", pkg_path="other_packages.txt", outstream=sys.stdout):
    # create an installation interface to install mod
    window = tk.Tk()
    window.title(title)
    # try to find cached infomation
    cache_obj_path = cache.DEFAULT_CACHE
    cache_loc = cache.DEFAULT_CACHE_LOC
    cache_obj = cache.read_cache(location=cache_obj_path)
    # Config frame, handle all the settings (original location, etc.)
    additional_set = set()
    frame, location = control_frame(cache_obj, cache_obj_path=cache_obj_path, cache_loc=cache_loc, additional_set, master=window, padx=5, pady=2)
    frame.grid(column=0, row=0, columnspan=2, sticky="w")
    # Additional mods from external source
    scrollsection = tk.Canvas(master=window)
    scrollsection.grid(column=0, row=1)
    sections = read_sections_from_pkg(pkg_path)
    for i,(header, entries) in enumerate(sections):
        adtframe = checkbox_frame(header, entries, additional_set, outstream=outstream, master=scrollsection, frame_cols=3, padx=2, pady=2)
        adtframe.grid(column=0, row=i, sticky="w")
    scroller = tk.Scrollbar(master=scrollsection)
    scroller.grid(column=1, row=0, rowspan=len(sections))
    scrollsection.configure(width=50, height=50, yscrollcommand = scroller.set)
    return window
    

if __name__ == "__main__":
    window = tk_interface()
    window.mainloop()

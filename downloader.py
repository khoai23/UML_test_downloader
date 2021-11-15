import tkinter as tk
from tkinter import filedialog, font, messagebox, tix
import io, os, sys, time
import requests
import shutil
import threading

import filehandler
from filehandler import GITHUB_PATTERN, DRIVE_FILE_LOCATION
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
    
location_cond = lambda path: os.path.isdir(os.path.join(path, "res_mods"))
def check_location(strvar, failvar=None, cond=location_cond, failvalue="Select a valid location..", outstream=sys.stdout):
    # check if location is valid using condition. If fail, set the variable to failvalue
    if(failvar is None):
        failvar = strvar
    if(not cond(strvar.get())):
        failedvalue = strvar.get()
        failvar.set(failvalue)
        outstream.write("Selected directory {:s} is invalid.\n".format(failedvalue))
        return False
    else:
        return True

def install(directoryvar, additional_set, cache_obj, cache_obj_path=cache.DEFAULT_CACHE, cache_loc=cache.DEFAULT_CACHE_LOC, wait=1.0, outstream=sys.stdout):
    # check the directory again for good measure
    directory = directoryvar.get()
    if(not check_location(directoryvar, outstream=outstream)):
        messagebox.showerror(title="Wrong directory", message="Directory {:s} is not a valid WOT instance. Try again. The directory to be used is one where you can see WorldOfTank.exe in the files.".format(directory))
        return
    
    # Download and extract the UML base to correct location (res_mods/vernumber/)
    resmod_folder = os.path.join(directory, "res_mods")
    subfolders = [ os.path.basename(os.path.normpath(f.path)) for f in os.scandir(resmod_folder) if f.is_dir()]
    valid = sorted([pth for pth in subfolders if all(c in "1234567890." for c in pth)], reverse=True) # hack to search for game version
    if(len(valid) > 1):
        outstream.write("Multiple game versions found, using the highest({:s} in {})\n".format(valid[0], valid))
    elif(len(valid) == 0):
        messagebox.showerror(title="No version available", message="There is no version detected in the resmod folder (list of folder found: {}). Try play a battle or something, I dunno.".format(subfolders))
        return
    # correct location to install, correct cache zip file
    UML_loc = os.path.join(resmod_folder, valid[0])
    uml_filepath = os.path.join(cache_loc, "src.zip")
    if(cache_obj.get("use_drive_UML", 0) == 1): # Use inbuilt drive file 
        filehandler.download(uml_filepath, DRIVE_FILE_LOCATION)
    else: # use the github file
        filehandler.download(uml_filepath, GITHUB_PATTERN.format("khoai23/UML_test_downloader", "src.zip"))
    filehandler.extractZip(uml_filepath, UML_loc) # extract the file to resmod
    # delete the file after extraction. This prevent updates from being blocked by previous cached UML package
    # TODO check hash or smth
    os.remove(uml_filepath)

    # download all the supplementary mods recorded in additional_set into the mods folder
    for filename, link in additional_set:
        fileloc = os.path.join(directory, "mods", valid[0], "UML", filename)
        start = time.time()
        filehandler.download(fileloc, link, cache_loc=cache_loc, wait=wait) # check for file in specific locations as well
    # after finished installing, update the cache_obj and write it to disk
    cache_obj["WOT_location"] = directory
    cache.write_cache(cache_obj, cache_obj_path)
    # done
    messagebox.showinfo(title="Done", message="Installation complete in {:s}".format(directory))
    outstream.write("Finish installation.\n")

def remove(directoryvar, careful=False, outstream=sys.stdout):
    # removing the installed mods from the WOT instance.
    # check the directory again for good measure
    directory = directoryvar.get()
    if(not check_location(directoryvar, outstream=outstream)):
        messagebox.showerror(title="Wrong directory", message="Directory {:s} is not a valid WOT instance. Try again. The directory to be used is one where you can see WorldOfTank.exe in the files.".format(directory))
        return
    resmod_folder = os.path.join(directory, "res_mods")
    subfolders = [ os.path.basename(os.path.normpath(f.path)) for f in os.scandir(resmod_folder) if f.is_dir()]
    valid = sorted([pth for pth in subfolders if all(c in "1234567890." for c in pth)], reverse=True) # hack to search for game version
    if(len(valid) > 1):
        outstream.write("Multiple game versions found, using the highest({:s} in {})\n".format(valid[0], valid))
    elif(len(valid) == 0):
        messagebox.showerror(title="No version available", message="There is no version detected in the resmod folder (list of folder found: {}). Try play a battle or something, I dunno.".format(subfolders))

    # always remove the mods/UML folder content
    mod_dir = os.path.join(directory, "mods", valid[0], "UML")
    shutil.rmtree(mod_dir)
    if(careful):
        # remove all known injection files from `resmods`; folders are left empty
        ownmodel_dir = os.path.join(resmod_folder, valid[0], "scripts", "client", "gui", "mods", "mod_ownmodel.py")
        os.unlink(ownmodel_dir)
    else:
        # Remove every files and folder in the resmod. This may scrub other mods as well (e.g Aslain's)
        for root, dirs, files in os.walk(os.path.join(resmod_folder, valid[0])):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))
    messagebox.showinfo(title="Cleaned", message="Cleaned {:s} files from {:s} and {:s}".format("specific UML" if careful else "all", mod_dir, resmod_folder))
                

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
    # the location will persists between runs if properly cached
    location = tk.StringVar()
    location.set(cache_obj.get("WOT_location", ""))
    loclabel = tk.Label(master=frame, text="WoT directory: ")
    # entry: Install location (WoT main directory). Check by res_mods folder
    locentry = tk.Entry(master=frame, textvariable=location, validate="focusout", validatecommand=lambda: check_location(location, cond=location_cond) )
    locbtn = tk.Button(master=frame, text="Browse", command=lambda: search_location(location, outstream=outstream))
    loclabel.grid(column=0, row=0, sticky="w")
    locentry.grid(column=1, row=0, sticky="w")
    locbtn.grid(column=2, row=0, sticky="w")
    use_drive_var = tk.IntVar(cache_obj.get("use_drive_UML", 0))
    def set_use_drive_cacheobj(var=use_drive_var, **kwargs): 
        cache_obj["use_drive_UML"] = var.get()
    use_drive_checkbox = tk.Checkbutton(master=frame, text="Use inbuilt GoogleDrive file.", variable=use_drive_var, onvalue=1, offvalue=0, command=set_use_drive_cacheobj)
    use_drive_checkbox.grid(column=2, row=1, sticky="e")
    # Install button, receive location and all the extra packages
    instbtn = tk.Button(master=frame, text="Install", command=lambda: install(location, additional_set, cache_obj, cache_obj_path=cache_obj_path, cache_loc=cache_loc, outstream=outstream) )
    instbtn.grid(column=0, row=2, columnspan=2)
    # Remove button, removing UML and associating files
    rmbtn = tk.Button(master=frame, text="Remove UML", command=lambda: remove(location, outstream=outstream) )
    rmbtn.grid(column=2, row=2, columnspan=3)
    return frame, location

def checkbox_frame(master, header, list_links, download_set=None, frame_cols=2, outstream=sys.stdout, **kwargs):
    # create a tk.Frame allowing user to check the mod they want to download.
    frame = tk.Frame(master=master, highlightbackground="black", highlightthickness=1, **kwargs)
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
        link = GITHUB_PATTERN.format(repo, requests.utils.quote(filepath))
        filename = os.path.basename(filepath)
        checkvar = tk.IntVar()
        checkbox = tk.Checkbutton(master=frame, text=description, variable=checkvar, onvalue=1, offvalue=0, command=lambda var=checkvar, entry=(filename, link): update_set(var, entry=entry))
        checkbox.grid(column=truecol, row=truerow, sticky="w")
        #desclabel = tk.Label(master=subframe, anchor="w", text=description)
        #checkbox.pack(side="left")
        #desclabel.pack(side="left")
    
    return frame

def treeview_frame(master, sections, download_set=None, outstream=sys.stdout, **kwargs):
    # create a tix.CheckList nested in a frame; this should allow scrolls/selections much easier
    frame = tk.Frame(master=master, highlightbackground="red", highlightthickness=1, **kwargs)
    indicesDict = dict()
    def selectItemFn(item, idsDict=indicesDict):
        # on selection: update download_set with the item
        if(idsDict[None].getstatus(item) == "on"): # tree obj is put in key None, since I'm too lazy for writing a new class
            # add item to download_set
            download_set.add(indicesDict[item])
        else:
            download_set.discard(indicesDict[item])
        outstream.write("Handled set with trigger {:s}, link {:s}, set result {}\n".format(item, indicesDict[item][1], download_set))
        
    tree = tix.CheckList(master=frame, browsecmd=selectItemFn, width=400, height=240)
    indicesDict[None] = tree # weird hack to access the tree obj
    # adding each sections
    for section_idx, (header, entries) in enumerate(sections):
        # parent row
        section_str = "section_{:d}".format(section_idx)
        tree.hlist.add(section_str, text=header)
        # children sub rows
        for i, (repo, filepath, description) in enumerate(entries):
            item_str = "{:s}.item_{:d}".format(section_str, i)
            tree.hlist.add(item_str, text=description)
            tree.setstatus(item_str, "off")
            link = GITHUB_PATTERN.format(repo, requests.utils.quote(filepath))
            filename = os.path.basename(filepath)
            indicesDict[item_str] = (filename, link)
    tree.pack()
    # tree.autosetmode()
    # ideally the widget would handle the selection update using selectItemFn above; TODO populate entries using cache
    return frame

def progressbar_download(master, install_fn, fn_args, fn_kwargs):
    # create customized dialog that will run install function, while receiving state update
    # thread to install
    install_thread = threading.Thread(target=install_fn, args=fn_args, kwargs=fn_kwargs)
    # toplevel with progressbar and a finish button
    progress_dialog = tk.Toplevel(master=master, title="Downloading...")
    tip = tk.Label(master=progress_dialog, text="Hint: Progress bars are like women. They stall when already late,\nmaddeningly slow most of the time, and are full of lies anyway.")
    tip.grid(row=0, column=0)
    progressbar = tk.ttk.Progressbar(master=progress_dialog)
    progressbar.grid(row=1, column=0)
    finishbtn = tk.Button(master=progress_dialog, text="Finish", command=progress_dialog.exit)
    finishbtn["state"] = tk.DISABLED
    finishbtn.grid(row=2, column=0)
    # bind progressbar to self-updating function, receiving installation data from install_fn, and make finish button to clickable when done

def tk_interface(title="UML_downloader", pkg_path="other_packages.txt", use_tree=True, outstream=sys.stdout):
    # create an installation interface to install mod.
    window = tix.Tk()
    window.title(title)
    # try to find cached infomation
    cache_obj_path = cache.DEFAULT_CACHE
    cache_loc = cache.DEFAULT_CACHE_LOC
    cache_obj = cache.read_cache(location=cache_obj_path)
    # Config frame, handle all the settings (original location, etc.)
    additional_set = set()
    frame, location = control_frame(cache_obj, additional_set, cache_obj_path=cache_obj_path, cache_loc=cache_loc, master=window, padx=5, pady=2)
    frame.grid(column=0, row=0, columnspan=2, sticky="w")
    # Additional mods from external source
    sections = read_sections_from_pkg(pkg_path)
    if(use_tree):
        adtframe = treeview_frame(window, sections, additional_set, outstream=outstream)
        adtframe.grid(column=0, row=2, columnspan=2)
    else:
        scrollsection = tk.Canvas(master=window)
        scrollsection.grid(column=0, row=1)
        for i,(header, entries) in enumerate(sections):
            adtframe = checkbox_frame(scrollsection, header, entries, additional_set, outstream=outstream, frame_cols=3, padx=2, pady=2)
            adtframe.grid(column=0, row=i, sticky="w")
        scroller = tk.Scrollbar(master=scrollsection)
        scroller.grid(column=1, row=0, rowspan=len(sections))
        scrollsection.configure(width=50, height=50, yscrollcommand = scroller.set)
    return window
    

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(__file__)
    print("Application path:", application_path)
    # Attempt to load the TIX_LIBRARY to os.environ if applicable. Hardcoded atm
    tix_location_pyinstaller = os.path.join(application_path, 'tix8.4.3')
    #if(os.path.isdir(tix_location_pyinstaller)): # location found in spec
    #    print("Updating TIX location: {:s}".format(tix_location_pyinstaller))
    #    os.environ["TIX_LIBRARY"] = tix_location_pyinstaller
    window = tk_interface()
    window.mainloop()

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, font, messagebox
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

def install(directoryvar, additional_set, cache_obj, cache_obj_path=cache.DEFAULT_CACHE, cache_loc=cache.DEFAULT_CACHE_LOC, progressbar=None, progress_labelvar=None, finish_trigger_fn=None, wait=1.0, outstream=sys.stdout):
    # check the directory again for good measure
    directory = directoryvar.get()
    if(not check_location(directoryvar, outstream=outstream)):
        messagebox.showerror(title="Wrong directory", message="Directory {:s} is not a valid WOT instance. Try again. The directory to be used is one where you can see WorldOfTank.exe in the files.".format(directory))
        if(progressbar or progress_labelvar):
            finish_trigger_fn()
        return
    # progressbar, progress label and finish trigger is checked
    start = time.time()
    if(progressbar):
        progressbar.start(100) # 100ms interval
        step_size = 400 / (len(additional_set) + 1)

    # Download and extract the UML base to correct location (res_mod/vernumber/)
    resmod_folder = os.path.join(directory, "res_mod")
    subfolders = [ os.path.basename(os.path.normpath(f.path)) for f in os.scandir(resmod_folder) if f.is_dir()]
    valid = sorted([pth for pth in subfolders if all(c in "1234567890." for c in pth)], reverse=True) # hack to search for game version
    if(len(valid) > 1):
        outstream.write("Multiple game versions found, using the highest({:s} in {})\n".format(valid[0], valid))
    elif(len(valid) == 0):
        messagebox.showerror(title="No version available", message="There is no version detected in the resmod folder (list of folder found: {}). Try to play a battle or something, I dunno.".format(subfolders))
        return
    # correct location to install, correct cache zip file
    UML_loc = os.path.join(resmod_folder, valid[0])
    uml_filepath = os.path.join(cache_loc, "src.zip")
    if(progress_labelvar):
        progress_labelvar.set("Downloading and extracting main UML file...")
    if(cache_obj.get("use_drive_UML", 0) == 1): # Use inbuilt drive file 
        filehandler.download(uml_filepath, DRIVE_FILE_LOCATION)
    else: # use the github file
        filehandler.download(uml_filepath, GITHUB_PATTERN.format("khoai23/UML_test_downloader", "src.zip"))
    filehandler.extractZip(uml_filepath, UML_loc) # extract the file to resmod
    # delete the file after extraction. This prevent updates from being blocked by previous cached UML package
    # TODO check hash or smth
    os.remove(uml_filepath)
    outstream.write("Base UML installed to {:s}\n".format(UML_loc))
    if(progressbar):
        progressbar["value"] = step_size 

    # download all the supplementary mods recorded in additional_set into the mods folder
    for i, (filename, link) in enumerate(additional_set):
        fileloc = os.path.join(directory, "mods", valid[0], "UML", filename)
        if(progress_labelvar):
            progress_labelvar.set("Downloading {:s} from {:s} to location {:s}...".format(filename, link, fileloc))
        filehandler.download(fileloc, link, cache_loc=cache_loc, wait=wait) # check for file in specific locations as well
        if(progressbar):
            progressbar["value"] = step_size * (i+1)
        outstream.write("Installed mod {:s} to {:s}.\n".format(filename, fileloc))
    # after finished installing, update the cache_obj and write it to disk
    cache_obj["WOT_location"] = directory
    cache.write_cache(cache_obj, cache_obj_path)
    # done
    if(progressbar or progress_labelvar): # if there are a progressbar in another thread, run its complete 
        if(callable(finish_trigger_fn)):
            finish_trigger_fn()
    else: # create a simple infobox
        messagebox.showinfo(title="Done", message="Installation complete in {:s}".format(directory))
    outstream.write("Finish installation.\n")

def remove(directoryvar, cache_loc=cache.DEFAULT_CACHE_LOC, careful=False, outstream=sys.stdout):
    # removing the installed mods from the WOT instance.
    # check the directory again for good measure
    directory = directoryvar.get()
    if(not check_location(directoryvar, outstream=outstream)):
        messagebox.showerror(title="Wrong directory", message="Directory {:s} is not a valid WOT instance. Try again. The directory to be used is one where you can see WorldOfTank.exe in the files.".format(directory))
        return
    resmod_folder = os.path.join(directory, "res_mod")
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

    # wipe the cache. TODO selectively
    cache.remove_cache(cache_loc)
    # message
    messagebox.showinfo(title="Cleaned", message="Cleaned {:s} files from {:s} and {:s}".format("specific UML" if careful else "all", mod_dir, resmod_dir))
                

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
    # entry: Install location (WoT main directory). Check by res_mod folder
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
    # instbtn = tk.Button(master=frame, text="Install", command=lambda: install(location, additional_set, cache_obj, cache_obj_path=cache_obj_path, cache_loc=cache_loc, outstream=outstream) )
    instbtn = tk.Button(master=frame, text="Install", command=lambda: progressbar_download(master, install, location, additional_set, cache_obj, cache_obj_path=cache_obj_path, cache_loc=cache_loc, outstream=outstream) )
    instbtn.grid(column=0, row=2, columnspan=2)
    # Remove button, removing UML and associating files
    rmbtn = tk.Button(master=frame, text="Remove UML", command=lambda: remove(location, cache_loc=cache_loc, outstream=outstream) )
    rmbtn.grid(column=2, row=2, columnspan=3)
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

def progressbar_download(master, install_fn, *fn_args, **fn_kwargs):
    # toplevel with progressbar and a finish button
    progress_dialog = tk.Toplevel(master=master)
    progress_dialog.title("Downloading...")
    tip = tk.Label(master=progress_dialog, text="Hint: Progress bars are like women. They stall when already late,\nmaddeningly slow most of the time, and are full of lies anyway.")
    tip.grid(row=0, column=0)
    progressbar = tk.ttk.Progressbar(master=progress_dialog, length=400)
    progressbar.grid(row=1, column=0)
    progress_labelvar = tk.StringVar(progress_dialog, value="Starting...")
    progress_label = tk.Label(master=progress_dialog, textvariable=progress_labelvar)
    progress_label.grid(row=2, column=0)
    finishbtn = tk.Button(master=progress_dialog, text="Finish", command=lambda: progress_dialog.destroy())
    finishbtn["state"] = tk.DISABLED
    finishbtn.grid(row=3, column=0)
    def enable_finish_btn():
        finishbtn["state"] = tk.ENABLED
    # create customized dialog that will run install function, while receiving state update
    # thread to install
    fn_kwargs["progressbar"] = progressbar
    fn_kwargs["progress_labelvar"] = progress_labelvar
    fn_kwargs["finish_trigger_fn"] = enable_finish_btn
    install_thread = threading.Thread(target=install_fn, args=fn_args, kwargs=fn_kwargs)
    # bind progressbar to self-updating function, receiving installation data from install_fn, and make finish button to clickable when done
    def progressbar_repeat(next_fn=None):
        # add a certain amount of progress to the progressbar
        if(progressbar["value"] <= 400 - 1):
            progressbar["value"] += 0.05
        else:
            return
        time.sleep(0.5 * 1000)
        callable(next_fn) and next_fn()
    repeat_thread = threading.Thread(target=progressbar_repeat, kwargs={"next_fn": progressbar_repeat})
    # get going
    install_thread.start()
    repeat_thread.start()

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
    frame, location = control_frame(cache_obj, additional_set, cache_obj_path=cache_obj_path, cache_loc=cache_loc, master=window, padx=5, pady=2)
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

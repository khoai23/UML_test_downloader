import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, font, messagebox, tix
from tkinter.constants import *
import io, os, sys, time
import requests
import shutil
import threading

import filehandler
from filehandler import GITHUB_PATTERN_DEFAULT, DRIVE_FILE_LOCATION, DEFAULT_REPO
import cache
from cache import SEPARATOR
from catalog_maker import read_sections_from_pkg
 
def search_location(strvar, failvar=None, cond=None, failvalue="Select a valid location..", outstream=sys.stdout):
    # open a filedialog and select a location
    if(failvar is None):
        failvar = strvar
    directory = filedialog.askdirectory(initialdir=None if not os.path.isdir(strvar.get()) else strvar.get())
    if(directory is not None and directory != ""):
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

def install(directoryvar, additional_set, cache_obj, cache_obj_path=cache.DEFAULT_CACHE, cache_loc=cache.DEFAULT_CACHE_LOC, progressbar=None, progress_labelvar=None, finish_trigger_fn=None, wait=1.0, outstream=sys.stdout):
    # check the directory again for good measure
    directory = directoryvar.get()
    if(not check_location(directoryvar, outstream=outstream)):
        messagebox.showerror(title="Wrong directory", message="Directory {:s} is not a valid WOT instance. Try again. The directory to be used is one where you can see WorldOfTank.exe in the files.".format(directory))
        if(progressbar or progress_labelvar): # if wrong directory, immediately enable exit
            progress_labelvar.set("Error found. Exit, and try again or check your version.")
            finish_trigger_fn(False)
        return
    # make certain cache_loc
    if(isinstance(cache_loc, tk.StringVar)):
        cache_loc = cache_loc.get()
    # progressbar, progress label and finish trigger is checked
    start = time.time()
    #if(progressbar):
        #progressbar.start(100) # 100ms interval
        # step_size = 400 / (len(additional_set) + 1)

    session = requests.Session()
    # Download and extract the UML base to correct location (res_mod/vernumber/)
    resmod_folder = os.path.join(directory, "res_mods")
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
        filehandler.download(uml_filepath, DRIVE_FILE_LOCATION, progressbar=progressbar, session=session)
    else: # use the github file
        filehandler.download(uml_filepath, GITHUB_PATTERN_DEFAULT.format("khoai23/UML_test_downloader", "src.zip"), progressbar=progressbar)
    filehandler.extractZip(uml_filepath, UML_loc) # extract the file to resmod
    # delete the file after extraction. This prevent updates from being blocked by previous cached UML package
    # not needed this time as we check filesize
    # os.remove(uml_filepath)
    outstream.write("Base UML installed to {:s}\n".format(UML_loc))
    
    # if selected, attempt to find and copy old ownModel.xml from other valid directoryvar
    if(cache_obj.get("copy_ownModel", 0) == 1):
        new_ownmodel_filepath = os.path.join(UML_loc, "scripts", "client", "mods", "ownModel.xml")
        copied = False
        for oldversion in valid[1:]: # go back from the latest version
            ownmodel_filepath = os.path.join(resmod_folder, oldversion, "scripts", "client", "mods", "ownModel.xml")
            if(os.path.isfile(ownmodel_filepath)):
                shutil.copyfile(ownmodel_filepath, new_ownmodel_filepath)
                outstream.write("Found ownModel.xml at {:s}, copied to {:s}".format(oldversion, ownmodel_filepath))
                copied = True
                break
        if(not copied):
            outstream.write("Did not find any ownModel.xml on older directories. Continuing.")

    # download all the supplementary mods recorded in additional_set into the mods folder
    for i, (filename, link) in enumerate(additional_set):
        fileloc = os.path.join(directory, "mods", valid[0], "UML", filename)
        if(progress_labelvar):
            progress_labelvar.set("Downloading {:s} from {} to location {:s}...".format(filename, link, fileloc))
        filehandler.download(fileloc, link, stream=True, cache_loc=cache_loc, wait=wait, progressbar=progressbar, session=session) # check for file in specific locations as well
        outstream.write("Installed mod {:s} to {:s}.\n".format(filename, fileloc))
    # after finished installing, update the cache_obj and write it to disk
    cache_obj["WOT_location"] = directory
    cache_obj["mods"] = [name for name, link in additional_set]
    cache.write_cache(cache_obj, cache_obj_path)
    # done
    session.close()
    if(progressbar or progress_labelvar): # if there are a progressbar in another thread, run its complete 
        if(callable(finish_trigger_fn)):
            progress_labelvar.set("Everything finished.")
            finish_trigger_fn(True)
    else: # create a simple infobox
        messagebox.showinfo(title="Done", message="Installation complete in {:s}".format(directory))
    
    outstream.write("Finish installation.\n")

def remove(directoryvar, careful=False, outstream=sys.stdout):
    # removing the installed mods from the WOT instance.
    # check the directory again for good measure
    directory = directoryvar.get()
    if(not check_location(directoryvar, outstream=outstream)):
        messagebox.showerror(title="Wrong directory", message="Directory {:s} is not a valid WOT instance. Try again. The directory to be used is one where you can see WorldOfTank.exe in the files.".format(directory))
        return
    if(isinstance(careful, tk.IntVar())):
        careful = careful.get() == 1
    resmod_folder = os.path.join(directory, "res_mods")
    subfolders = [ os.path.basename(os.path.normpath(f.path)) for f in os.scandir(resmod_folder) if f.is_dir()]
    valid = sorted([pth for pth in subfolders if all(c in "1234567890." for c in pth)], reverse=True) # hack to search for game version
    if(len(valid) > 1):
        outstream.write("Multiple game versions found, using the highest({:s} in {})\n".format(valid[0], valid))
    elif(len(valid) == 0):
        messagebox.showerror(title="No version available", message="There is no version detected in the resmod folder (list of folder found: {}). Try play a battle or something, I dunno.".format(subfolders))

    # always remove the mods/UML folder content
    mod_dir = os.path.join(directory, "mods", valid[0], "UML")
    shutil.rmtree(mod_dir, ignore_errors=True)
    if(careful):
        # remove all known injection files from `resmods`; additional resources are left as-is
        ownmodel_dir = os.path.join(resmod_folder, valid[0], "scripts", "client", "gui", "mods", "mod_ownmodel.py")
        os.unlink(ownmodel_dir)
    else:
        # Remove every files and folder in the resmod. This may scrub other mods as well (e.g Aslain's)
        for root, dirs, files in os.walk(os.path.join(resmod_folder, valid[0])):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))
    # message
    messagebox.showinfo(title="Cleaned", message="Cleaned {:s} files from {:s} and {:s}".format("specific UML" if careful else "all", mod_dir, resmod_folder))
                
    
def control_frame(cache_obj, additional_set, update_sections_fn=None, cache_obj_path=cache.DEFAULT_CACHE, cache_loc=cache.DEFAULT_CACHE_LOC, master=None, outstream=sys.stdout, **kwargs):
    # create a tk.Frame concerning configurations.
    frame = tk.Frame(master=master, **kwargs)
    
    # the location will persists between runs if properly cached
    location = tk.StringVar()
    location.set(cache_obj.get("WOT_location", ""))
    loclabel = tk.Label(master=frame, text="WoT directory: ")
    # entry: Install location (WoT main directory). Check by res_mods folder
    locentry = tk.Entry(master=frame, textvariable=location, validate="focusout", validatecommand=lambda: check_location(location, cond=location_cond) )
    locbtn = tk.Button(master=frame, text="Browse", command=lambda: search_location(location, cond=location_cond, outstream=outstream))
    loclabel.grid(column=0, row=0, sticky="w")
    locentry.grid(column=1, row=0, sticky="w")
    locbtn.grid(column=2, row=0)
    
    # mod filecache can also be modified here. Cache obj path is NOT changed; as it must persist between runs
    cachelocation = tk.StringVar()
    cachelabel = tk.Label(master=frame, text="Cache location: ")
    cache_obj["cache_dir"] = cache_obj.get("cache_dir", cache_loc)
    cachelocation.set(cache_obj["cache_dir"])
    def set_cachelocation(location_str):
        cache_obj["cache_dir"] = location_str
        return True
    def verify_cache_clear():
        message = "You are about to delete all cached wotmod file. {:s} Proceed?".format("This will also delete all saved settings if you do not install." if cache_obj["cache_dir"] == os.path.dirname(cache_obj_path) else "")
        result = messagebox.askyesnocancel(title="Wipe cache", message=message)
        if(result):
            # proceed with clearance
            cache.remove_cache(cache_obj["cache_dir"])
    cacheentry = tk.Entry(master=frame, textvariable=cachelocation, validate="focusout", validatecommand=lambda: os.path.isdir(cachelocation.get()))
    cachebtn = tk.Button(master=frame, text="Change", command=lambda: search_location(cachelocation, cond=set_cachelocation, outstream=outstream))
    clearcachebtn = tk.Button(master=frame, text="Wipe cache", command=verify_cache_clear)
    cachelabel.grid(column=0, row=1, sticky="w")
    cacheentry.grid(column=1, row=1, sticky="w")
    cachebtn.grid(column=2, row=1)
    clearcachebtn.grid(column=3, row=1, sticky="e")
    
    copy_ownModel_var = tk.IntVar(master=frame, value=cache_obj.get("copy_ownModel", 0))
    def set_copy_ownModel_cacheobj(var=copy_ownModel_var, **kwargs): 
        cache_obj["copy_ownModel"] = var.get()
    copy_ownModel_checkbox = tk.Checkbutton(master=frame, text="Copy old ownModel.xml", variable=copy_ownModel_var, onvalue=1, offvalue=0, command=set_copy_ownModel_cacheobj)
    copy_ownModel_checkbox.grid(column=0, row=2, columnspan=2, sticky="e")
    use_drive_var = tk.IntVar(master=frame, value=cache_obj.get("use_drive_UML", 0))
    def set_use_drive_cacheobj(var=use_drive_var, **kwargs): 
        cache_obj["use_drive_UML"] = var.get()
    use_drive_checkbox = tk.Checkbutton(master=frame, text="Use GoogleDrive file.", variable=use_drive_var, onvalue=1, offvalue=0, command=set_use_drive_cacheobj)
    use_drive_checkbox.grid(column=2, row=2, sticky="w")
    # Install button, receive location and all the extra packages
    # instbtn = tk.Button(master=frame, text="Install", command=lambda: install(location, additional_set, cache_obj, cache_obj_path=cache_obj_path, cache_loc=cache_loc, outstream=outstream) )
    instbtn = tk.Button(master=frame, text="Install", command=lambda: progressbar_download(master, install, location, additional_set, cache_obj, cache_obj_path=cache_obj_path, cache_loc=cachelocation, outstream=outstream) )
    instbtn.grid(column=0, row=3)
    upstbtn = tk.Button(master=frame, text="Update Sections", command=update_sections_fn)
    upstbtn.grid(column=1, row=3)
    # Remove button, removing UML and associating files
    rmbtn = tk.Button(master=frame, text="Remove UML", command=lambda: remove(location, outstream=outstream) )
    rmbtn.grid(column=2, row=3, columnspan=3)
    
    return frame, location

def treeview_frame(master, sections, download_set=None, outstream=sys.stdout, cache_obj=None, **kwargs):
    # create a tix.CheckList nested in a frame; this should allow scrolls/selections much easier
    frame = tk.Frame(master=master, highlightbackground="red", highlightthickness=1, **kwargs)
    indicesDict = dict()
    def selectItemFn(item, idsDict=indicesDict):
        # on selection: update download_set with the item
        if(idsDict[None].getstatus(item) == "on"): # tree obj is put in key None, since I'm too lazy for writing a new class
            # add item to download_set
            download_set.add(indicesDict[item])
        elif(idsDict[None].getstatus(item) == "off"):
            download_set.discard(indicesDict[item])
        else: # none state when clicking parents
            # print(idsDict[None].getstatus(item))
            return
        outstream.write("Handled set with trigger {:s}, link {}, set result {}\n".format(item, indicesDict[item][1], download_set))
        
    tree = tix.CheckList(master=frame, browsecmd=selectItemFn, width=400, height=240)
    indicesDict[None] = tree # weird hack to access the tree obj
    # adding each sections
    for section_idx, (header, entries) in enumerate(sections):
        # parent row
        section_str = "section_{:d}".format(section_idx)
        tree.hlist.add(section_str, text=header)
        # children sub rows
        for i, (description, repo, filepath) in enumerate(entries):
            if(repo is not None): # github format which is (repo, filepath)
                filename = os.path.basename(filepath)
                link = (repo, requests.utils.quote(filepath))
            else: # googledrive format which is (None, filename{cache.SEPARATOR}link)
                filename, link = filepath.split(SEPARATOR)
            item_str = "{:s}.item_{:d}".format(section_str, i)
            tree.hlist.add(item_str, text=description)
            if(filename in cache_obj.get("mods", set())):
                itemcheck_status = "on" # if downloaded in the past, should have a name in cache set
                download_set.add((filename, link)) # also add to the set
            else:
                itemcheck_status = "off"
            tree.setstatus(item_str, itemcheck_status)
            indicesDict[item_str] = (filename, link)
    tree.pack()
    # tree.autosetmode()
    # ideally the widget would handle the selection update using selectItemFn above; TODO populate entries using cache
    return frame

def progressbar_download(master, install_fn, *fn_args, **fn_kwargs):
    # create customized dialog that will run install function, while receiving state update
    # thread to install
    # install_thread = threading.Thread(target=install_fn, args=fn_args, kwargs=fn_kwargs)
    # toplevel with progressbar and a finish button
    progress_dialog = tk.Toplevel(master=master)
    progress_dialog.title("Downloading...")
    tip = tk.Label(master=progress_dialog, text="Hint: Progress bars are like women. They stall when already late, maddeningly slow most of the time, and are full of lies anyway.", wraplength=400.0)
    tip.grid(row=0, column=0)
    progressbar = tk.ttk.Progressbar(master=progress_dialog, length=400.0, mode='determinate')
    progressbar.grid(row=1, column=0)
    progress_labelvar = tk.StringVar(progress_dialog, value="Starting...")
    progress_label = tk.Label(master=progress_dialog, textvariable=progress_labelvar, wraplength=400.0)
    progress_label.grid(row=2, column=0)
    finishbtn = tk.Button(master=progress_dialog, text="Finish", command=lambda: progress_dialog.destroy())
    finishbtn["state"] = DISABLED
    finishbtn.grid(row=3, column=0)
    def enable_finish_btn(state=True):
        finishbtn["state"] = NORMAL
        if(not state):
            # premature exit (error), immediately close down the dialog as well
            progress_dialog.destroy()
    # create customized dialog that will run install function, while receiving state update
    # thread to install
    fn_kwargs["progressbar"] = progressbar
    fn_kwargs["progress_labelvar"] = progress_labelvar
    fn_kwargs["finish_trigger_fn"] = enable_finish_btn
    install_thread = threading.Thread(target=install_fn, daemon=True, args=fn_args, kwargs=fn_kwargs)
    # bind progressbar to self-updating function, receiving installation data from install_fn, and make finish button to clickable when done
    def progressbar_repeat(next_fn=None):
        # add a certain amount of progress to the progressbar
        if(progressbar["value"] <= 400 - 1):
            progressbar["value"] += 0.05
        else:
            return
        time.sleep(0.5 * 1000)
        callable(next_fn) and next_fn()
    # repeat_thread = threading.Thread(target=progressbar_repeat, kwargs={"next_fn": progressbar_repeat})
    # get going
    install_thread.start()
    # disable root window interaction during install
    master.wait_window(progress_dialog)
    # repeat_thread.start()

def tk_interface(title="UML_downloader", pkg_path="packages/other_packages.txt", outstream=sys.stdout):
    # create an installation interface to install mod.
    window = tix.Tk()
    window.title(title)
    # create the correct pkg_path depending on pyinstaller mode
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(__file__)
    local_pkg_path = os.path.join(application_path, pkg_path)
    # try to find cached infomation
    cache_obj_path = cache.DEFAULT_CACHE
    cache_loc = cache.DEFAULT_CACHE_LOC
    cache_obj = cache.read_cache(location=cache_obj_path)
    cached_pkg_path = os.path.join(cache_obj.get("cache_dir", cache_loc), pkg_path)
    # the set used to update data
    additional_set = set()
    keeper = {"updated": False}
    # update section function
    def update_sections():
        if(not keeper["updated"]): # this to prevent redundant multiple download. TODO disable the button instead
            link = GITHUB_PATTERN_DEFAULT.format(DEFAULT_REPO, pkg_path)
            filehandler.download(cached_pkg_path, link, stream=False, outstream=outstream)
            keeper["updated"] = True
        else:
            return
        sections = read_sections_from_pkg(cached_pkg_path)
        keeper["adtframe"].destroy()
        keeper["adtframe"] = adtframe = treeview_frame(window, sections, additional_set, cache_obj=cache_obj, outstream=outstream)
        adtframe.grid(column=0, row=2, columnspan=2)
    # Config frame, handle all the settings (original location, etc.)
    frame, location = control_frame(cache_obj, additional_set, update_sections_fn=update_sections, cache_obj_path=cache_obj_path, cache_loc=cache_loc, master=window, padx=5, pady=2)
    frame.grid(column=0, row=0, columnspan=2, sticky="w")
    # Additional mods from external source
    sections = read_sections_from_pkg(cached_pkg_path if os.path.isfile(cached_pkg_path) else local_pkg_path)
    keeper["adtframe"] = adtframe = treeview_frame(window, sections, additional_set, cache_obj=cache_obj, outstream=outstream)
    adtframe.grid(column=0, row=2, columnspan=2)
    return window
    

if __name__ == "__main__":
    # print("Application path:", application_path)
    window = tk_interface(pkg_path="packages/packages.json")
    window.mainloop()
    

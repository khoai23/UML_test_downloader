import re, io, os
import json
import sys

from cache import SEPARATOR

# two versions: https and git@
repo_regex = re.compile(r"(https://github.com/|git@github.com:)(.+).git")

def read_submodules(submodule_file=".gitmodules"):
    # Read and convert all submodule
    with io.open(submodule_file, "r", encoding="utf-8") as sf:
        lines = sf.readlines()
    
    substitute = dict()
    for i in range(0, len(lines), 3):
        # load blocks, read the repo and respective path into dicts
        _, pathline, urlline = lines[i:i+3]
        path = pathline.split("=")[-1].strip()
        repo = re.search(repo_regex, urlline).group(2)
        # path should be sanctioned as well
        path = os.path.relpath(path)
        substitute[path] = repo
    return substitute


def walk_folder(folder_path, extension=".wotmod", repo="khoai23/UML_test_downloader", substitute=None):
    # walk through the entire folder, creating tuples of (repo, location). 
    # If exist path that is in submodules, replace the current repo with the submodule repo and fix the paths accordingly.
    data = []
    for root, folders, files in os.walk(folder_path):
        viable_files = [f for f in files if os.path.splitext(f)[-1] == extension]
        relpath_files = [os.path.relpath(os.path.join(root, f)) for f in viable_files]
        for rf in relpath_files:
            cur_repo = repo
            if(substitute is not None):
                # attempt to replace repo path if detected submodules
                if(any(subpath == rf[:len(subpath)] for subpath in substitute.keys())):
                    # found match at base (we are going to run this in root)
                    subpath = next(sp for sp in substitute.keys() if sp == rf[:len(sp)])
                    cur_repo, rf = substitute[subpath], os.path.relpath(rf, subpath)
            # window paths use backslash while URL as we want use forwardslash
            rf = rf.replace("\\", "/")
            # regardless of replacing or not, put into data
            data.append( (cur_repo, rf) )
    return data
    
def export_sections_to_txt(data, txtfile="other_packages.txt"):
    # TODO open wotmod file and add proper description
    # Organize base on cue
    UUP_desc = "Falkonett UUP Project" # UUP repo
    UUP_sections = [entry for entry in data if "UUP" in entry[0]] 
    data = [entry for entry in data if entry not in UUP_sections] 
    # generate description: [UUP] {vehicle name}
    descmaker = lambda path: "[UUP] {:s}".format( path.split("/")[-1].replace(".wotmod", "").replace("_", " ").replace("TheFalkonett's UUP ", "").strip() )
    UUP_sections = [(descmaker(path), repo, path) for repo, path in UUP_sections ]
    
    A_desc = "Atacms's UML Addon/Standalone" # Atacms models
    A_sections = [entry for entry in data if "[atacms]" in entry[1]] 
    data = [entry for entry in data if entry not in A_sections] 
    # generate description: [Atacms] {vehicle name}
    descmaker = lambda path: "[Atacms] {:s}".format( path.split("/")[-1].replace(".wotmod", "").replace("[atacms]", "").replace("_", " ").strip() )
    A_sections = [(descmaker(path), repo, path) for repo, path in A_sections ]
    
    other_desc = "Private, Unverified, etc." # all the other
    other_sections = data 
    descmaker = lambda path: "[Private] {:s}".format( path.split("/")[-1].replace(".wotmod", "").replace("_", " ").strip() )
    other_sections = [(descmaker(path), repo, path) for repo, path in other_sections ]
    
    with io.open(txtfile, "w", encoding="utf-8") as tf:
        UUP_text_section = UUP_desc + "\n" + "\n".join(["\t".join(tpl) for tpl in UUP_sections])
        A_text_section = A_desc + "\n" + "\n".join(["\t".join(tpl) for tpl in A_sections])
        other_text_section = other_desc + "\n" + "\n".join(["\t".join(tpl) for tpl in other_sections])
        tf.write("\n\n".join([UUP_text_section, A_text_section, other_text_section]))
    
def description_maker_func(path, override_dict=None, remove_phrases=[], descformat="{:s}"):
    if(override_dict and path in override_dict):
        # found override, using its description and kick it out of the dict
        return override_dict.pop(path)
    # get last basename
    basename = os.path.basename(path)
    for phr in remove_phrases:
        basename = basename.replace(phr, "")
    cleanname = basename.replace(".wotmod", "").replace("_", " ").strip()
    return descformat.format(cleanname)
    
def export_sections_to_json(data, override_datafile=None, additional_datafile=None, ignore_datafile=None, private_additional=None, jsonfile="packages.json"):
    # create override_dict from file. This dict should be formatted "path": "custom description" 
    # This will override found paths in the data with the custom descriptor
    override_dict = None
    if(override_datafile):
        with io.open(override_datafile, "r", encoding="utf-8") as jf:
            override_dict = json.load(jf)
    # create ignore_list from file. This list should contain "path" that should be ignored
    # This will stop adding entries with specific paths into the sections.
    ignore_list = None
    if(ignore_datafile):
        with io.open(ignore_datafile, "r", encoding="utf-8") as jf:
            ignore_list = json.load(jf)
    sections = {}
    uup = sections["TheFalkonett's UUP Project"] = {}
    UUP_sections = [entry for entry in data if "Falkonett" in entry[0]] 
    for repo, path in UUP_sections:
        if(ignore_list and path in ignore_list):
            continue
        uup[description_maker_func(path, override_dict=override_dict, remove_phrases=["TheFalkonett's_UUP_"])] = (repo, path)
    atacms = sections["Atacms's UML Models/Remodels"] = {}
    A_sections = [entry for entry in data if "[atacms]" in entry[1]] 
    for repo, path in A_sections:
        if(ignore_list and path in ignore_list):
            continue
        atacms[description_maker_func(path, override_dict=override_dict, remove_phrases=["[atacms]"])] = (repo, path)
    local = sections["Private, Unverified, etc."] = {}
    other_sections = [entry for entry in data if entry not in UUP_sections and entry not in A_sections]
    for repo, path in other_sections:
        if(ignore_list and path in ignore_list):
            continue
        local[description_maker_func(path, override_dict=override_dict)] = (repo, path)
    # create additional dict from file. Entries will be added directly to `other_sections`; with every entry going from "filename": ["mod_description", "mod_download_link"] to "mod_description": [None, "mod_filename{cache.SEPARATOR}mod_download_link"] so the downloader can differentiate.
    # TODO updating to other section e.g Atacms using keywords
    if(additional_datafile):
        with io.open(additional_datafile, "r", encoding="utf-8") as jf:
            additional_dict = json.load(jf)
            formatted_additional = {desc: (None, "{:s}{:s}{:s}".format(name, SEPARATOR, dlink)) for name, (desc, dlink) in additional_dict.items()}
            # split the additional downloads to correct category
            atacms_additional = {k:v for k, v in formatted_additional.items() if "[Atacms]" in k}
            atacms.update(atacms_additional)
            local_additional = {k:v for k, v in formatted_additional.items() if k not in atacms_additional.keys()}
            local.update(local_additional)
    if(private_additional):
        # private models; only available when running this file in private mode
        with io.open(private_additional, "r", encoding="utf-8") as jf:
            additional_dict = json.load(jf)
            formatted_additional = {desc: (None, "{:s}{:s}{:s}".format(name, SEPARATOR, dlink)) for name, (desc, dlink) in additional_dict.items()}
            local.update(formatted_additional)
    # print(data, uup, atacms, local)
    with io.open(jsonfile, "w", encoding="utf-8") as jf:
        json.dump(sections, jf, indent=2)

def read_sections_from_pkg(filepath, section_delim="\n\n", entry_delim="\n", internal_delim="\t"):
    if(filepath[-4:] == ".txt"):
        # read a list of sections in a file. Sections have the first line being header and all next line entries.
        # conform with checkbox_frame requirement (tuple of 3)
        with io.open(filepath, "r", encoding="utf-8") as pkgs:
            data = pkgs.read()
            sections = data.split(section_delim) if section_delim in data else [data]
            formed = [s.strip().split(entry_delim) for s in sections]
            # return (header, formatted entries) for each section
            formatted = [ (s[0], [l.strip().split(internal_delim) for l in s[1:]]) 
                for s in formed]
    elif(filepath[-5:] == ".json"):
        with io.open(filepath, "r", encoding="utf-8") as jf:
            data = json.load(jf)
            # format
            formatted = [(section_key, [(item_desc, repo_name, file_path) for item_desc, (repo_name, file_path) in item_dict.items()]) 
                            for section_key, item_dict in data.items()]
    else:
        raise ValueError("Unknown filepath type, please check: {:s}".format(filepath))
    return formatted

if __name__ == "__main__":
    private_path = additional_datafile=os.path.join("packages", "private.json") if len(sys.argv) > 1 else None
    subdict = read_submodules()
    data = walk_folder("./mods", substitute=subdict)
    export_sections_to_txt(data, os.path.join("packages", "other_packages.txt"))
    export_sections_to_json(data, override_datafile=os.path.join("packages", "override.json"),
                                ignore_datafile=os.path.join("packages", "ignore.json"),
                                additional_datafile=os.path.join("packages", "additional.json"),
                                private_additional=private_path,
                                jsonfile=os.path.join("packages", "packages.json"))
    print("Done generating package file (json/txt)")

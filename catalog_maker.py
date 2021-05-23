import re, io, os

repo_regex = re.compile(r"https://github.com/(.+).git")

def read_submodules(submodule_file=".gitmodules"):
    # Read and convert all submodule
    with io.open(submodule_file, "r", encoding="utf-8") as sf:
        lines = sf.readlines()
    
    substitute = dict()
    for i in range(0, len(lines), 3):
        # load blocks, read the repo and respective path into dicts
        _, pathline, urlline = lines[i:i+3]
        path = pathline.split("=")[-1].strip()
        repo = re.search(repo_regex, urlline).group(1)
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
    UUP_sections = [(repo, path, descmaker(path)) for repo, path in UUP_sections ]
    
    A_desc = "Atacms's UML Addon/Standalone" # Atacms models
    A_sections = [entry for entry in data if "Atacms" in entry[1]] 
    data = [entry for entry in data if entry not in A_sections] 
    # generate description: [Atacms] {vehicle name}
    descmaker = lambda path: "[Atacms] {:s}".format( path.split("/")[-1].replace(".wotmod", "").replace("[atacms]", "").replace("_", " ").strip() )
    A_sections = [(repo, path, descmaker(path)) for repo, path in A_sections ]
    
    other_desc = "Private, Unverified, etc." # all the other
    other_sections = data 
    descmaker = lambda path: "[Private] {:s}".format( path.split("/")[-1].replace(".wotmod", "").replace("_", " ").strip() )
    other_sections = [(repo, path, descmaker(path)) for repo, path in other_sections ]
    
    with io.open(txtfile, "w", encoding="utf-8") as tf:
        UUP_text_section = UUP_desc + "\n" + "\n".join(["\t".join(tpl) for tpl in UUP_sections])
        A_text_section = A_desc + "\n" + "\n".join(["\t".join(tpl) for tpl in A_sections])
        other_text_section = other_desc + "\n" + "\n".join(["\t".join(tpl) for tpl in other_sections])
        tf.write("\n\n".join([UUP_text_section, A_text_section, other_text_section]))

if __name__ == "__main__":
    subdict = read_submodules()
    data = walk_folder("./mods", substitute=subdict)
    export_sections_to_txt(data, "test/other_packages.txt")
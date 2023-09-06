import xml.etree.ElementTree as ET
import argparse
import zipfile36 as zipfile
import io, os
import json

from xml_loader import recursive_cleanText, convert_WoT_to_UML, generateValueDict

def add_suffix(filepath, suffix):
    fbase, fext = os.path.splitext(filepath)
    return fbase + suffix + fext
    
def convert_xml(inresfile, outresfile, args):
    indata = inresfile.read().decode('utf-8')
    wotTree = ET.fromstring(indata)
    with io.open(args.engine_json_file, "r") as ef, io.open(args.gun_json_file, "r") as gf:
        engine_dict, gun_dict = json.load(ef), json.load(gf)
    profileValueDict = generateValueDict(args.input, wotTree, model_name=args.profile_name, engine_dict=engine_dict, gun_dict=gun_dict)
    if(args.no_damaged_model): # do not create the destroyed model node when set
        profileValueDict.pop("chassis/destroyed", None) # 
    # print(profileValueDict)
    umlTree = convert_WoT_to_UML(wotTree, default_dict=profileValueDict, ignore_failed_copy=args.lax)
    if(args.pretty): # pretty print functions, enabled by default
        recursive_cleanText(umlTree.getroot())
        if hasattr(ET, "indent"): # only available to some later versions. Bummer.
            ET.indent(umlTree)
    outdata = ET.tostring(umlTree.getroot())
    outresfile.write(outdata)
    

class ZipFileOrFolder:
    def __init__(self, isfolder, locationOrPath, *args, **kwargs):
        if(isfolder):
            if not os.path.exists(locationOrPath):
                os.makedirs(locationOrPath)
            self._base = None
            self._location = os.path.splitext(locationOrPath)[0]
        else:
            self._base = zipfile.ZipFile(locationOrPath, *args, **kwargs)
            self._location = None
    
    def open(self, filename, mode, *args, **kwargs):
        if(self._base is not None):
            return self._base.open(filename, mode, *args, **kwargs)
        else:
            new_pathname = os.path.join(self._location, filename)
            base_folder = os.path.dirname(new_pathname)
            if not os.path.exists(base_folder):
                os.makedirs(base_folder)
            return io.open(new_pathname, mode + "b", *args, **kwargs) # mode is defaulted to rb/wb in the zipfiles
    
    def __enter__(self):
        return self
        
    def __exit__(self, type, value, traceback):
        if(self._base is not None):
            self._base.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract, convert, and rebuild .wotmod remodels to corresponding UML format.")
    parser.add_argument("input", type=str, help=".wotmod file")
    parser.add_argument("-n", "--profile_name", type=str, default=None, help="Name of the new profile. If not specified, use the filename of the .wotmod as needed")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output file. Default to (oldfilename)_UML.wotmod")
    parser.add_argument("--engine_json_file", type=str, default="engine.json", help="Reference engine file extracted from wot-src")
    parser.add_argument("--gun_json_file", type=str, default="gun.json", help="Reference gun file extracted from wot-src")
    parser.add_argument("-r", "--resource_only", action="store_true", help="Set to not create corresponding XML; useful if there are existing profiles packed with UML (e.g Mirukii's)")
    parser.add_argument("-e", "--extracted", action="store_true", help="Set to not rebuild into wotmod again. Use if you want to customize the profile.")
    parser.add_argument("--no_damaged_model", action="store_true", help="If set, do not import damaged model to the XML profile (show original vehicle's wreck)")
    parser.add_argument("--relocate_data", action="store_true", help="Set to relocate all resource file and modify .visual(_processed) accordingly . Currently unimplemented.")
    parser.add_argument("--pretty", action="store_false", help="Specify to disable default result of XML printing (no indent, no stripping values).")
    parser.add_argument("--lax", action="store_false", help="If set, do not raise error when missing nodes during xml conversion.")
    
    args = parser.parse_args()
    if(args.relocate_data):
        raise NotImplementedError
    if(args.output is None):
        args.output = add_suffix(args.input, "_UML")
    if(args.profile_name is None):
        args.profile_name = os.path.splitext(os.path.basename(args.input))[0]
    internal_UML_profile_filename = os.path.join("res", "scripts", "client", "mods", "UMLprofiles", args.profile_name + ".xml")
    # print(args, internal_UML_profile_filename)
    # open the zipfile, both input and output
    with zipfile.ZipFile(args.input, "r", compression=zipfile.ZIP_STORED) as inf, ZipFileOrFolder(args.extracted, args.output, "w", compression=zipfile.ZIP_STORED) as outf:
        # for everything not the profile, copy over
        for info in inf.infolist():
            if(info.is_dir()):
                # do nothing to directory
                pass
            elif("item_defs" not in info.filename):
                # resource file, move it over
                print("Moving " + info.filename)
                with inf.open(info.filename, "r") as inresfile, outf.open(info.filename, "w") as outresfile:
                    outresfile.write(inresfile.read())
            else:
                assert "xml" in info.filename, "Expecting an item_defs vehicle profile, but received {}".format(info.filename)
                if(args.resource_only):
                    print("Resource only mode; do not convert corresponding item_defs XML")
                    continue
                print("Converting " + info.filename)
                with inf.open(info.filename, "r") as inresfile, outf.open(internal_UML_profile_filename, "w") as outresfile:
                    convert_xml(inresfile, outresfile, args)
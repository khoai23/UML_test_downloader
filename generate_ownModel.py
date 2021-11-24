import os, io, sys
import xml.etree.ElementTree as ET
import copy
import zipfile36 as zipfile

def generate_profiles(mod_dir, outstream=sys.stdout):
    # open every mod in the `mod_dir` and look for xml profiles.
    profiles = []
    for f in os.listdir(mod_dir):
        if(f[-7:] != ".wotmod"):
            # not mod file for some reason, ignore
            continue
        try:
            with zipfile.ZipFile(os.path.join(mod_dir, f)) as zf:
    #            zipdata_bytes = io.BytesIO(zf_wotmod.read())
    #            with zipfile.ZipFile(zipdata_bytes) as zf:
                    namelist = zf.namelist()
                    for name in namelist:
                        if(name[-4:] == ".xml"):
                            outstream.write("Found a xml file in {:s} of {:s}, attempting to extract profile header(s).\n".format(name, f))
                            bytestring = zf.read(name)
                            xmltree = ET.fromstring(bytestring)[0]
                            if(xmltree.tag != "models"):
                                # is not correct format of a UML profile, ignoring.
                                continue
                            # read all children as profile headers
                            profiles.extend( (child.tag for child in xmltree) )
        except zipfile.BadZipFile:
            pass # not a zip file, ignore 
    return profiles

def read_ownModel_file(ownmodel_dir):
    # return the tree hierarchy from ownModel file
    if(os.path.isfile(ownmodel_dir)):
        return ET.parse(ownmodel_dir)
    else:
        return None

DEFAULT_ATTRIB_PROFILE = (ET.Element("enabled"), ET.Element("swapNPC"), ET.Element("useWhitelist"), ET.Element("whitelist"))
DEFAULT_ATTRIB_PROFILE[0].text, DEFAULT_ATTRIB_PROFILE[1].text, DEFAULT_ATTRIB_PROFILE[2].text, DEFAULT_ATTRIB_PROFILE[3].text = "false", "false", "true", "dummy1, dummy2"

def generate_ownModel(base_vehicles, extra_vehicles, mod_profiles, default_attribs={}):
    # Under construction. 
    # raise NotImplementedError
    def buildDefaultElement(tag, children, copyChildren=True):
        element = ET.Element(tag)
        element.extend(copy.deepcopy(children) if copyChildren else children)
        return element
    ownModel_tree = ET.Element("model", attrib=default_attribs)
    ownModel_tree.extend([buildDefaultElement(pf, DEFAULT_ATTRIB_PROFILE) for pf in mod_profiles])
    ownModel_tree.extend([buildDefaultElement(ev, DEFAULT_ATTRIB_PROFILE) for ev in extra_vehicles])
    return ET.ElementTree(ownModel_tree)




if __name__ == "__main__":
    mod_dir = sys.argv[1]
    print(ET.tostring(generate_ownModel_file([], [], generate_profiles(mod_dir), None).getroot()))

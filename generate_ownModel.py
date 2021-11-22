import os, io, sys
import xml.etree.ElementTree as ET
import zipfile

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
                            xmltree = ET.fromstring(bytestring).root()
                            if(xmltree.tag != "model"):
                                # is not correct format of a UML profile, ignoring.
                                continue
                            # read all children as profile headers
                            profiles.extend( (child.tag for child in xmltree.children) )
        except zipfile.BadZipFile:
            pass # not a zip file, ignore 
    return profiles

def read_ownModel_file(ownmodel_dir):
    # return the tree hierarchy from ownModel file
    if(os.path.isfile(ownmodel_dir)):
        return ET.parse(ownmodel_dir)
    else:
        return None

DEFAULT_ATTRIB_PROFILE = (ET.Element("enabled", text="false"), ET.Element("swapNPC", text="false"), ET.Element("whitelist", text="dummyVehicle1, dummyVehicle2"))

def generate_ownModel_file(base_vehicles, extra_vehicles, mod_profiles, ownmodel_dir, default_attribs={}):
    # Under construction. 
    raise NotImplementedError
    def buildDefaultElement(tag, children, copy=True):
        element = ET.Element(tag=tag)
        element.extend(list(children) if copy else children)
        return element
    ownModel_tree = ET.Element(tag="model", attrib=default_attribs)
    tree.extend(buildDefaultElement(pf.tag, DEFAULT_ATTRIB_PROFILE) for pf in mod_profiles)
    tree.extend(buildDefaultElement(ev.tag, DEFAULT_ATTRIB_PROFILE) for ev in extra_vehicles)
    return ET.ElementTree(ownModel_tree, file=ownmodel_dir)


if __name__ == "__main__":
    mod_dir = sys.argv[1]
    print(generate_profiles(mod_dir))

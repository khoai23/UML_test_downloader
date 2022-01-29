### Convert all engine sounds from various engine.xml
import io, os, sys
import xml.etree.ElementTree as ET
import json

class MockElement: # a mock element to deal with none existing node while browsing (e.g gunReloadEffect)
    def __init__(self, val):
        self.text = val

if __name__ == "__main__":
    # extract engine data
    engine_data = {}
    # extract gun data 
    gun_data = {}
    item_dir = os.path.join(os.path.dirname(__file__), "wot-src", "sources", "res", "scripts", "item_defs", "vehicles")
    for root, dirs, files in os.walk(item_dir):
        for f in files:
            if "engines.xml" in f:
                xmlrootNode = ET.parse(os.path.join(item_dir, root, f)).getroot()
                xmlEngineSharedNode = next(n for n in xmlrootNode if n.tag == "shared")
                for engineNode in xmlEngineSharedNode:
                    engineName = engineNode.tag
                    engineSoundPC = next(n for n in engineNode if n.tag == "wwsoundPC").text
                    engineSoundNPC = next(n for n in engineNode if n.tag == "wwsoundNPC").text
                    engine_data[engineName] = (engineSoundPC, engineSoundNPC) # retrieve PC/NPC sound
                #print(os.path.join(item_dir, root, f))
            elif "guns.xml" in f:
                xmlrootNode = ET.parse(os.path.join(item_dir, root, f)).getroot()
                xmlGunSharedNode = next(n for n in xmlrootNode if n.tag == "shared")
                for gunNode in xmlGunSharedNode:
                    gunName = gunNode.tag
                    # print(list(gunNode))
                    gunReloadEffect = next( (n for n in gunNode if n.tag == "reloadEffect") , MockElement(None)).text
                    gunEffect = next(n for n in gunNode if n.tag == "effects").text # retrieve gun effect
                    for node in next(n for n in gunNode if n.tag == "recoil"):
                        if(node.tag == "lodDist"):
                            gLodDist = node.text.strip()
                        elif(node.tag == "amplitude"):
                            gAmpl = node.text.strip()
                        elif(node.tag == "recoilEffect"):
                            gRecoil = node.text.strip()
                        else:
                            raise ValueError("Unknown node residing in the <recoil> gun node: {}".format(node.tag))
                    gun_data[gunName] = (gunEffect, gunReloadEffect, (gLodDist, gAmpl, gRecoil))
    # print(engine_data)
    engineFilename = gunFilename = None
    try:
        engineFilename = sys.argv[1]
        gunFilename = sys.argv[2]
    except IndexError:
        print("Default engine data to engine.json and gun data to gun.json")
        engineFilename = engineFilename or "engine.json"
        gunFilename = gunFilename or "gun.json"
    with io.open(engineFilename, "w") as ef:
        json.dump(engine_data, ef)
    with io.open(gunFilename, "w") as gf:
        json.dump(gun_data, gf)
    
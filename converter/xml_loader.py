import xml.etree.ElementTree as ET
import sys, os, io
import copy
import json

def recursive_print(node, indent=""):
    print("{:s}[{:s}] {}".format(indent, node.tag, node.text.strip()))
    for c in node:
        recursive_print(c, indent=indent+"  ")

def recursive_nodename(node, prefix=None, separator="|"):
    newprefix = node.tag if prefix is None else prefix + separator + node.tag
    listnode = [newprefix]
    for c in node:
        listnode.extend(recursive_nodename(c, prefix=newprefix, separator=separator))
    return listnode

def recursive_cleanText(node, cleaner_fn=lambda x: x.strip()):
    if(node.text):
        node.text = cleaner_fn(node.text)
    for c in node:
        recursive_cleanText(c, cleaner_fn=cleaner_fn)

Convert_Tagset = {"clan",  "player", "inscription", "insigniaOnGun"}
def convertCustomizationSlots(nodes, accepted_tagset=Convert_Tagset):
    # reformat WoT customization nodes to UML format
    # only affect known nodes types - clan, player, inscription, MoE
    converted_nodes = []
    for slotNode in nodes:
        newNodeTag = next(n.text for n in slotNode if n.tag == "slotType")
        if(newNodeTag not in accepted_tagset):
            # is not a supported node (paint/camouflage), ignore
            continue
        newNode = copy.deepcopy(slotNode)
        newNode.tag = newNodeTag
        converted_nodes.append(newNode)
    # print(converted_nodes)
    return converted_nodes
    
UML_conversion_dict = {
    # UML config - static values except <whitelist> which will use default name
    "enabled": "?",
    "swapNPC": "?",
    "useWhitelist": "?",
    "whitelist": "?",
    "reference": "?",
    "playerEmblem": "?",
    # chassis section - pull directly
    "chassis/undamaged": "chassis/*/models/undamaged",
    "chassis/destroyed": "chassis/*/models/destroyed",
    "chassis/traces": "chassis/*/traces",
    "chassis/tracks": "chassis/*/tracks",
    "chassis/wheels": "chassis/*/wheels",
    "chassis/topRightCarryingPoint": "chassis/*/topRightCarryingPoint",
    "chassis/drivingWheels": "chassis/*/drivingWheels",
    "chassis/trackNodes": "chassis/*/trackNodes",
    "chassis/groundNodes": "chassis/*/groundNodes",
    "chassis/splineDesc": "chassis/*/splineDesc",
    "chassis/physicalTracks": "chassis/*/physicalTracks",
    "chassis/hullPosition": "chassis/*/hullPosition",
    "chassis/trackThickness": "chassis/*/trackThickness",
    "chassis/AODecals": "chassis/*/AODecals",
    # hull section - convert emblem/decal groups
    "hull/undamaged": "hull/models/undamaged",
    "hull/destroyed": "hull/models/destroyed",
    "hull/exhaust": "hull/exhaust",
    "hull/camouflage": "hull/camouflage",
    "hull/emblemSlots": "hull/customizationSlots[convert]",
    # turret - also convert the emblem/decal group
    "turret/undamaged": "turrets0/*/models/undamaged",
    "turret/destroyed": "turrets0/*/models/destroyed",
    "turret/emblemSlots": "turrets0/*/customizationSlots[convert]",
    "turret/camouflage": "turrets0/*/camouflage",
    # gun - convert only MoE markers, but do it using function anyway.
    "gun/undamaged": "turrets0/*/guns/*/models/undamaged",
    "gun/destroyed": "turrets0/*/guns/*/models/destroyed",
    "gun/emblemSlots": "turrets0/*/guns/*/customizationSlots[convert]",
    "gun/camouflage": "turrets0/*/guns/*/camouflage",
    "gun/effects": "?",
    "gun/reloadEffect": "?",
    "gun/recoil": "?",
    # engine - match engine sound
    "engine": "?",
    # default root camouflage
    "camouflage": "camouflage"
}

UML_backup_conversion_dict = {
    # UML backup config - some elements had been renamed; those elements can be converted directly
    "customizationSlots": "emblemSlots",
}

UML_default_dict = {
    "enabled": "false",
    "swapNPC": "false",
    "useWhitelist": "true"
}
    
def convert_WoT_to_UML(wotTree, conversion_dict=UML_conversion_dict, default_dict=UML_default_dict, ignore_failed_copy=False):
    # attempt to convert from opposite xml tree
    UML_root_node = ET.Element("root")
    models_node = ET.SubElement(UML_root_node, "models")
    UML_model_node = ET.SubElement(models_node, default_dict.get("model_name", "DEFAULT_PROFILE_NAME"))
    for sourcebranch, targetbranch in conversion_dict.items():
        # sourcebranch will always be a formatted string, so we can simply use SubElement
        truesourcepath = sourcebranch # keep the true xpath in the event of "?"
        currentNode = UML_model_node
        while("/" in sourcebranch):
            nodeTag, sourcebranch = sourcebranch.split("/", 1)
            try:
                currentNode = next(n for n in currentNode if n.tag == nodeTag) # found existing parent
            except StopIteration:
                currentNode = ET.SubElement(currentNode, nodeTag) # create new
        # by simple logic, the convertedNode must be a new node
        convertedNode = ET.SubElement(currentNode, sourcebranch)
        # navigate targetbranch manually since we have ? (use default), * (select any child), and [convert] to convert customization
        if(targetbranch == "?"):
            value = default_dict.get(truesourcepath, "#ERROR#")  # the default value SHOULD not happen once script is done 
            if(isinstance(value, str)):
                convertedNode.text = value.strip() # if string, set as single value
            elif(isinstance(value, list)):
                convertedNode.extend(value) # if list, set as parent node 
        else:
            try:
                currentNode = wotTree
                while("/" in targetbranch):
                    nodeTag, targetbranch = targetbranch.split("/", 1) # split single tag
                    if(nodeTag == "*"):
                        # get last node. TODO maybe consider different vers?
                        currentNode = currentNode[-1]
                    else:
                        # get the child node with the specific name
                        currentNode = next(n for n in currentNode if n.tag == nodeTag)
                # the last nodetag would be copied over except the one marked with [convert] (which will undergo a conversion process)
                # except for older remodels, which we can pull them over wholesale.
                if("[convert]" in targetbranch):
                    targetbranch = targetbranch.replace("[convert]", "")
                    currentNode = next(n for n in currentNode if n.tag == targetbranch)
                    convertedNode.extend(convertCustomizationSlots(currentNode))
                else:
                    currentNode = next(n for n in currentNode if n.tag == targetbranch)
                    convertedNode.extend([c for c in currentNode])
                    convertedNode.text = currentNode.text
            except StopIteration as e:
                print("StopIteration caught with known set: {} {} {}".format(currentNode, targetbranch, [n.tag for n in currentNode]))
                if(not ignore_failed_copy):
                    # setting this flag will ignore missing elements
                    raise e
    # the model node will be turned into ElementTree to be dumped
    return ET.ElementTree(UML_root_node)

emblemdicts_original = {'ussr_star': 15501, 
   'germany_cross': 15502, 
   'usa_star': 15503, 
   'french_rose': 15504, 
   'china_star': 15505, 
   'britain_color': 15506, 
   'germany_bundecross': 15507, 
   'japanese_sun': 15508, 
   'china_kuomintang': 15509, 
   'alpha_tester': 15510, 
   'beta_tester': 15511, 
   'germany_ddr': 15512, 
   'moder_ring': 15513, 
   'czech_round': 15514, 
   'swedish_flag': 15515, 
   'poland_chekers': 15516, 
   'italian_flag': 15500, 
   'poland_flag': 409, 
   'israel_flag': 424, 
   'finland_flag': 437, 
   'australia_flag': 439}
emblemdicts = {index:name for name, index in emblemdicts_original.items()}
   
def generateValueDict(modPath, wotTree, model_name=None, engine_dict=None, gun_dict=None, error_text="#ERROR#"):
    # create customized valueDict that changes depending on the input model
    profileValueDict = dict(UML_default_dict)
    # (re)model name is decided by the filename (not contained extension)
    profileValueDict["model_name"] = model_name or os.path.splitext(os.path.basename(modPath))[0]
    # default whitelist is the tag of the wotTree minus the xml
    profileValueDict["whitelist"] = wotTree.tag.replace(".xml", "")
    # reference can be whatever. right now it's a credit
    profileValueDict["reference"] = "UML profile converted from {:s} by khoai23's script.".format(modPath)
    # default emblem: access emblems/default and convert to corresponding string name
    emblemValue = wotTree.find("emblems/default").text
    try:
        emblemValue = int(emblemValue)
    except ValueError as e:
        if(emblemValue not in emblemdicts_original.keys()):
            # older version MUST use correct values listed, else kick out ValueError
            raise e
    profileValueDict["playerEmblem"] = emblemdicts.get(emblemValue, str(emblemValue))
    
    # engine: wwsoundPC and wwsoundNPC extracted from wot-src by a finder script (@engines.xml)
    if(engine_dict):
        # engineName found from wotTree
        enginesNode = wotTree.find("engines") # list of available engine
        engineName = enginesNode[-1].tag # take the last node (most modern engine)'s name
        try:
            soundPC, soundNPC = engine_dict[engineName] # look up corresponding sounds
        except KeyError as e:
            print("Issue during lookup for engineName {:s}. This may happen to outdated remodels / engine.json file.")
            raise e
        #
        profileValueDict["engine"] = pcSoundNode, npcSoundNode = [ET.Element("wwsoundPC"), ET.Element("wwsoundNPC")]
        pcSoundNode.text = soundPC
        npcSoundNode.text = soundNPC
    # gun: effects, reloadEffect, (lodDist, amplitude, recoilEffect) extracted from wot-src by a finder script (@guns.xml)
    if(gun_dict):
        # gunName found from wotTree
        turretNode = wotTree.find("turrets0")[-1] # list of available turret, take the last turret (most modern)
        gunName = turretNode.find("guns")[-1].tag # take the last node (most modern gun)'s name
        try:
            effects, reloadEffect, (lodDist, amplitude, recoilEffect) = gun_dict[gunName] # look up corresponding sounds
        except KeyError as e:
            print("Issue during lookup for gunName {:s}. This may happen to outdated remodels / gun.json file.")
            raise e
        # Construct the needed data
        profileValueDict["gun/effects"] = effects
        if(reloadEffect): # some gun does not have reloadEffect. May or may not be an issue.
            profileValueDict["gun/reloadEffect"] = reloadEffect
        profileValueDict["gun/recoil"] = rLod, rAmp, rEff = [ET.Element("lodDist"), ET.Element("amplitude"), ET.Element("recoilEffect")]
        rLod.text = lodDist; rAmp.text = amplitude; rEff.text = recoilEffect
        
    return profileValueDict

def cleanDefaultWoTProfile(text):
    # TODO the read profile will be parsed without xmlns tags
    pass

if __name__ == "__main__":
    sourcefile, targetfile = sys.argv[1:]
    wotTree = ET.parse(sourcefile).getroot() # currently not working on WoT xml due to xmlns:... element. TODO get rid of that.
    with io.open("engine.json", "r") as ef, io.open("gun.json", "r") as gf:
        engine_dict, gun_dict = json.load(ef), json.load(gf)
    profileValueDict = generateValueDict(sourcefile, wotTree, engine_dict=engine_dict, gun_dict=gun_dict)
    # print(profileValueDict)
    umlTree = convert_WoT_to_UML(wotTree, default_dict=profileValueDict)
    recursive_cleanText(umlTree.getroot())
    # ET.indent(umlTree)
    umlTree.write(targetfile)
    sys.exit(0)
    import Levenshtein as lv
    for needed in listNeededNode:
        possible = sorted( ((lv.distance(needed, p), p) for p in listPossibleNode), key=lambda x: x[0])[0]
        print("{} <= {}".format(needed, possible))

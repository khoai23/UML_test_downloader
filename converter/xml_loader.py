import xml.etree.ElementTree as ET
import sys

def recursive_print(node, indent=""):
    print("{:s}[{:s}] {}".format(indent, node.tag, node.text.strip()))
    for c in node:
        recursive_print(c, indent=indent+"  ")

UML_conversion_dict = {
  "hangarShadowTexture": "hangarShadowTexture",
  "hullPosition": 
}

if __name__ == "__main__":
    tree = ET.parse(sys.argv[1])
    root = tree.getroot()
    recursive_print(root)

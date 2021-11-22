import os, io
import json
import contextlib

if( os.getenv("APPDATA") is None or os.getenv("APPDATA") == ""):
    print("Warning: APPDATA variable is null; the cache will be written to local folder and may not persist between runs.")
    appdata_exist = False
else:
    # print("APPDATA: {:s}".format(os.getenv("APPDATA")))
    appdata_exist = True
DEFAULT_CACHE = os.path.join(os.getenv("APPDATA") if appdata_exist else "", "UML_downloader", "persistent.txt")
DEFAULT_CACHE_LOC = os.path.join(os.getenv("APPDATA") if appdata_exist else "", "UML_downloader")
SEPARATOR = "::"

def try_convert_value(rawvalue):
    # attempt to reconvert values from cache back to original
    if(rawvalue == "None"): # none
        return None
    elif(rawvalue in ("True", "False")): # bool
        return rawvalue == "True"
    else:
        try:
            value = int(rawvalue) # int
        except ValueError:
            try:
                value = float(rawvalue) # float
            except ValueError:
                value = rawvalue
        return value

def read_cache(location=DEFAULT_CACHE, separator=SEPARATOR, sanitize=True):
    try:
        with io.open(location, "r", encoding="utf-8") as cache:
            # read from txt file and dump into a dictionary; separator
            data = json.load(cache)
            # print(rawdata, data)
    except Exception as e:
        if(sanitize):
            print(e)
            # silently remove the file after outputing the error
            with contextlib.suppress(FileNotFoundError):
                os.remove(location)
        # cache do not exist / error while reading, create blank
        data = {}
    # data = {k: try_convert_value(v) for k, v in data.items()}
    return data

def write_cache(data, location=DEFAULT_CACHE, separator=SEPARATOR):
    location_dir, filename = os.path.split(location)
    # try to make the location to write
    os.makedirs(location_dir, exist_ok=True)
    # create and write data to this location
    with io.open(location, "w", encoding="utf-8") as cache:
        json.dump(data, cache)
        
def remove_cache(location=DEFAULT_CACHE):
    os.remove(location)
    os.removedirs(os.path.split(location)[0])
    

if __name__ == "__main__":
    # test read/write cache
    test = {"trash1": "random_str", "trash_2": 4, "trash_3": 22.16, "trash_4": False, "trash_5": None}
    write_cache(test, location=DEFAULT_CACHE)
    read = read_cache(location=DEFAULT_CACHE)
    print(test, "->", read)
    remove_cache(location=DEFAULT_CACHE)

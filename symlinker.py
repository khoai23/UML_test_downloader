import os, sys, ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        raise False

if __name__ == "__main__":
    print(ctypes.windll.shell32.ShellExecuteEx(None, "runas", "mklink", "test.txt requirements.txt", None, 1))
    sys.exit(0)
    if(is_admin()):
        pass
    else:
        print(sys.executable, " ".join(sys.argv))
        print(ctypes.windll.shell32.ShellExecuteEx(None, "runas", sys.executable, " ".join(sys.argv), None, 1))
    target, symlink_destination = sys.argv[1:]
    try:
        os.symlink(target, symlink_destination)
        sys.exit( 0 )
    except OSError as e:
        # insufficient privilege, copy directly
        print("OSError caught: " + str(e) + "\n")
        sys.exit( 1 )
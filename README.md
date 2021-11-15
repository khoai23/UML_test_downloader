A little program to make installing sir [atacms's UML mod](http://forum.worldoftanks.eu/index.php?/topic/457839-11000universal-model-loader-uml-change-only-the-appearance-of-your-own-tank/) a bit simpler. To compile your own version, run this from the base directory:

```
# install needed packages (tkinter might need additional apt-get or smth)
pip install -r requirements.txt
# generating catalog file
python catalog_maker.py
# generate the exe
pyinstaller downloader.py --name UML_Installer --onefile --add-data ./other_packages.txt:./other_packages.txt --add-data old_packages.txt:old_packages.txt
```

Still lack a bunch of features:
- [ ] Automatic detection of WG game location
- [x] Persistent mods between game version ~~(new version will redownload mods from github)~~ new version now keep copies in APPDATA
- [ ] Persistent mods selection between installs
- [ ] Persistent mods checking and update for outdated contents
- [ ] PyInstaller to create standalone exe
- [ ] Progressbar and Threading; Accurate progressbar relative to sizes of mods instead of by package

All credits goes to respective authors who published their own mod on github and made them compatible to UML.

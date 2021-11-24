A little program to make installing sir [atacms's UML mod](http://forum.worldoftanks.eu/index.php?/topic/457839-11000universal-model-loader-uml-change-only-the-appearance-of-your-own-tank/) a bit simpler. To compile your own version, run this from the base directory:

```
# install needed packages (tkinter might need additional apt-get or smth)
pip install -r requirements.txt
# generating catalog file
python catalog_maker.py
# generate the spec file (UML_Installer.spec)
pyi-makespec downloader.py --name UML_Installer --onefile --add-data packages;packages
# add to spec file datas ``(os.path.join(sys.prefix, 'tcl', 'tix8.4.3'), 'tix8.4.3')``, replacing 8.4.3 with whatever version applicable to your python Tkinter
pyinstaller UML_Installer.spec
```

Still lack a bunch of features:
- [ ] Automatic detection of WG game location
- [x] Persistent mods between game version ~~(new version will redownload mods from github)~~ new version now keep copies in APPDATA
- [x] Persistent mods selection between installs (check file size enabled)
- [x] Persistent mods checking and update for outdated contents (check file size enabled)
- [x] Failed download handling (check file size enabled)
- [x] PyInstaller to create standalone exe (Check on Windows)
- [x] TreeView style of catalog
- [x] Progressbar and Threading, preventing complete freeze of main window on progressbar
- [ ] Accurate progressbar relative to sizes of mods instead of by package
- [x] Copying old ownModel.xml from old directory
- [ ] Better `catalog_maker`, tooltip or image for each package.
- [ ] Query list of downloadable packages from online
- [ ] Separate the "wipe mod" option from "wipe cache" option (currently all in `Remove` button)
- [ ] Crediting proper authors

All credits goes to respective authors who published their own mod on github and made them compatible to UML.

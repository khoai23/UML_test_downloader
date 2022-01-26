### Converter Script

The point of this python script is to convert standalone remodels (replacing vehicle .xml) to UML equivalent (adding new profile to the location). To accomplish this, we will sequentially:

- Extract the original remodel .wotmod
- Find the corresponding vehicle .xml
	- Create a new UML profile and port all needed xml data over to it
- [Optional] move all resources dictated by .model, .visual and .visual\_processed file to an unique location.
- Rezip the new .wotmod into place

Each of these process should correspond to a single python function in the script.

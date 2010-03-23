all:
	gtk-builder-convert minex/data/minex.glade bin/minex.xml
	mkdir /tmp/minex/
	cp minex/minex.py /tmp/minex/
	sed -i "s/'..\/bin\/minex.xml'/'minex.xml'/g" /tmp/minex/minex.py
	python -mcompileall /tmp/minex/
	mv /tmp/minex/minex.pyc bin/minex
	chmod a+x bin/minex
	cp minex/data/minex.png bin/
	rm -rf /tmp/minex/

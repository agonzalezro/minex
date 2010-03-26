all:
	mkdir -p bin/
	gtk-builder-convert minex/data/minex.glade bin/minex.xml
	mkdir -p /tmp/minex/
	cp minex/minex.py /tmp/minex/
	sed -i "s/'..\/bin\/minex.xml'/'minex.xml'/g" /tmp/minex/minex.py
	sed -i "s/'..\/bin\/minex.png'/'minex.png'/g" /tmp/minex/minex.py
	python -mcompileall /tmp/minex/
	mv /tmp/minex/minex.pyc bin/minex
	chmod a+x bin/minex
	cp minex/data/minex.png bin/
	rm -rf /tmp/minex/

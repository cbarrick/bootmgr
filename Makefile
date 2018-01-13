.DEFAULT: all
.PHONY: all install clean

DESTDIR ?= /usr/local


all: build/bin/bootmgr


install: all
	cp -RT build $(DESTDIR)


clean:
	rm -rf build


build/bin/bootmgr: bootmgr.py
	mkdir -p build/bin
	cp bootmgr.py build/bin/bootmgr
	chmod +x build/bin/bootmgr

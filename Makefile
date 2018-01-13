.DEFAULT: all
.PHONY: all install clean

DESTDIR ?= /
PREFIX  ?= /usr


all: build/$(PREFIX)/bin/bootmgr


install: all
	cp -RT build $(DESTDIR)


clean:
	rm -rf build


build/$(PREFIX)/bin/bootmgr: bootmgr.py
	mkdir -p build/$(PREFIX)/bin
	cp bootmgr.py build/$(PREFIX)/bin/bootmgr
	chmod +x build/$(PREFIX)/bin/bootmgr

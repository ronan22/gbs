VERSION = $(shell sed -ne 's/__version__\s*=\s*[\x22\x27]\([^\x22\x27]\+\)[\x22\x27].*/\1/p ' gitbuildsys/__init__.py)
TAGVER = $(shell echo $(VERSION) | sed -e "s/\([0-9\.]*\).*/\1/")
PKGNAME = gbs

ifeq ($(VERSION), $(TAGVER))
	TAG = $(TAGVER)
else
	TAG = "HEAD"
endif
TAG="HEAD"
ifndef PREFIX
    PREFIX = "/usr/local"
endif

all:
	python setup.py build
	cd bsr && python setup.py build && cd ..

tag:
	git tag $(VERSION)

dist-common: man
	git archive --format=tar --prefix=$(PKGNAME)-$(TAGVER)/ $(TAG) | tar xpf -
	git show $(TAG) --oneline | head -1 > $(PKGNAME)-$(TAGVER)/commit-id
	mkdir $(PKGNAME)-$(TAGVER)/doc; mv gbs.1 $(PKGNAME)-$(TAGVER)/doc

dist-bz2: dist-common
	tar jcpf $(PKGNAME)-$(TAGVER).tar.bz2 $(PKGNAME)-$(TAGVER)
	rm -rf $(PKGNAME)-$(TAGVER)

dist-gz: dist-common
	tar zcpf $(PKGNAME)-$(TAGVER).tar.gz $(PKGNAME)-$(TAGVER)
	rm -rf $(PKGNAME)-$(TAGVER)

man:
	rst2man docs/GBS.rst >docs/gbs.1

html:
	rst2html docs/GBS.rst >docs/gbs.html

pdf:
	rst2pdf docs/GBS.rst -o docs/gbs.pdf

docs: man html pdf

install: all
	python setup.py install --prefix=${PREFIX}
	cd bsr && python setup.py install --install-scripts=/usr/local/bin --prefix=/usr/local && cd ..

clean:
	rm -rf {build/,dist/,*.egg-info/}
	cd bsr && rm -rf {build/,dist/,*.egg-info/} && cd ..
test:
	nosetests -v --with-coverage --with-xunit

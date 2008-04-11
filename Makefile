r := $(shell svnversion -nc .. | sed -e 's/^[^:]*://;s/[A-Za-z]//')
ts := $(shell date +%s)
tmpdir := $(shell mktemp -ud)
pwd := $(shell pwd)

release:
	@rm -rf $(tmpdir)
	@mkdir -p $(tmpdir)
	@svn export . $(tmpdir)/appengine_helper_for_django
	@echo "VERSION=$(r)\nTIMESTAMP=$(ts)\n" > \
		$(tmpdir)/appengine_helper_for_django/VERSION
	@rm $(tmpdir)/appengine_helper_for_django/Makefile
	@cd $(tmpdir); find . | \
		zip $(pwd)/appengine_helper_for_django-r$(r).zip -@ >/dev/null
	@rm -rf $(tmpdir)

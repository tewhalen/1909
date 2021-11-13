# a makefile

LAST_PAGE = 171

PAGES = $(shell seq -f %03g 0 $(LAST_PAGE))

PAGE_DIRS = $(addprefix working/,$(PAGES))

MAKEFILES = $(addsuffix /Makefile,$(PAGE_DIRS))

TOP := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

all: $(MAKEFILES)
	@for dir in $(PAGE_DIRS); do \
			$(MAKE) -C $$dir;\
	done

clean:
		@for dir in $(PAGE_DIRS); do \
				$(MAKE) -C $$dir clean;\
		done
		rm working/page-subset.pdf

working:
	mkdir working

setup: $(MAKEFILES) working/page-subset.pdf

$(PAGE_DIRS):
	mkdir $@

$(MAKEFILES): working/%/Makefile: page.makefile working/%
	cp page.Makefile $@


working/page-subset.pdf: source/house-renumbering-1909.PDF
	gs -q -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dSAFER \
       -dFirstPage=7 -dLastPage=178 \
       -sOutputFile=$@ $<

remake_pages:	working/page-subset.pdf
		for dir in $(PAGE_DIRS); do \
	        $(MAKE) -C $$dir remake_page;\
		done

report:
	python processors/report.py
#.PHONY: spanners

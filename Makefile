# a makefile

LAST_PAGE = 1820

PAGES = $(shell seq -f %04g 0 $(LAST_PAGE))

PAGE_DIRS = $(addprefix working/,$(PAGES))

MAKEFILES = $(addsuffix /Makefile,$(PAGE_DIRS))

OCRFULL = $(addsuffix /page.csv,$(PAGE_DIRS))

TOP := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

.PRECIOUS: working/%/column-1-raw_ocr.csv working/%/column-2-raw_ocr.csv working/%/column-3-raw_ocr.csv working/%/column-4-raw_ocr.csv working/%/column-5-raw_ocr.csv working/%/page.png working/%/column-1.png

# ".SECONDARY with no prerequisites causes all targets to be treated as secondary 
# (i.e., no target is removed because it is considered intermediate). 
# does this work?
.SECONDARY:

all: $(OCRFULL)


ocr_clean:
	rm -f working/*/column*ocr*.csv working/*/page.csv

img_clean:
	rm -f working/*/column*.png working/*/page-crop.png


clean: ocr_clean img_clean
		@for dir in $(PAGE_DIRS); do \
				$(MAKE) -C $$dir clean;\
		done
		rm working/page-subset.pdf

working/%/page-convert.png: working/%/page.png
	convert +dither -colors 2 -colorspace gray -normalize -density 600x600 $< $@

working/%/page-crop.png: working/%/page-convert.png
	processors/auto_crop_page.py $< $@

working/%/column-1.png working/%/column-2.png working/%/column-3.png working/%/column-4.png working/%/column-5.png: working/%/page-crop.png
	processors/split_columns.py $<

working/%/column-1-raw_ocr.csv: working/%/column-1.png
	processors/raw_ocr.py $< $@

working/%/column-2-raw_ocr.csv: working/%/column-2.png
	processors/raw_ocr.py $< $@

working/%/column-3-raw_ocr.csv: working/%/column-3.png
	processors/raw_ocr.py $< $@

working/%/column-4-raw_ocr.csv: working/%/column-4.png
	processors/raw_ocr.py $< $@

working/%/column-5-raw_ocr.csv: working/%/column-5.png
	processors/raw_ocr.py $< $@

working/%/column-1-ocr.csv: working/%/column-1-raw_ocr.csv
	processors/ocr_column.py $< $@ --errors working/$*/column-1-e.csv 

working/%/column-2-ocr.csv: working/%/column-2-raw_ocr.csv working/%/column-1-ocr.csv
	processors/ocr_column.py $< $@ --errors working/$*/column-2-e.csv 

working/%/column-3-ocr.csv: working/%/column-3-raw_ocr.csv working/%/column-2-ocr.csv
	processors/ocr_column.py $< $@ --errors working/$*/column-3-e.csv 

working/%/column-4-ocr.csv: working/%/column-4-raw_ocr.csv working/%/column-3-ocr.csv
	processors/ocr_column.py $< $@  --errors working/$*/column-4-e.csv 

working/%/column-5-ocr.csv: working/%/column-5-raw_ocr.csv working/%/column-4-ocr.csv
	processors/ocr_column.py $< $@  --errors working/$*/column-5-e.csv 

working/%/page.csv: working/%/column-1-ocr.csv working/%/column-2-ocr.csv working/%/column-3-ocr.csv working/%/column-4-ocr.csv working/%/column-5-ocr.csv
	csvstack $^ > $@

remake_pages:	$(addsuffix /page.png,$(PAGE_DIRS))
	

report:
	python processors/report.py
#.PHONY: spanners

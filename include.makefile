# a makefile


#TOP := $(dir $(CURDIR)/$(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST)))
TOP := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

COL_NOS = 1 2 3 4 5
COLUMNS = $(addprefix column-,$(COL_NOS))
COL_IMGS = $(addsuffix .png, $(COLUMNS))
#column-1.png column-5.png column-2.png column-3.png column-4.png

.PHONY = all
INFO = $(addsuffix .csv, $(COLUMNS))

.SECONDARY: $(SEGMENTS)

all: $(INFO) page.csv
	@:

clean:
	rm -f column-*.csv page.csv
	rm -f column-*.png
	rm -f page-crop.png
	rm -f page.png

# extract the specific page
page.png:
	convert +dither -colors 2 -colorspace gray -normalize -density 600x600 ../page-subset.pdf[$(notdir $(CURDIR))] page.png

# crop the page
page-crop.png: page.png
	$(TOP)/processors/auto_crop_page.py $< $@

# divide into columns
$(COL_IMGS): page-crop.png
	$(TOP)/processors/split_columns.py $<

column-1.csv: column-1.png
	$(TOP)/processors/ocr_column.py $< $@ --errors column-1-e.csv --page_id $(notdir $(CURDIR))

column-2.csv: column-2.png column-1.csv
	$(TOP)/processors/ocr_column.py $< $@ --prev_csv column-1.csv --errors column-2-e.csv --page_id $(notdir $(CURDIR))

column-3.csv: column-3.png column-2.csv
	$(TOP)/processors/ocr_column.py $< $@ --prev_csv column-2.csv --errors column-3-e.csv --page_id $(notdir $(CURDIR))

column-4.csv: column-4.png column-3.csv
	$(TOP)/processors/ocr_column.py $< $@ --prev_csv column-3.csv --errors column-4-e.csv --page_id $(notdir $(CURDIR))

column-5.csv: column-5.png column-4.csv
	$(TOP)/processors/ocr_column.py $< $@ --prev_csv column-4.csv --errors column-5-e.csv --page_id $(notdir $(CURDIR))

page.csv: $(INFO)
	csvstack $^ > page.csv




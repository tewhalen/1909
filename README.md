Requirements:

- Python 3 (probably at least 3.4)
- pipenv (`pip3 install pipenv`)
- tesseract (`brew install tesseract`, at least if you have a mac and homebrew working)
- imagemagick / ghostscript 

# Using this repository:

The working/ subfolders contain a folder for each page. Each contains a page.png file that's the
baseline page. It'll attempt to auto-deskew and crop each page. 

> `pipenv install`

`make all` at the top level should attempt to deskew, crop, split, and OCR everything, building
CSV output in each working dir.

> `pipenv shell`

> `make setup`

> `make all`

After that, concatenating all the page.csv files in each working dir should work.
> `csvstack working/*/page.csv > all_data.csv`

## Manual tweaking

Any skew of the type on the page greatly affects the reliability of page segmentation and OCR. If you want to manually override the automatic cropping/deskewing process, create a `page-handcrop.png` file in the page's working directory. Some already have them. Leaving a medium amount of white border on the page helps the OCR, as does removing any horizontal lines and noise. Be sure to
leave the four thick vertical columnar separators, but the janky thin typeset lines that separate the odd/even columns can be removed. This sometimes
helps with OCR if the addresses get too close to that line.

## The OCR model

This includes a `1909.traineddata` file which is based on the "best" english tesseract model, fine-tuned with more than 4000 hand-corrected examples from the scanned book. This, in theory, is slightly better at dealing with the type and typesetting of thee text. 

## Exploring

`make report` should produce some reporting on how far your OCR process got, where it failed, and which pages have the best/worst OCR confidence. If certain processors simply refuse to run (the OCR will abort if there's a high error percentage), you can create a `force-ocr` file in that page directory and it'll force it through.


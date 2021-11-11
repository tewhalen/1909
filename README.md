Requirements:

- Python 3 (probably at least 3.4)
- tessseract
- imagemagick
- gnu make

Using this repository:

The working/ subfolders contain a folder for each page. Each contains a page.png file that's the
baseline page. It'll attempt to auto-deskew and crop each page. If you want to manually override
this process, create a page-handcrop.png file in the working directory. Some already have them.

> pipenv install

'make all' at the top level should attempt to deskew, crop, split, and OCR everything, building
CSV output in each working dir.

> pipenv shell
> make setup
> make all

After that, concatenating all the page.csv files in each working dir should work.
> csvstack working/*/page.csv > all_data.csv


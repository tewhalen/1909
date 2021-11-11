#!/usr/bin/env python3
import os
import sys

import click
import peakutils
from PIL import Image
from shapely.geometry import Polygon

from image_utils import auto_crop, deskew, new_crop, silly_crop
from street_correct import divide_into_rows, divide_slip, find_five_columns

# print(sys.path)




def save_column(im, i, column):
    """Save this column"""

    ftif = "column-%d.png" % (i + 1)

    trimmed = im.crop(column.bounds)
    # horizontal deskew
    trimmed = deskew(trimmed, axis=0)
    # trimmed = silly_crop(trimmed)
    trimmed.save(ftif, "PNG")
    return trimmed


def get_columns(bar_limits, im_size):
    width, height = im_size

    cols = []
    for right, left in bar_limits:

        p = Polygon([(right, 0), (left, 0), (left, height), (right, height)])
        cols.append(p)
    return cols


@click.command()
@click.argument("filename", type=click.Path(exists=True))
def split_page(filename):
    """Extract columns from spreadsheet-like image file"""
    im = Image.open(filename)
    try:
        column_limits = find_five_columns(im)
        clips = get_columns(column_limits, im.size)
    except RuntimeError:
        sys.stderr.write("%s: can't split into columns\n" % (filename))
        sys.exit(1)
    # sys.stderr.write("%s: %d columns detected\n" % (filename, len(vlines)))

    # clips = get_columns(vlines, top_bar, im.size)
    # sys.stderr.write("%s: cols: %d\n" % (filename, len(clips)))

    for i, col in enumerate(clips):
        trimmed_column = save_column(im, i, col)


if __name__ == "__main__":
    # split target page into columnar json segementation files
    split_page()

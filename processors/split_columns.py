#!/usr/bin/env python3
import pathlib
import sys

import click
from loguru import logger
from PIL import Image
from shapely.geometry import Polygon

from image_utils import deskew
from street_correct import find_five_columns


logger.remove()


def save_column(im, i, column, savepath):
    """Save this column"""

    ftif = "column-%d.png" % (i + 1)

    trimmed = im.crop(column.bounds)
    # horizontal deskew
    trimmed = deskew(trimmed, axis=0)
    # trimmed = silly_crop(trimmed)
    trimmed.save(savepath / ftif, "PNG")
    return trimmed


def get_columns(bar_limits, im_size):
    width, height = im_size

    cols = []
    for right, left in bar_limits:

        p = Polygon([(right, 0), (left, 0), (left, height), (right, height)])
        cols.append(p)
    return cols


@logger.catch
@click.command()
@click.argument("filename", type=click.Path(exists=True))
def split_page(filename):
    """Extract columns from spreadsheet-like image file"""

    logger.add(
        sys.stderr, format="<level>{message}</level>", backtrace=True, level="INFO"
    )

    handcrop = pathlib.Path(filename).with_name("page-handcrop.png")
    if handcrop.exists():
        logger.success(
            "%s: page-handcrop.png exists, using it to override.\n" % (filename,)
        )
        filename = handcrop

    im = Image.open(filename)
    try:
        column_limits = find_five_columns(im)
        clips = get_columns(column_limits, im.size)
    except RuntimeError:
        logger.critical("{}: can't split into columns", filename)
        raise
        sys.exit(1)
    # sys.stderr.write("%s: %d columns detected\n" % (filename, len(vlines)))

    # clips = get_columns(vlines, top_bar, im.size)
    # sys.stderr.write("%s: cols: %d\n" % (filename, len(clips)))

    savepath = pathlib.Path(filename).parent
    for i, col in enumerate(clips):
        save_column(im, i, col, savepath)


if __name__ == "__main__":
    # split target page into columnar json segementation files
    split_page()

#!/usr/bin/env python3
import os
import pathlib
import shutil
import sys

import click
import numpy as np
import peakutils
from loguru import logger
from PIL import Image

from image_utils import deskew, get_histogram, new_crop, newish_crop

#sys.path.append(os.path.dirname(os.path.dirname(__file__)))


logger.remove()
def find_top_two_lines(img):
    """Each page has two horizontal lines running across the top"""
    wd, ht = img.size

    # find the top lines
    # which should be in the top half
    hist = get_histogram(img, axis=1)
    indexes = peakutils.indexes(hist, thres=0.9)  # , min_dist=5)
    return indexes[-1]


def topline_crop(img: Image):

    topline = find_top_two_lines(img)

    wd, ht = img.size

    return img.crop((0, topline, wd, ht))


@click.command()
@click.argument("filename", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--force", is_flag=True, help="Force auto-cropping even if the override file exists.")
def crop_page(filename, output, force):
    """deskew using horizontal lines and intelligently crop
    
    unless page-handcrop.png exists, in which case copy that."""

    logger.add(sys.stderr, format="<level>{message}</level>", level="INFO")

    handcrop = pathlib.Path(filename).with_name('page-handcrop.png')
    if handcrop.exists() and not force:
        shutil.copy(handcrop, output)
        logger.success("%s: page-handcrop.png exists, using it to override.\n" % (filename,))

        sys.exit()

    im = Image.open(filename)
    # pix = im.load()
    width, height = im.size
    logger.info("%s: %dx%d\n" % (filename, width, height))
    logger.info("%s: deskewing horiz " % (filename,))
    

    im = deskew(im)

    width, height = im.size
    logger.info("(%dx%d)\n" % (width, height))

    try:
        logger.debug("%s: removing top two lines.\n" % (filename,))

        im = topline_crop(im)
    except:
        logger.critical("%s: failed to find the top two lines.\n" % (filename,))
        sys.exit(1)
    width, height = im.size

    logger.info("%s: deskewing vert\n" % (filename,))
    im = deskew(im, axis=1)
    width, height = im.size

    # sys.stderr.write("%s: cropping\n" % (filename,))
    # im = newish_crop(im)
    # width, height = im.size
    logger.info("%s: revised to %dx%d\n" % (filename, width, height))
    im.save(output)


if __name__ == "__main__":
    # split target page into columnar json segementation files
    crop_page()

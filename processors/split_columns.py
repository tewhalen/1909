#!/usr/bin/env python3
import pathlib
import sys

import click
from loguru import logger
from PIL import Image
import cv2
import numpy as np
import pandas as pd

from image_utils import deskew
from street_correct import find_five_columns


logger.remove()


def save_column(im, i, column, savepath):
    """Save this column"""

    ftif = "column-%d.png" % (i + 1)
    h, w = im.size
    x1, x2 = column

    trimmed = im.crop((x1, 0, x2, w))
    # horizontal deskew
    trimmed = deskew(trimmed, axis=0)
    # trimmed = silly_crop(trimmed)
    trimmed.save(savepath / ftif, "PNG")
    return trimmed


def find_lines_in_image(filename):
    orig_img = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
    (h, w, _) = orig_img.shape

    SIZE = 600

    scale = float(SIZE) / w

    n_h, n_w = int(h * scale), int(w * scale)
    img = cv2.resize(orig_img, (n_w, n_h))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 75, 150)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=int(80),
        minLineLength=200,
        maxLineGap=2,
    )
    lines = pd.DataFrame(lines[:, 0, :], columns=["x1", "y1", "x2", "y2"])

    return (lines.sort_values("x1") / scale).astype(int)


def get_columns(img, lines, columns=5):
    # let's assume these are fully vertical
    w, h = img.size
    min_width = (w / columns) * 0.9  # -10%
    prev_x = 0
    cols = [0]
    for line in lines.itertuples():
        if line.x1 - prev_x > min_width:
            cols.append(line.x1)
            prev_x = line.x1
    if cols[0] > min_width:
        cols.insert(0, 0)
    if w - cols[-1] > min_width:
        cols.append(w)
    logger.info("h:{}, w:{}, cols:{}", h, w, cols)
    return list(zip(cols, cols[1:]))


@logger.catch
@click.command()
@click.argument("filename", type=click.Path(exists=True))
def split_page(filename):
    """Extract columns from spreadsheet-like image file"""

    logger.add(sys.stderr, format="<level>{message}</level>", level="DEBUG")

    handcrop = pathlib.Path(filename).with_name("page-handcrop.png")
    if handcrop.exists():
        logger.success(
            "%s: page-handcrop.png exists, using it to override.\n" % (filename,)
        )
        filename = handcrop

    # orig_img = cv2.imread(filename, cv2.IMREAD_UNCHANGED)

    lines = find_lines_in_image(str(filename))

    image = Image.open(filename)
    cols = get_columns(image, lines, columns=5)
    logger.info(cols)

    # sys.stderr.write("%s: %d columns detected\n" % (filename, len(vlines)))

    # clips = get_columns(vlines, top_bar, im.size)
    # sys.stderr.write("%s: cols: %d\n" % (filename, len(clips)))

    savepath = pathlib.Path(filename).parent
    for i, col in enumerate(cols):
        save_column(image, i, col, savepath)


if __name__ == "__main__":
    # split target page into columnar json segementation files
    split_page()

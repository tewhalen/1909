#!/usr/bin/env python

import pathlib
import re
import sys

import click
import pandas as pd
from PIL import Image
from loguru import logger

# sys.path.append(pathlib.Path(__file__).parent)
# import config

FILTER_OUT = ["|"]


def filter_horiz_lines(text: str):
    "returns true if this is not just horizontal line stuff"

    horiz_chars = "".maketrans("", "", "—._-~=")

    return any(text.translate(horiz_chars).strip())


@click.command()
@click.argument("filename", type=click.Path(exists=True, path_type=pathlib.Path))
@click.argument("prefix", type=str)
def make_training_data(filename: pathlib.Path, prefix):
    """OCR the file, find the segments that are either
    a) more than a standard deviation under the mean condfidence level; or
    b) aren't entirely numeric

    and write out the image segment as png, along with the text the OCR produced

    This is meant to be hand-corrected and used to train the LSTM model"""

    logger.add(sys.stderr, format="<level>{message}</level>", level="INFO")

    column_id = int(re.match(r"column-([0-9]+)", filename.name).group(1))

    ocr_data = pd.read_csv(
        pathlib.Path(filename.with_name("column-{}-raw_ocr.csv".format(column_id)))
    )
    base_img = Image.open(filename)

    mean_conf = ocr_data["conf"].mean()
    sd_conf = ocr_data["conf"].std()

    worst_q = ocr_data["conf"].quantile(0.2)
    # leaven in the top 20% most-confident
    best_q = ocr_data["conf"].quantile(0.8)

    logger.info("mean confidence: {:.02f} {:.02f}".format(mean_conf, sd_conf))

    for index, row in ocr_data.iterrows():

        if (row.conf > best_q) or (row.conf < worst_q):
            # output a cropped image
            output_fn = "{}-{:05}.png".format(prefix, index)
            box = base_img.crop((row.left, row.top, row.right, row.bot))
            box.save(output_fn)
            # open("{}-{:05n}.gt.txt".format(prefix, index), "w").write(row.text)


if __name__ == "__main__":
    logger.remove()

    # make html?
    make_training_data()

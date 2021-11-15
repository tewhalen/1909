#!/usr/bin/env python

import csv
import json
import os
import sys
import typing

import click
import matplotlib.pyplot as plt
import pandas as pd
from pandas.core import base
import pytesseract
from numpy import nan
from PIL import Image, ImageDraw

FILTER_OUT = ["|"]

# i know this is bad but i'm doing it anyway
TESSDATADIR = "../../"


def filter_horiz_lines(text: str):
    "returns true if this is not just horizontal line stuff"

    horiz_chars = "".maketrans("", "", "—._-~=")

    return any(text.translate(horiz_chars).strip())


def prepare_ocr_data(filename: str) -> pd.DataFrame:

    # Get verbose data including boxes, confidences, line and page numbers

    ocr_data = pytesseract.image_to_data(
        Image.open(filename),
        output_type=pytesseract.Output.DATAFRAME,
        config="--tessdata-dir {} -l 1909 --psm 6".format(
            TESSDATADIR
        ),  # Assume a single uniform block of text.
    ).dropna()

    # we assume the mode is the basic row, and throw out everything that's
    # three times the height of that
    height_mode = ocr_data["height"].mode()[0]  # mode is a series, just use the top

    ocr_data = ocr_data[ocr_data["height"] <= height_mode * 3]

    # and lets throw out anything that's less than 75% the height of the regular row
    ocr_data = ocr_data[ocr_data["height"] > height_mode * 0.75]

    # filter out common OCR errors
    ocr_data = ocr_data[~ocr_data["text"].isin(FILTER_OUT)]

    # filter out horiz lines
    ocr_data = ocr_data[ocr_data["text"].apply(filter_horiz_lines)]

    ocr_data["right"] = ocr_data["left"] + ocr_data["width"]
    ocr_data["bot"] = ocr_data["top"] + ocr_data["height"]
    return ocr_data


@click.command()
@click.argument("filename", type=click.Path(exists=True))
@click.argument("prefix", type=str)
def make_training_data(filename, prefix):
    """OCR the file, find the segments that are either
    a) more than a standard deviation under the mean condfidence level; or
    b) aren't entirely numeric

    and write out the image segment as png, along with the text the OCR produced

    This is meant to be hand-corrected and used to train the LSTM model"""

    ocr_data = prepare_ocr_data(filename)
    base_img = Image.open(filename)

    mean_conf = ocr_data["conf"].mean()
    sd_conf = ocr_data["conf"].std()

    # leaven in the top 10% most-confident
    best_q = ocr_data["conf"].quantile(0.9)

    print("mean confidence: {:.02f} {:.02f}".format(mean_conf, sd_conf))

    for index, row in ocr_data.iterrows():

        if (row.conf > best_q) or (
            (row.conf < (mean_conf - sd_conf)) or not row.text.isnumeric()
        ):
            # output a cropped image
            output_fn = "{}-{:05}.png".format(prefix, index)
            box = base_img.crop((row.left, row.top, row.right, row.bot))
            box.save(output_fn)
            open("{}-{:05n}.gt.txt".format(prefix, index), "w").write(row.text)


if __name__ == "__main__":
    # split target page into columnar json segementation files
    make_training_data()

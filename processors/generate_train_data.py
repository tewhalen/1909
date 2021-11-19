#!/usr/bin/env python


import re

import click
import pandas as pd
import pytesseract
from PIL import Image
import jinja2
import pathlib

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
        config="--psm 6",  # Assume a single uniform block of text.
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
@click.argument("filename", type=click.Path(exists=True, path_type=pathlib.Path))
@click.argument("prefix", type=str)
def make_training_data(filename: pathlib.Path, prefix):
    """OCR the file, find the segments that are either
    a) more than a standard deviation under the mean condfidence level; or
    b) aren't entirely numeric

    and write out the image segment as png, along with the text the OCR produced

    This is meant to be hand-corrected and used to train the LSTM model"""

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

    print("mean confidence: {:.02f} {:.02f}".format(mean_conf, sd_conf))

    t = jinja2.Template(
        open(pathlib.Path(__file__).parent / "training_template.html").read()
    )

    open(filename.with_suffix(".html"), "w").write(
        t.render(
            ocr_data=ocr_data[~ocr_data["conf"].between(worst_q, best_q)],
            column_image=filename.name,
            prefix=prefix,
        )
    )

    for index, row in ocr_data.iterrows():

        if (row.conf > best_q) or (row.conf < worst_q):
            # output a cropped image
            output_fn = "{}-{:05}.png".format(prefix, index)
            box = base_img.crop((row.left, row.top, row.right, row.bot))
            box.save(output_fn)
            # open("{}-{:05n}.gt.txt".format(prefix, index), "w").write(row.text)


if __name__ == "__main__":
    # make html?
    make_training_data()

#!/usr/bin/env python

import csv
import pathlib
import sys

import click
import pandas as pd
import pytesseract
from loguru import logger
from PIL import Image, ImageDraw

logger.remove()

FILTER_OUT = ["|"]

TESSDATADIR = pathlib.Path(__file__).parent.parent


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
@click.argument("output", type=click.Path())
@click.option("--debug_image", type=click.Path())
def ocr_column(filename, output, debug_image=None):
    """get our best information"""
    logger.add(
        sys.stderr, format="<level>{message}</level>", backtrace=True, level="INFO"
    )

    ocr_data = prepare_ocr_data(filename)

    conf = ocr_data["conf"].mean()
    # logger.info("{}: {")
    if conf < 85:
        logger.warning(
            "{} mean (std) OCR confidence: {:.2f} ({:.2f})",
            filename,
            ocr_data["conf"].mean(),
            ocr_data["conf"].std(),
        )
    elif conf >= 92:
        logger.success(
            "{} mean (std) OCR confidence: {:.2f} ({:.2f})",
            filename,
            ocr_data["conf"].mean(),
            ocr_data["conf"].std(),
        )
    else:
        logger.info(
            "{} mean (std) OCR confidence: {:.2f} ({:.2f})",
            filename,
            ocr_data["conf"].mean(),
            ocr_data["conf"].std(),
        )

    ocr_data.to_csv(output, quoting=csv.QUOTE_NONNUMERIC)

    if debug_image:
        # output a marked-up debug image
        base_img = Image.open(filename)
        draw = ImageDraw.Draw(base_img)
        for index, row in ocr_data.iterrows():
            draw.rectangle((row.right, row.bot, row.left, row.top))
            draw.text((row.left, row.bot), row.text, color="red")
            # print(index, row['right'],row['left'],row.conf)
        base_img.save(debug_image)


if __name__ == "__main__":
    # split target page into columnar json segementation files
    ocr_column()

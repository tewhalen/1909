#!/usr/bin/env python

import csv
import pathlib
import sys

import click
import pandas as pd
import pytesseract
from loguru import logger
from PIL import Image, ImageDraw


sys.path.append(str(pathlib.Path(__file__).parent.parent))
# print(sys.path)
import config


def prepare_ocr_data(filename: str) -> pd.DataFrame:

    # Get verbose data including boxes, confidences, line and page numbers

    ocr_data = pytesseract.image_to_data(
        Image.open(filename),
        output_type=pytesseract.Output.DATAFRAME,
        config="--tessdata-dir {} -l {} --psm {}".format(
            config.OCR.TESSDATADIR, config.OCR.MODEL, config.OCR.PSM
        ),  # Assume a single uniform block of text.
    ).dropna()

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
        base_img.convert("RGB")
        new_img = Image.new("RGB", base_img.size)
        new_img.paste(base_img)
        draw = ImageDraw.Draw(new_img)
        for index, row in ocr_data.iterrows():
            color = "blue"
            if row.conf > 90:
                color = "green"
            elif row.conf < 85:
                color = "red"

            draw.rectangle((row.right, row.bot, row.left, row.top), outline=color)
            x = "{} ({:0.0f}%)".format(row.text, row.conf)
            # print("drawing {}".format(x))
            draw.text((row.left, row.bot), x, fill=color)
            # color="red")

            # print(index, row['right'],row['left'],row.conf)
        new_img.save(debug_image, icc_profile=None)


if __name__ == "__main__":

    # split target page into columnar json segementation files
    logger.remove()

    ocr_column()

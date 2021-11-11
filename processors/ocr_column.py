#!/usr/bin/env python

import csv
import json
import os
import sys
import typing

import click
import matplotlib.pyplot as plt
import pandas as pd
import pytesseract
from numpy import nan
from PIL import Image

FILTER_OUT = ["|"]


def filter_horiz_lines(text: str):
    "returns true if this is not just horizontal line stuff"

    horiz_chars = "".maketrans("", "", "—._-~=")

    return any(text.translate(horiz_chars).strip())


class Text:
    def __init__(self, item):
        # print(item)
        self.text = item["text"]
        self.conf = item["conf"]
        self.row = item["top"]
        self.col = item["left"]
        self.bbox = (item["left"], item["top"], item["right"], item["bot"])

    def __repr__(self):
        return "<{!r} ({})>".format(self.text, self.conf)


def parse_group(group):
    # print(repr(group))

    row_height = group["height"].min()
    return (row_height, [Text(row) for i, row in group.iterrows()])


def within(x, pct, value):
    return value * (1 - pct) <= x <= value * (1 + pct)


def make_column_dataframe(column_pairs):

    # make a series
    column_df = pd.DataFrame(
        ((pair[0].text, pair[0].conf) for pair in column_pairs),
        columns=["address", "confidence"],
    )

    # this will make everything non-numeric into Nan
    column_df["address"] = pd.to_numeric(
        column_df["address"],
        errors="coerce",
    )
    return column_df


class Street:
    def __init__(self, name: str, page_id: int):
        self.pairs = []
        self.name = name
        self.page_id = page_id

    def parse_row(self, texts) -> bool:

        # ignore header rows
        if texts[0].text.startswith("CONTINUED"):
            return True
        elif texts[0].text == "Odd":
            return True
        elif texts[0].text == "Old":
            return True
        elif texts[0].text == "New":
            return True

        if len(texts) == 2:
            # simple map?
            self.pairs.append((texts[0], texts[1]))
            return True
        elif len(texts) == 4:
            self.pairs.append((texts[0], texts[1]))
            self.pairs.append((texts[2], texts[3]))

            return True
        else:
            return False

    def divide_into_columns(self) -> typing.Tuple[list, list]:
        # so first we divide into two columns
        left_most_new_col = 9999
        left_most_new = None
        left_most_width = 0

        for new, old in self.pairs:
            # find the right-most old start
            if new.col < left_most_new_col:
                left_most_new = new
                left_most_new_col = new.col
                left_most_width = old.bbox[2]  # right bbox edge
        column_one = []
        column_two = []

        for new, old in self.pairs:
            if new.col > left_most_width:
                column_two.append((new, old))
            else:
                column_one.append((new, old))
        return column_one, column_two

    def check_assumptions(self):
        """We assume the new address numbers are monotonically increasing in each column
        And new addresses are purely numeric
        And all odd or all even in a column
        """
        col_one, col_two = self.divide_into_columns()

        error_count = 0

        column = make_column_dataframe(col_one)

        if col_two:
            # col one is oddd and col two is even
            col_one_oddeven = 0
            col_two_oddeven = 1
        elif (column["address"].mod(2)).mode()[0] == 0:
            # find whether most are even or odd

            # col one is even
            col_one_oddeven = 1
        else:
            # col one is odd
            col_one_oddeven = 0

        column.loc[column["address"].mod(2) == col_one_oddeven, "address"] = nan

        # score for monotonicity
        null_out_mono_errors(column, "address")

        for i in column[column["address"].isna()].index:
            col_one[i][0].text = ""  # clear text of nas
        error_count = column["address"].isnull().sum()

        if col_two:
            column = make_column_dataframe(col_two)
            # column two is always even
            column.loc[column["address"].mod(2) == 1, "address"] = nan

            # score for monotonicity
            null_out_mono_errors(column, "address")

            for i in column[column["address"].isna()].index:
                col_two[i][0].text = ""  # clear text of nas
            error_count += column["address"].isnull().sum()

        return error_count
        if False:
            print(self.name)
            print(col_one, col_two)
            print(column)
            column["address"].plot()
            plt.show()

    def output(self, infile_name: str, outfile: csv.DictWriter):
        for new, old in self.pairs:
            outfile.writerow(
                {
                    "page": self.page_id,
                    "filename": infile_name,
                    "street": self.name,
                    "old": old.text,
                    "new": new.text,
                    "old_conf": old.conf,
                    "new_conf": new.conf,
                    "old_bbox": old.bbox,
                    "new_bbox": new.bbox,
                }
            )


def null_out_mono_errors(df, column_name):
    "set df[column_name] to NaN when the value isn't monotonically increasing" ""
    for i, row in df.iterrows():

        score = mono_score(df[column_name], i)
        if score > 1 and row[column_name]:
            df.loc[i, column_name] = nan


def mono_score(series, i):
    # diff should be positive below and positive above
    #                 v
    # 100  102  104  106   108   110   112
    # true true true false false false false # x[i] - x[n] > 0
    # true true true false false false false # n < i
    diff = (series[i] - series) > 0
    index = series.index < i
    comparison = diff != index

    if False:  # series[i] == 1307:
        print(i, "diff", diff)

        print(i, "index", index)
        print(comparison)
        print(comparison.where(series.notna()))
        print(comparison.sum())

    return comparison.where(series.notna()).sum() ** 2 / len(series)


def prepare_ocr_data(filename):

    # Get verbose data including boxes, confidences, line and page numbers

    ocr_data = pytesseract.image_to_data(
        Image.open(filename),
        output_type=pytesseract.Output.DATAFRAME,
        config="--psm 6",  # Assume a single uniform block of text.
    ).dropna()
    height_mode = ocr_data["height"].mode()[0]  # mode is a series, just use the top
    # we assume the mode is the basic row, and throw out everything that's
    # three times the height of that
    ocr_data = ocr_data[ocr_data["height"] <= height_mode * 3]
    # and lets throw out anything that's less than 75% the width of the regular row
    ocr_data = ocr_data[ocr_data["height"] > height_mode * 0.75]

    # filter out common OCR errors
    ocr_data = ocr_data[~ocr_data["text"].isin(FILTER_OUT)]

    # filter out horiz lines
    ocr_data = ocr_data[ocr_data["text"].apply(filter_horiz_lines)]

    ocr_data["right"] = ocr_data["left"] + ocr_data["width"]
    ocr_data["bot"] = ocr_data["top"] + ocr_data["height"]
    return ocr_data


def set_error(df, group_id, error_msg):
    # add an error message to the group
    df.loc[
        (df["block_num"] == group_id[0])
        & (df["par_num"] == group_id[1])
        & (df["line_num"] == group_id[2]),
        "error",
    ] = error_msg


@click.command()
@click.argument("filename", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--errors", type=click.Path())
@click.option("--prev_csv", type=click.Path(exists=True))
@click.option("--page_id", type=int)
def ocr_column(filename, output, errors, prev_csv=None, page_id=0):
    """get our best information"""

    ocr_data = prepare_ocr_data(filename)
    height_mode = ocr_data["height"].mode()[0]  # mode is a series, just use the top
    ocr_data["error"] = ""
    grouped = ocr_data.groupby(["block_num", "par_num", "line_num"])

    # print(ocr_data["height"].describe())

    if os.path.exists("known_streets.json"):
        known_streets = json.load(open("known_streets.json"))
    else:
        known_streets = None

    if prev_csv:
        # get the last row of the csv
        try:
            prev_street = [x for x in csv.DictReader(open(prev_csv))][-1]["street"]
        except IndexError:
            sys.stderr.write("{}: can't find a previous street name in {}\n".format(filename, prev_csv))
            sys.exit(1)
        current_street = Street(prev_street, page_id=page_id)
        streets = [current_street]
        print("starting with {}".format(prev_street))
    elif known_streets:
        current_street = Street(known_streets[0], page_id=page_id)

        streets = [current_street]
    else:
        streets = []
        current_street = Street(None, page_id=page_id)

    failed_groups = []
    error_count = 0
    success_count = 0
    for group_id, group in grouped:
        result = False

        row_height, texts = parse_group(group)
        if row_height > 1.3 * height_mode:
            # this is a street name probably
            if not known_streets:
                current_street = Street(name=" ".join(x.text for x in texts), page_id=page_id)
                streets.append(current_street)
                result = True
            else:
                new_street_name = name=" ".join(x.text for x in texts)
                if new_street_name in known_streets:
                    new_street_name = known_streets[new_street_name]
                    if new_street_name != current_street.name:
                        current_street = Street(new_street_name, page_id=page_id)
                        streets.append(current_street)
                        result = True
        elif within(row_height, 0.10, height_mode):

            result = current_street.parse_row(texts)
            if not result:
                set_error(ocr_data, group_id, "{} unparsable".format(error_count))

                error_count += 1
            else:
                success_count += 1
        else:
            result = False
            set_error(ocr_data, group_id, "{} bad row height".format(error_count))

            error_count += 1

        if not result:
            failed_groups.append(group_id)

    if error_count:
        print(
            "{} ({:0.1%}) errored groups.".format(
                error_count, error_count / (error_count + success_count)
            )
        )
        groups = [grouped.get_group(i) for i in failed_groups]
        failures = pd.concat(groups, axis=0, join="outer")
        failures.to_csv(errors, quoting=csv.QUOTE_NONNUMERIC)
    with open(output, "w") as output_fp:
        output_csv = csv.DictWriter(
            output_fp,
            ["page",
                "filename",
                "street",
                "old",
                "new",
                "old_conf",
                "new_conf",
                "old_bbox",
                "new_bbox",
            ],
        )
        output_csv.writeheader()
        for street in streets:
            if street.pairs:
                errors = street.check_assumptions()
                print(
                    "{}: {} pairs, {} errors".format(
                        street.name, len(street.pairs), errors
                    )
                )
                street.output(infile_name=filename, outfile=output_csv)


if __name__ == "__main__":
    # split target page into columnar json segementation files
    ocr_column()

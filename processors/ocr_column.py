#!/usr/bin/env python

import copy
import csv
import itertools
import pathlib
import re
import sys
import typing

import click
import pandas as pd
from loguru import logger
from numpy import nan

logger.remove()


def probable_street_name(text: str):
    for substr in (
        "Street",
        "Court",
        "Avenue",
        "North",
        "South",
        "Place",
        "East",
        "West",
    ):
        if substr in text:
            return True
    return False


class Text:
    def __init__(self, item):
        self.text = item["text"]
        self.line_num = item["line_num"]
        self.conf = item["conf"]
        self.top = item["top"]
        self.left = item["left"]
        self.right = item["right"]
        self.bot = item["bot"]
        self.flag = False

    @property
    def bbox(self):
        return (self.left, self.top, self.right, self.bot)

    def __repr__(self):
        return "<{!r} ({})>".format(self.text, self.conf)

    def __add__(self, other):
        d = {}
        d["text"] = self.text + " " + other.text
        d["conf"] = min(self.conf, other.conf)
        d["top"] = max(self.top, other.top)
        d["left"] = min(self.left, other.left)
        d["right"] = max(self.right, other.right)
        d["bot"] = min(self.bot, other.bot)
        d["line_num"] = self.line_num
        return Text(d)

    def split(self):
        "split this if it has a |"
        texts = []
        if "|" in self.text:
            for subtext in self.text.split("|"):
                if subtext:
                    new_text = copy.copy(self)
                    new_text.text = subtext
                    texts.append(new_text)
        else:
            texts = [self]
        return texts


def parse_ocr_row(group):

    row_height = group["height"].min()
    texts = [Text(row).split() for i, row in group.iterrows()]
    texts = list(itertools.chain.from_iterable(texts))
    return (row_height, texts)


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
        """Based on the number and contents of the texts in the row, attempt to
        figure out the address mapping"""

        # ignore header rows
        if texts[0].text.startswith("CONTINUED"):
            return True
        elif texts[0].text == "Odd":
            return True
        elif texts[0].text == "Old":
            return True
        elif texts[0].text == "New":
            return True

        is_num = [x.text.isnumeric() for x in texts]
        if len(texts) == 2:
            # simple map?
            self.pairs.append((texts[0], texts[1]))
            return True
        elif len(texts) == 3:
            # new old suffix
            # new prefix old
            if texts[0].text.isnumeric():
                if texts[1].text.isnumeric() or texts[2].text.isnumeric():
                    self.pairs.append((texts[0], texts[1] + texts[2]))
                    return True
            logger.debug(
                "Row of length three unparsable: {}", " ".join(x.text for x in texts)
            )
            return False
        elif (
            len(texts) == 4 and texts[0].text.isnumeric() and texts[2].text.isnumeric()
        ):
            # somehow we got two pairs
            # new old  | new old
            self.pairs.append((texts[0], texts[1]))
            self.pairs.append((texts[2], texts[3]))

            return True
        elif len(texts) == 5 and is_num[0]:
            # NEW   old     suffix  NEW     old
            # NEW   old     NEW     old     suffix
            # NEW   prefix  old     NEW     old
            # NEW   old     NEW     prefix  old

            if is_num[2] and not (is_num[4] and is_num[3]):
                # NEW   old     NEW     old     suffix
                # NEW   old     NEW     prefix  old
                self.pairs.append((texts[0], texts[1]))
                self.pairs.append((texts[2], texts[3] + texts[4]))
                return True
            elif not (is_num[1] and is_num[2]):
                # NEW   old     suffix  NEW     old
                # NEW   prefix  old     NEW     old
                self.pairs.append((texts[0], texts[1] + texts[2]))
                self.pairs.append((texts[3], texts[4]))
                return True
            return False

        elif len(texts) == 6:
            # new old suffix new old suffix
            if texts[0].text.isnumeric() and texts[3].text.isnumeric():
                if (texts[1].text.isnumeric() or texts[2].text.isnumeric()) and (
                    texts[4].text.isnumeric() or texts[5].text.isnumeric()
                ):

                    self.pairs.append((texts[0], texts[1] + texts[2]))
                    self.pairs.append((texts[0], texts[4] + texts[5]))
                    return True
            return False

    def divide_into_columns(self) -> typing.Tuple[list, list]:
        # so first we divide into two columns
        # we'll leverage the line number for this

        furthest_right_old = 0  # the start of the furthest-right old
        left_most_c2_new = 0  # the start of the associated new

        for new, old in self.pairs:
            # find the right-most old start
            if old.left > furthest_right_old:
                furthest_right_old = old.left
                left_most_c2_new = new.left

        column_one = []
        column_two = []

        for new, old in self.pairs:
            if new.right <= left_most_c2_new:
                # doesn't overlap
                column_one.append((new, old))
            else:
                column_two.append((new, old))
        logger.debug(
            "found {} left pairs and {} right pairs", len(column_one), len(column_two)
        )
        if not column_one:
            return column_two, column_one
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
            # col one is odd and col two is even
            col_one_oddeven = 0
            logger.debug("{}: column 1 is odd and column 2 is even", self.name)
        elif (column["address"].mod(2)).mode()[0] == 0:
            # find whether most are even or odd

            # col one is even
            col_one_oddeven = 1
            logger.debug("{}: a single even column", self.name)

        else:
            # col one is odd
            col_one_oddeven = 0
            logger.debug("{}: a single odd column", self.name)

        column.loc[column["address"].mod(2) == col_one_oddeven, "address"] = nan

        # score for monotonicity
        null_out_mono_errors(column, "address")

        for i in column[column["address"].isna()].index:
            logger.debug(
                "{} doesn't seem right in row {}...",
                col_one[i][0].text,
                col_one[i][0].line_num,
            )
            col_one[i][0].flag = True  # clear text of nas
        error_count = column["address"].isnull().sum()

        if col_two:
            column = make_column_dataframe(col_two)
            # column two is always even
            column.loc[column["address"].mod(2) == 1, "address"] = nan

            # score for monotonicity
            null_out_mono_errors(column, "address")

            for i in column[column["address"].isna()].index:
                col_two[i][0].flag = True  # clear text of nas
            error_count += column["address"].isnull().sum()

        return error_count

    def output(self, column: int, outfile: csv.DictWriter):
        for new, old in self.pairs:
            outfile.writerow(
                {
                    "page": self.page_id,
                    "column": column,
                    "line_num": new.line_num,
                    "street": self.name,
                    "new": new.text,
                    "old": old.text,
                    "new_conf": new.conf,
                    "old_conf": old.conf,
                    "new_bbox": new.bbox,
                    "old_bbox": old.bbox,
                    "flag": new.flag or old.flag,
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

    return comparison.where(series.notna()).sum() ** 2 / len(series)


def set_error(df, group_id, error_msg):
    # add an error message to the group
    df.loc[
        (df["block_num"] == group_id[0])
        & (df["par_num"] == group_id[1])
        & (df["line_num"] == group_id[2]),
        "error",
    ] = error_msg


def get_previous_street_name(column_id: int, output_path) -> str:
    """Based on the column id and file location, try to find a previous column's
    output in order to get the last know street name, so we can continue
    if necessary.
    """
    if column_id > 1:
        prev_csv = output_path.with_stem("column-{}-ocr".format(column_id - 1))
        if not prev_csv.exists():
            logger.warning("Can't find expected previous column {}\n".format(prev_csv))
            return None
        else:
            logger.info("Looking in {} for previous street name.", prev_csv)
            # get the last row of the csv
            try:
                return [x for x in csv.DictReader(open(prev_csv))][-1]["street"]
            except IndexError:
                logger.warning(
                    "Can't find a previous street name in {}\n".format(prev_csv)
                )
                return None
    else:
        return None


@click.command()
@click.argument("filename", type=click.Path(exists=True, path_type=pathlib.Path))
@click.argument("output", type=click.Path(path_type=pathlib.Path))
@click.option(
    "--errors",
    type=click.Path(),
    help="Write out some errors to this file in csv format.",
)
@click.option("--normal", "log_level", flag_value="SUCCESS", default=True)
@click.option("--verbose", "log_level", help="Verbose mode.", flag_value="INFO")
@click.option("--debug", "log_level", help="Debug mode.", flag_value="DEBUG")
def ocr_column(filename: pathlib.Path, output, errors, log_level):
    """
    Read in the raw ocr from csv, transform it into street-based address transformation and apply basic error catching.
    """

    # set up logging

    logger.add(sys.stderr, format="<level>{message}</level>", level=log_level)

    # figure out our context
    page_id = filename.parent.name
    column_id = int(re.match(r"column-([0-9]+)", filename.name).group(1))
    logger.info("Considering column {} on page {}", column_id, page_id)
    prev_street_name = get_previous_street_name(column_id, output)

    # read in the raw ocr data
    ocr_data = pd.read_csv(filename)

    force = filename.with_name("force-ocr").exists()
    street_info = handle_data(ocr_data, page_id, prev_street_name, errors, force)

    with open(output, "w") as output_fp:
        output_csv = csv.DictWriter(
            output_fp,
            [
                "page",
                "column",
                "line_num",
                "street",
                "new",
                "old",
                "new_conf",
                "old_conf",
                "new_bbox",
                "old_bbox",
                "flag",
            ],
            quoting=csv.QUOTE_NONNUMERIC,
        )
        output_csv.writeheader()
        for street in street_info:
            if street.pairs:
                errors = street.check_assumptions()
                logger.success(
                    "{}: {} pairs, {} numeric order errors".format(
                        street.name, len(street.pairs), errors
                    )
                )
                street.output(column=column_id, outfile=output_csv)


def handle_data(
    ocr_data: pd.DataFrame, page_id: int, prev_street_name: str, error_file, force: bool
):
    height_mode = ocr_data["height"].mode()[0]  # mode is a series, just use the top
    ocr_data["error"] = ""

    # unfortunately, sometimes there's more than one "paragraph" in the way
    # the OCR segments the column, so we need to calcuate a unique line number
    ocr_data["line_num"] = ocr_data["line_num"] + ((ocr_data["par_num"] - 1) * 1000)

    # group it into horizontally-aligned groups
    grouped = ocr_data.groupby(["block_num", "par_num", "line_num"])

    current_street = Street(prev_street_name, page_id=page_id)

    if prev_street_name:
        streets = [current_street]
        logger.info("continuing with {}".format(prev_street_name))
    else:
        streets = []

    failed_groups = []
    error_count = 0
    success_count = 0

    for group_id, group in grouped:

        result = False
        row_height, texts = parse_ocr_row(group)
        combined_text = " ".join(x.text for x in texts)

        if row_height > 1.3 * height_mode or probable_street_name(combined_text):
            # this is a street name probably
            current_street = Street(name=combined_text, page_id=page_id)
            streets.append(current_street)
            result = True

        elif within(row_height, 0.2, height_mode):
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
        logger.warning(
            "{} ({:0.1%}) rejected OCR groups.".format(
                error_count, error_count / (error_count + success_count)
            )
        )
        if error_file:
            groups = [grouped.get_group(i) for i in failed_groups]
            failures = pd.concat(groups, axis=0, join="outer")
            failures.to_csv(error_file, quoting=csv.QUOTE_NONNUMERIC)
        if not force and error_count / (error_count + success_count) > 0.15:
            logger.error(
                "{}: Too many OCR errors, aborting. Fix the image, or reevaluate your life",
                page_id,
            )
            sys.exit(1)
    return streets


if __name__ == "__main__":
    # split target page into columnar json segementation files
    ocr_column()

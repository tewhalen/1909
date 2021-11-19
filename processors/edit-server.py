#!/usr/bin/env python
import os, pathlib
from numpy.lib.npyio import load
import pandas as pd

from flask import Flask, Response, request, send_from_directory
import jinja2

api = Flask(__name__)


"""This is quick and VERY VERY DIRTY"""


def load_ground_texts(path: pathlib.Path, page: int, column: int):
    ground_texts = {}
    gts = path.glob("p{:03}-c{:02}-*.gt.txt".format(page, column))
    for textfile in gts:
        text = textfile.read_text().strip()
        index = int(textfile.name.split("-")[-1].removesuffix(".gt.txt"))
        ground_texts[index] = text
    return ground_texts


@api.route("/")
def get_index():
    # serve up html files
    # NEVER DO THIS
    return send_from_directory(os.getcwd(), "column-1.html")


@api.route("/column<int:col>/")
def show_column(col):

    page = 1

    t = jinja2.Template(
        open(pathlib.Path(__file__).parent / "training_template.html").read()
    )

    # read in the raw ocr data
    ocr_data = pd.read_csv(
        pathlib.Path(os.getcwd()) / "column-{}-raw_ocr.csv".format(col)
    )

    # read in replacement texts and replace
    known_ground_texts = load_ground_texts(pathlib.Path(os.getcwd()), page, col)
    for i, text in known_ground_texts.items():
        ocr_data.loc[i, "text"] = text

    worst_q = ocr_data["conf"].quantile(0.2)
    # leaven in the top 20% most-confident
    best_q = ocr_data["conf"].quantile(0.8)

    filename = "column-{}.png".format(col)

    return t.render(
        ocr_data=ocr_data[~ocr_data["conf"].between(worst_q, best_q)],
        column_image=filename,
        prefix="p{:03}-c{:02}".format(page, col),
    )


@api.route("/<imagename>.png")
def get_image(imagename):
    # serve up images
    # DONT DO IT THIS WAY

    return send_from_directory(os.getcwd(), imagename + ".png")


@api.route("/<javascript>.js")
def get_js(javascript):
    # serve up javascript
    # THIS IS VERY BAD
    return send_from_directory(os.getcwd(), javascript + ".js")


@api.route("/p<int:page>-c<int:col>-<int:row>", methods=["POST"])
def post_new_text(page, col, row):
    # take in UNCHECKED data and AT EXTREME RISK, write it to a LOCAL file
    # NEVER DO THIS
    fn = "p{:03}-c{:02}-{:05}.gt.txt".format(page, col, row)
    text = request.form["text"].strip()
    # print(fn, repr(text))

    # ONLY A FOOL WOULD DO THE FOLLOWING
    open(fn, "w").write(text + "\n")

    return {}


if __name__ == "__main__":
    api.run(debug=True)

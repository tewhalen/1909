#!/usr/bin/env python
import os

from flask import Flask, Response, request, send_from_directory

api = Flask(__name__)


"""This is quick and VERY VERY DIRTY"""


@api.route("/")
def get_index():
    # serve up html files
    # NEVER DO THIS
    return send_from_directory(os.getcwd(), "column-1.html")


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
    print(fn, repr(text))

    # ONLY A FOOL WOULD DO THE FOLLOWING
    open(fn, "w").write(text + "\n")

    return {}


if __name__ == "__main__":
    api.run(debug=True)

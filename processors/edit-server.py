#!/usr/bin/env python
from flask import Flask, Response, request

api = Flask(__name__)


@api.route("/")
def get_index():
    return open("column-1.html").read()


@api.route("/<imagename>.png")
def get_image(imagename):
    return Response(open(imagename + ".png", "rb").read(), 200, mimetype="image/png")


@api.route("/<javascript>.js")
def get_js(javascript):
    return Response(
        open(javascript + ".js", "rb").read(), 200, mimetype="text/javascript"
    )


@api.route("/p<page>-c<col>-<row>", methods=["POST"])
def post_new_text(page, col, row):
    fn = "p{}-c{}-{}.gt.txt".format(page, col, row)
    text = request.form["text"].strip()
    print(fn, repr(text))
    open(fn, "w").write(text + "\n")

    return {}


if __name__ == "__main__":
    api.run(debug=True)

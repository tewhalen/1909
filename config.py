#!/usr/bin/env python

import pathlib

BASE_DIR = pathlib.Path(__file__).parent

TEMPLATES_DIR = BASE_DIR / "processors/templates"


class OCR:
    # Where the model is stored
    TESSDATADIR = BASE_DIR
    # the name of the model
    MODEL = "1909"
    # what page segmentation mode to use
    PSM = "6"

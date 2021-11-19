#!/usr/bin/env python3
import ast
import pathlib

import click
import jinja2
import pandas

TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"


class Book:
    def __init__(self, data_table):
        self.data_table = data_table
        self.pages = []
        for page_id, page_data_table in self.data_table.groupby("page"):

            self.pages.append(Page(page_id, page_data_table))

    def render(self):

        t = jinja2.Template(open(TEMPLATES_DIR / "book_index_template.html").read())

        return t.render(book=self)


class Page:
    def __init__(self, page_id, data_table: pandas.DataFrame):
        self.data_table = data_table
        self.page_id = "{:03}".format(page_id)

    def streets(self):
        return self.data_table["street"].unique()

    def addresses(self):
        return len(self.data_table)

    @property
    def confidence(self):
        "The minimum average confidence across the old/new columns"
        return min(
            self.data_table["new_conf"].mean(), self.data_table["old_conf"].mean()
        )


@click.command()
@click.argument("infile", type=click.Path(exists=True, path_type=pathlib.Path))
def reconstruct(infile: pathlib.Path):
    """Using a CSV file, reconstruct what the column may have looked like"""

    in_data = pandas.read_csv(
        infile,
    )
    book = Book(in_data)

    print(book.render())


if __name__ == "__main__":
    reconstruct()

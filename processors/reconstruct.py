#!/usr/bin/env python3
import ast
import pathlib

import click
import jinja2
import pandas

TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"


class Column:
    def __init__(self, col_id: int, data_table: pandas.DataFrame):
        self.column_id = col_id
        self.data_table = data_table

    @property
    def confidence(self):
        "The minimum average conficdence across the old/new columns"
        return min(
            self.data_table["new_conf"].mean(), self.data_table["old_conf"].mean()
        )

    def render(self):
        t = jinja2.Template(open(TEMPLATES_DIR / "correction_template.html").read())

        return t.render(
            streets=self.data_table.groupby("street"), column_image=self.image
        )

    @property
    def image(self):
        return "column-{}.png".format(self.column_id)

    @property
    def correction_href(self):
        return "column-{}.html".format(self.column_id)

    def streets(self):
        for street in self.data_table["street"].unique():
            yield {"name": street, "count": self.data_table["street"].eq(street).sum()}


class Page:
    def __init__(self, pagedir: pathlib.Path):
        self.data_table = pandas.read_csv(
            pagedir / "page.csv",
            converters={
                "new_bbox": ast.literal_eval,
                "old_bbox": ast.literal_eval,
                "new": str,
                "old": str,
            },
        )
        self.columns = []
        for page_col_id, data_table in self.data_table.groupby(["page", "column"]):
            page_id, col_id = page_col_id
            self.columns.append(Column(col_id, data_table))

    def render(self):

        t = jinja2.Template(open(TEMPLATES_DIR / "page_index_template.html").read())

        return t.render(page=self)


@click.command()
@click.argument("infile", type=click.Path(exists=True, path_type=pathlib.Path))
def reconstruct(infile: pathlib.Path):
    """Using a CSV file, reconstruct what the column may have looked like"""

    page = Page(infile)

    (infile / "index.html").write_text(page.render())
    for column in page.columns:
        (infile / column.correction_href).write_text(column.render())


if __name__ == "__main__":
    reconstruct()

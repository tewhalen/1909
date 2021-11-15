#!/usr/bin/env python3
import ast
import pathlib
import re

import click
import jinja2
import pandas


@click.command()
@click.argument("infile", type=click.Path(exists=True, path_type=pathlib.Path))
def reconstruct(infile: pathlib.Path):
    """Using a CSV file, reconstruct what the column may have looked like"""
    csv_in = pandas.read_csv(
        infile, converters={"new_bbox": ast.literal_eval, "old_bbox": ast.literal_eval}
    )

    column_id = int(re.match(r"column-([0-9]+)", infile.name).group(1))

    column_image = infile.with_name("column-{}.png".format(column_id))
    t = jinja2.Template(
        open(pathlib.Path(__file__).parent / "correction_template.html").read()
    )

    print(t.render(streets=csv_in.groupby("street"), column_image=column_image))


if __name__ == "__main__":
    reconstruct()

"""Cli for NOA-Beyond Postprocess:Aggregate processor.

This interface and processor are used for aggregating EO data.
"""

from __future__ import annotations
import sys
import logging
from pathlib import Path

import click
from click import Argument  # , Option

# Appending the module path in order to have a kind of cli "dry execution"
sys.path.append(str(Path(__file__).parent / ".."))

from noapostaggregate import postaggregate  # noqa:402 pylint:disable=wrong-import-position

logger = logging.getLogger(__name__)


@click.group(
    help=(
        "Processes EO data from [PATH] according to parameters defined "
        "in the [CONFIG_FILE]."
    )
)
@click.option(
    "--log",
    default="warning",
    help="Log level (optional, e.g. DEBUG. Default is WARNING)",
)
def cli(log):
    """Click cli group for processing cli commands"""
    numeric_level = getattr(logging, log.upper(), "WARNING")
    logging.basicConfig(level=numeric_level, format="%(asctime)s %(message)s")


@cli.command(
    help=(
        "Aggregate according to [agg_function] argument for files in [path]."
    )
)
@click.argument("agg_function", required=True)
@click.argument("path", required=True)
@click.argument("config_file", required=False)
def aggregate(agg_function: Argument | str, path: Argument | str, config_file: Argument | str) -> None:
    """
    Instantiate Postprocess class and process path contents.

    Parameters:
        agg_function (click.Argument | str): Aggregate function [median, average, min, max]
        path (click.Argument | str): Path to look for files
        config_file (click.Argument | str): config json file
    """
    if path:
        logger.debug("Cli query using config file: %s", config_file)

    click.echo("Processing files in path %s:\n", path)
    process = postaggregate.Aggregate(path, config_file)
    process.from_path(agg_function)


if __name__ == "__main__":  # pragma: no cover
    cli()

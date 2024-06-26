"""Cli for NOA-Beyond Preprocess processor.

This interface and processor are used to preprocess downloaded EO data.
"""

from __future__ import annotations
import sys
import logging
from pathlib import Path

import click
from click import Argument  # , Option

# Appending the module path in order to have a kind of cli "dry execution"
sys.path.append(str(Path(__file__).parent / ".."))

from noapreprocess import preprocess  # noqa:402 pylint:disable=wrong-import-position

logger = logging.getLogger(__name__)


@click.group(
    help=(
        "Processes downloaded EO data to [PATH] according to parameters defined "
        "in the [CONFIG_FILE]."
    )
)
@click.option(
    "--log",
    default="warning",
    help="Log level (optional, e.g. DEBUG. Default is WARNING)",
)
def cli(log):
    """Click cli group for query, download, describe cli commands"""
    numeric_level = getattr(logging, log.upper(), "WARNING")
    logging.basicConfig(level=numeric_level, format="%(asctime)s %(message)s")


@cli.command(
    help=(
        "Generic unzipping and COG transforming of files in [PATH]."
    )
)
@click.argument("path", required=True)
@click.argument("config_file", required=False)
def process(path: Argument | str, config_file: Argument | str) -> None:
    """
    Instantiate Preprocess class and process path contents.

    Parameters:
        path (click.Argument | str): Path to look for files
        config_file (click.Argument | str): config json file
    """
    if config_file:
        logger.debug("Cli query for config file: %s", config_file)

    click.echo("Processing files in path %s:\n", path)
    process = preprocess.Preprocess(path, config_file)
    process.from_path()


if __name__ == "__main__":  # pragma: no cover
    cli()

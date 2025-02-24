"""Cli for NOA-Beyond Harvester processor.

This interface and processor are used to query and download EO data
from various data providers: Copernicus and Earthdata.
"""

from __future__ import annotations
import sys
import json
import logging
from pathlib import Path

import click
from click import Argument, Option

import openeo

from noaopeneo.monthly_median import aggegate_per_tile
from noaopeneo import utils

# Appending the module path in order to have a kind of cli "dry execution"
sys.path.append(str(Path(__file__).parent / ".."))

logger = logging.getLogger(__name__)


@click.group(
    help=(
        "Product generation from Copernicus CDSE using openeo python client "
        "according to parameters as defined in the [CONFIG_FILE]."
        "It can also receive a [SHAPE_FILE] path as an argument, in order "
        "for the bounding box to be defined there instead of the [CONFIG_FILE]."
    )
)
@click.option(
    "--log",
    default="warning",
    help="Log level (optional, e.g. DEBUG. Default is WARNING)",
)
def cli(log):
    """Click cli group for product generation"""
    numeric_level = getattr(logging, log.upper(), "WARNING")
    logging.basicConfig(level=numeric_level, format="%(asctime)s %(message)s")


@cli.command(
    help=(
        "Monthly cloud free composite."
        "You can also provide (optional) a [SHAPE_FILE] path in order to define "
        "the bounding box there instead of the config file."
    )
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Shows the progress indicator (for Copernicus only)",
)
@click.option(
    "--bbox_only",
    "-bb",
    is_flag=True,
    help="Only use multipolygon total bbox, not individual",
)
@click.argument("config_file", required=True)
@click.argument("shape_file", required=False)
@click.option("--output_path", default="./data", help="Output path")
@click.option(
    "--tiles",
    "-t",
    multiple=True,
    help="TileId(s). Can be set multiple times"
)
def cfmc(
    config_file: Argument | str,
    shape_file: Argument | str,
    output_path: Option | str,
    tiles: Option | tuple[str],
    bbox_only: Option | bool,
    verbose: Option | bool,
) -> None:
    """
    Produces cloud free monthly composite for given bbox or shape.

    Parameters:
        config_file (click.Argument | str): config json file listing
            providers, collections and search terms
        verbose (click.Option | bool): to show download progress indicator or not.
    """
    logger.debug("Config file: %s", config_file)
    logger.debug("Output path: %s", output_path)

    if shape_file:
        logger.debug("Shapefile path: %s", shape_file)
        _shape_file_bbox_list = utils.get_bbox_from_shp(shape_file, bbox_only)

    with open(config_file, encoding="utf8") as f:
        _config = json.load(f)

    logger.debug("Trying to connect to cdse openeo")
    connection = openeo.connect("https://openeo.dataspace.copernicus.eu").authenticate_oidc()
    for tile in tiles:
        aggegate_per_tile(connection, tile)


if __name__ == "__main__":  # pragma: no cover
    cli()

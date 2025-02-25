"""Cli for NOA-Beyond CDSE OpenEO operations.

This interface and processor are used to perform batch operations
using the openEO python library for CDSE provider and data.
"""

from __future__ import annotations
import os
import sys
import json
import logging
from pathlib import Path

import click
from click import Argument, Option

import openeo

from noaopeneo.monthly_median import month_median
from noaopeneo import utils

# Appending the module path in order to have a kind of cli "dry execution"
sys.path.append(str(Path(__file__).parent / ".."))

logger = logging.getLogger(__name__)


@click.group(
    help=(
        "Product generation from Copernicus CDSE using openeo python client "
        "according to parameters as defined in the [CONFIG_FILE]."
        "A GeoJson [SHAPE_FILE] path is required as an argument "
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
    "--bbox_only",
    "-bb",
    is_flag=True,
    help="Only use multipolygon total bbox, not individual",
)
@click.argument("config_file", required=True)
@click.argument("shape_file", required=True)
@click.option("--output_path", default="./data", help="Output path")
def cfmc(
    config_file: Argument | str,
    shape_file: Argument | str,
    output_path: Option | str,
    bbox_only: Option | bool
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

    logger.debug("Shapefile path: %s", shape_file)
    shape = shape_file
    if bbox_only:
        shape = utils.get_bbox_from_shp(shape_file, bbox_only)

    with open(config_file, encoding="utf8") as f:
        _config = json.load(f)

    logger.debug("Trying to connect to cdse openeo")
    # client id: env: OPENEO_CLIENT_ID
    # client secret: env: OPENEO_CLIENT_SECRET
    client_id = os.getenv("OPENEO_CLIENT_ID", None)
    client_secret = os.getenv("OPENEO_CLIENT_SECRET", None)
    connection = openeo.connect(
        "https://openeo.dataspace.copernicus.eu"
    ).authenticate_oidc_client_credentials(
        client_id=client_id,
        client_secret=client_secret
    )

    max_cloud_cover = _config["max_cloud_cover"]

    month_median(
        connection,
        _config["start_date"],
        _config["end_date"],
        shape,
        max_cloud_cover=max_cloud_cover
    )


@cli.command(
    help=(
        "Job info"
    )
)
@click.argument("job_id", required=True)
def job_info(job_id: Argument | str,):
    """ Please get the job info """
    logger.debug("Trying to connect to cdse openeo")
    # client id: env: OPENEO_CLIENT_ID
    # client secret: env: OPENEO_CLIENT_SECRET
    client_id = os.getenv("OPENEO_CLIENT_ID", None)
    client_secret = os.getenv("OPENEO_CLIENT_SECRET", None)
    connection = openeo.connect(
        "https://openeo.dataspace.copernicus.eu"
    ).authenticate_oidc_client_credentials(
        client_id=client_id,
        client_secret=client_secret
    )
    print(connection.get(f"/jobs/{job_id}", expected_status=200).json())


@cli.command(
    help=(
        "Job delete"
    )
)
@click.argument("job_id", required=True)
def job_delete(job_id: Argument | str,):
    """ Please get the job info """
    logger.debug("Trying to connect to cdse openeo")
    # client id: env: OPENEO_CLIENT_ID
    # client secret: env: OPENEO_CLIENT_SECRET
    client_id = os.getenv("OPENEO_CLIENT_ID", None)
    client_secret = os.getenv("OPENEO_CLIENT_SECRET", None)
    connection = openeo.connect(
        "https://openeo.dataspace.copernicus.eu"
    ).authenticate_oidc_client_credentials(
        client_id=client_id,
        client_secret=client_secret
    )
    print(connection.delete(f"/jobs/{job_id}", expected_status=204))


if __name__ == "__main__":  # pragma: no cover
    cli()

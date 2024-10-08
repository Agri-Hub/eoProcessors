"""Cli for NOA-Beyond Harvester processor.

This interface and processor are used to query and download EO data
from various data providers: Copernicus and Earthdata.
"""

from __future__ import annotations
import sys
import logging
from pathlib import Path

import click
from click import Argument, Option

# Appending the module path in order to have a kind of cli "dry execution"
sys.path.append(str(Path(__file__).parent / ".."))

from noaharvester import harvester  # noqa:402 pylint:disable=wrong-import-position

logger = logging.getLogger(__name__)


@click.group(
    help=(
        "Queries and/or Downloads data from Copernicus and EarthData services "
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
    """Click cli group for query, download, describe cli commands"""
    numeric_level = getattr(logging, log.upper(), "WARNING")
    logging.basicConfig(level=numeric_level, format="%(asctime)s %(message)s")


@cli.command(help="Describe collection query fields (Copernicus only)")
@click.argument("config_file", required=True)
def describe(config_file: Argument | str) -> None:
    """
    Instantiate Harvester Class and call "describe" for available query terms
    of the selected collections (only available for Copernicus)

    Parameters:
        config_file (click.Argument | str): config json file listing
            providers, collections and search terms
    """
    if config_file:
        logger.debug("Cli describing for config file: %s", config_file)

        harvest = harvester.Harvester(config_file=config_file)
        click.echo("Available parameters for selected collections:\n")
        harvest.describe()


@cli.command(
    help=(
        "Downloads data from the selected providers and query terms. "
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
def download(
    config_file: Argument | str,
    shape_file: Argument | str,
    output_path: Option | str,
    bbox_only: Option | bool,
    verbose: Option | bool,
) -> None:
    """
    Instantiate Harvester class and call download function.
    Downloads all relevant data as defined in the config file.

    Parameters:
        config_file (click.Argument | str): config json file listing
            providers, collections and search terms
        verbose (click.Option | bool): to show download progress indicator or not.
    """
    if config_file:
        logger.debug("Cli download for config file: %s", config_file)

        click.echo("Downloading...\n")
        click.echo(output_path)
        harvest = harvester.Harvester(
            config_file=config_file,
            output_path=output_path,
            shape_file=shape_file,
            verbose=verbose,
            bbox_only=bbox_only,
        )
        harvest.download_data()
        click.echo("Done.\n")


@cli.command(
    help=(
        "Download data from the provided provider and URI list. "
        "Command also expects the provider credentials but can also "
        "get them from the optional config file."
    )
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Shows the progress indicator (for Copernicus only)",
)
@click.argument("config_file", required=True)
@click.argument("provider", required=True)
@click.option("--output_path", default="./data", help="Output path")
@click.option("--uri", "-u", multiple=True)
def from_uri_list(
    config_file: Argument | str,
    provider: Argument | str,
    output_path: Option | str,
    uri: Option | tuple[str],
    verbose: Option | bool,
) -> None:
    """
    Instantiate Harvester class and call download function.
    Downloads all relevant data as defined in the config file.

    Parameters:
        config_file (click.Argument | str): config json file listing
            providers, collections and search terms
        provider (click.Argument | str): provider to download from
        output_path (click.Option | str): where to download to
        uri (click.Option | tuple[str]): A tuple of uris to download
        verbose (click.Option | bool): to show download progress indicator or not.
    """
    if config_file:
        logger.debug("Cli download for config file: %s", config_file)

        click.echo("Downloading...\n")
        click.echo(output_path)
        harvest = harvester.Harvester(
            config_file=config_file,
            output_path=output_path,
            verbose=verbose,
            from_uri=True
        )
        # TODO either make it public or provide a public interface
        harvest._resolve_provider_instance(provider)
        harvest.download_from_uri_list(uri)
        click.echo("Done.\n")


@cli.command(
    help=(
        "Queries for available products according to the config file."
        "You can also provide (optional) a [SHAPE_FILE] path in order to define "
        "the bounding box there instead of the config file."
    )
)
@click.argument("config_file", required=True)
@click.argument("shape_file", required=False)
@click.option(
    "--bbox_only",
    "-bb",
    is_flag=True,
    help="Only use multipolygon total bbox, not individual",
)
def query(
    config_file: Argument | str, shape_file: Argument | str, bbox_only: Option | bool
) -> None:
    """
    Instantiate Harvester class and call query function in order to search for
    available products for the selected collections.

    Parameters:
        config_file (click.Argument | str): config json file listing
            providers, collections and search terms
    """
    if config_file:
        logger.debug("Cli query for config file: %s", config_file)

        click.echo("Querying providers for products:\n")
        harvest = harvester.Harvester(
            config_file, shape_file=shape_file, bbox_only=bbox_only
        )
        harvest.query_data()


if __name__ == "__main__":  # pragma: no cover
    cli()

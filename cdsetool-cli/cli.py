import click
from cdsetool_cli.utils import download_data, available_parameters


@click.command(
    help=(
        "Downloads Copernicus data according to parameters as defined in the [CONFIG_FILE],"
        " or shows available query parameters for Satellites present in the [CONFIG_FILE]"
    )
)
@click.option(
    "--download",
    "-d",
    is_flag=True,
    help="Downloads available Copernicus data according to CONFIG_FILE",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Shows the progress indicator (for download option only)",
)
@click.option(
    "--parameters",
    "-p",
    is_flag=True,
    help="Show available query Parameters for Satellites present in CONFIG_FILE",
)
@click.argument("config_file", required=True)
def cli(download, parameters, config_file, verbose):
    if parameters:
        available_parameters(config_file)
    elif download:
        download_data(config_file, verbose)
    else:
        click.echo("Please select at least one option (-d, -p)")


if __name__ == "__main__":
    cli()

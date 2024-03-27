import os
import json
import click

from cdsetool.query import query_features
from cdsetool.query import describe_collection
from cdsetool.download import download_features
from cdsetool.credentials import Credentials
from cdsetool.monitor import StatusMonitor


def available_parameters(config_file):

    with open(f"config/{config_file}") as f:
        config = json.load(f)

    for satellite, _ in config.items():
        search_terms = describe_collection(satellite).keys()
        click.echo(f"{satellite} available search terms: \n {search_terms}\n")


def download_data(config_file, verbose):

    credentials = Credentials(os.environ["login"], os.environ["password"])
    monitor = StatusMonitor() if verbose else False

    with open(f"config/{config_file}") as f:
        config = json.load(f)

    for satellite, search_terms in config.items():
        # wait for all batch requests to complete, returning list
        features = list(query_features(satellite, search_terms))
        print(f"Available items for {satellite}: {len(features)} \n")

    for satellite, search_terms in config.items():

        download_path = "/app/data"
        features = list(query_features(satellite, search_terms))

        list(download_features(
            features,
            download_path,
            {
                "concurrency": 4,
                "monitor": monitor,
                "credentials": credentials
            }))

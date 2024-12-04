"""Copernicus data provider class. Implements Provider ABC."""

from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
import click

from cdsetool.credentials import Credentials
from cdsetool.monitor import StatusMonitor
from cdsetool.query import query_features, describe_collection
from cdsetool.download import download_features, download_feature

from noaharvester.providers import DataProvider

logger = logging.getLogger(__name__)


class Copernicus(DataProvider):
    """
    The Copernicus service provider, implementing query, download and describe collection
    functions. It uses (wraps) the cdsetool Python package.

    Properties:
        credentials: returns the Credentials (cdsetool) instance

    Methods:
        query (item): Query a collection based on search terms in [item].
                    Item also includes the collection name.
        download (item): Download a collection [item].
        describe (collection): Output available search terms of [collection].
    """

    def __init__(self, output_path, verbose: bool = False) -> Copernicus:
        """
        Copernicus provider. Constructor also performs the login operation based
        on credentials present in the .netrc file.

        Parameters:
            verbose (bool): If True, download progress indicator will be visible
        """
        super().__init__(output_path=output_path)

        # From .netrc
        logger.debug("Checking Copernicus credentials - trying to acquire token")
        self._credentials = Credentials(
            username=os.getenv("COPERNICUS_LOGIN"),
            password=os.getenv("COPERNICUS_PASSWORD")
        )

        self._downloaded_feature_ids = []
        self.verbose = verbose
        self._download_uri_prefix = "https://catalogue.dataspace.copernicus.eu/download/"

    @property
    def credentials(self) -> Credentials:
        """Return the credentials instance."""
        return self._credentials

    def query(self, item: dict) -> tuple[str, int]:
        """
        Query Copernicus for item["collection"], item["search_terms"]] items.

        Parameters:
            item (dict): Dictionary as per config file structure.

        Returns:
            tuple (str, int):  Collection name, sum of available items.
        """
        logger.debug("Search terms: %s", item["search_terms"])

        features = list(query_features(item["collection"], item["search_terms"]))
        click.echo(
            f"Total available items for {item['collection']}: {len(features)} \n"
        )

        return item["collection"], len(features)

    def describe(self, collection: str) -> tuple[str, list]:
        """
        Ask Copernicus for describe the collection.

        Parameters:
            collection (string): The collection to be queried.

        Returns:
            tuple (string, list):  Collection name, list of available search terms.
        """
        search_terms = describe_collection(collection).keys()
        click.echo(f"{collection}:\n {search_terms}\n")

        return collection, list(search_terms)

    def single_download(self, uuid: str, title: str) -> Path:
        """
        Utilize the minimum CSETool interface for downloading single items.
        CDSETool utilizes id and title of the Feature and also some optional
        values from Options.
        """
        feature = {
            "properties": {
                "title": title,
                "services": {
                    "download": {
                        "url": self._download_uri_prefix + uuid
                    }
                }
            }
        }

        options = {
            "monitor": StatusMonitor() if self.verbose else False,
            "credentials": self.credentials,
            "logger": logger
        }

        filename = download_feature(feature=feature, path=self._download_path, options=options)
        return Path(self._download_path, filename)
        # TODO Verify checksum

    def download(self, item: dict) -> tuple[str, int]:
        """
        Download from Copernicus from item["collection"] the item["search_terms"]] items.
        Download is using a concurrency setting of 4 threads and stored in local execution
        folder, under /data.

        Parameters:
            item (dict): Dictionary as per config file structure.

        Returns:
            tuple (string, int):  Collection name, sum of downloaded files.
        """
        downloaded_files = []
        logger.debug("Download search terms: %s", item["search_terms"])

        if not str(self._download_path).startswith("s3"):
            self._download_path.mkdir(parents=True, exist_ok=True)

        features = list(query_features(item["collection"], item["search_terms"]))
        initial_query_return = len(features)

        for feature in features:
            if feature["properties"]["status"] == "ONLINE":
                if feature["id"] not in self._downloaded_feature_ids:
                    self._downloaded_feature_ids.append(feature["id"])
                else:
                    features.remove(feature)
        click.echo(
            f"Total items to be downloaded for {item['collection']}: {len(features)}. "
            f"Avoided {initial_query_return - len(features)} duplicates.\n"
        )

        sys.stdout.flush()

        if features:
            downloaded_files = list(
                download_features(
                    features,
                    self._download_path,
                    {
                        "concurrency": 4,
                        "monitor": StatusMonitor() if self.verbose else False,
                        "credentials": self.credentials,
                        "logger": logger
                    },
                )
            )

        return item["collection"], len(downloaded_files)

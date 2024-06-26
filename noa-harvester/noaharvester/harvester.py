"""Main Harvester module, calling abstract provider functions."""

from __future__ import annotations

import logging
import json

from noaharvester.providers import DataProvider, copernicus, earthdata, earthsearch
from noaharvester import utils

logger = logging.getLogger(__name__)


class Harvester:
    """
    Harvester main class and module. Loads search items and calls providers instances.

    Methods:
        query_data: Search for items (products) in collections.
        download_data: Download items from providers and collections.
        describe: Describe available search terms of collections (Copernicus only)
    """

    def __init__(
        self, config_file: str, shape_file: str = None, verbose: bool = False
    ) -> Harvester:
        """
        Harvester class. Constructor reads and loads the search items json file.

        Parameters:
            config_file (str): Config filename (json) which includes all search items.
            shape_file (str - Optional): Read and use shapefile instread of config coordinates.
            verbose (bool - Optional): Indicate if Copernicus download progress is verbose.
        """
        self._config_filename = config_file
        self._verbose = verbose

        self._search_items: list = []
        self._providers = {}
        self._shape_file_bbox = None

        if shape_file:
            logger.debug("Using shapefile from path: %s", shape_file)
            self._shape_file_bbox = str(utils.get_bbox_from_shp(shape_file)).strip()[
                1:-1
            ]

        with open(config_file, encoding="utf8") as f:
            self._config = json.load(f)

        for item in self._config:
            if self._shape_file_bbox:
                item["search_terms"]["box"] = self._shape_file_bbox
            logger.debug("Appending search item: %s", item)
            self._search_items.append(item)

    def query_data(self) -> None:
        """
        For every item in config file loaded by Harvester instance, create or retrieve
        the provider instance and query for available collection items.
        """
        for item in self._search_items:
            logger.debug(
                "Querying %s collection %s",
                item.get("provider"),
                item.get("collection"),
            )

            provider = self._resolve_provider_instance(item.get("provider"))
            provider.query(item)

    def download_data(self) -> None:
        """
        For every item in config file loaded by Harvester instance, create or retrieve
        the provider instance and download all available collection items according to
        search terms for that item.
        """
        for item in self._search_items:
            logger.debug(
                "Download from %s and collection: %s",
                item.get("provider"),
                item.get("collection"),
            )

            provider = self._resolve_provider_instance(item.get("provider"))
            provider.download(item)

    def describe(self) -> None:
        """
        For every item in config file loaded by Harvester instance, create or retrieve
        the Copernicus provider instance and describe the collection (available search
        terms).
        """
        for item in self._search_items:
            if item.get("provider") == "copernicus":
                logger.debug(
                    "Describing from: %s, collection: %s",
                    item.get("provider"),
                    item.get("collection"),
                )
                provider = self._resolve_provider_instance(item.get("provider"))
                provider.describe(item.get("collection"))

    def _resolve_provider_instance(self, provider) -> DataProvider:
        if provider not in self._providers:
            logger.debug(
                "Provider: %s DataProvider instance not found. Creating new.", provider
            )
            if provider == "copernicus":
                self._providers[provider] = copernicus.Copernicus(self._verbose)
            elif provider == "earthdata":
                self._providers[provider] = earthdata.Earthdata()
            elif provider == "earthsearch":
                self._providers[provider] = earthsearch.Earthsearch()
        else:
            logger.info("Provider: %s DataProvider instance found.", provider)
        return self._providers[provider]

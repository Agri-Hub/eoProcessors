"""Main Harvester module, calling abstract provider functions."""

from __future__ import annotations
from copy import deepcopy

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
        self,
        config_file: str,
        output_path: str = None,
        shape_file: str = None,
        verbose: bool = False,
        bbox_only: bool = False,
        from_uri: bool = False
    ) -> Harvester:
        """
        Harvester class. Constructor reads and loads the search items json file.

        Parameters:
            config_file (str): Config filename (json) which includes all search items.
            shape_file (str - Optional): Read and use shapefile instead of config coordinates.
            verbose (bool - Optional): Indicate if Copernicus download progress is verbose.
        """
        self._config_filename = config_file
        self._output_path = output_path
        self._verbose = verbose

        self._search_items: list = []
        self._providers = {}
        self._shape_file_bbox_list = None

        if shape_file:
            logger.debug("Using shapefile from path: %s", shape_file)
            self._shape_file_bbox_list = utils.get_bbox_from_shp(shape_file, bbox_only)

        with open(config_file, encoding="utf8") as f:
            self._config = json.load(f)

        if from_uri:
            pass
        else:
            for item in self._config:
                if self._shape_file_bbox_list:
                    for bbox in self._shape_file_bbox_list:
                        sub_item = deepcopy(item)
                        sub_item["search_terms"]["box"] = str(bbox).strip()[1:-1]
                        self._search_items.append(sub_item)
                        logger.debug("Appending search item: %s", sub_item)
                else:
                    self._search_items.append(item)
                    logger.debug("Appending search item: %s", item)
        logger.debug("Total search items: %s", len(self._search_items))

    def download_from_uri_list(self) -> None:
        pass

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
                self._providers[provider] = copernicus.Copernicus(self._output_path, self._verbose)
            elif provider == "earthdata":
                self._providers[provider] = earthdata.Earthdata(self._output_path)
            elif provider == "earthsearch":
                self._providers[provider] = earthsearch.Earthsearch(self._output_path)
        else:
            logger.info("Provider: %s DataProvider instance found.", provider)
        return self._providers[provider]

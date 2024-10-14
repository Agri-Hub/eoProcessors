"""Earthdata data provider class. Implements Provider ABC."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
import requests
from pqdm.threads import pqdm

import click
import pystac_client

from noaharvester.providers import DataProvider


logger = logging.getLogger(__name__)


class Earthsearch(DataProvider):
    """
    The Earthsearch cloud provider, implementing STAC search and download
    functions. It uses PySTAC client to perform the search operations.
    TODO: for now, it only downloads S2 L2A COGs.

    Methods:
        query (item): Query the S2 L2A COGs collection based on search terms in [item].
        download (item): Download an [item].
    """

    def __init__(self, output_path) -> Earthsearch:
        """
        Earthsearch cloud provider.
        """
        super().__init__(output_path=output_path)

        logger.debug("Earthsearch provider. No credentials needed.")
        self._downloaded_files = []
        self._STAC_URL = "https://earth-search.aws.element84.com/"

    def query(self, item: dict) -> tuple[str, int]:
        """
        Query S2 L2A COGs collection for item["search_terms"] items.

        Parameters:
            item (dict): Dictionary as per config file structure.

        Returns:
            tuple (str, int):  Collection name, sum of available items.
        """
        logger.debug("Search terms: %s", item["search_terms"])

        results = self._search_stac_collection(item)

        click.echo(f"Available items for {item['collection']}: {len(results.items)}")
        return item["collection"], len(results.items)

    def single_download(self, uri: str) -> tuple[str, int]:
        logger.error("Not implemented for Earthsearch provider")
        pass

    def download(self, item: dict) -> tuple[str, int]:
        """
        Download is using a concurrent http connections setting of 8 threads and stored in local execution
        folder, under /data.

        Parameters:
            item (dict): Dictionary as per config file structure.

        Returns:
            tuple (string, int):  Collection name, sum of downloaded files.
        """
        logger.debug("Download search terms: %s", item["search_terms"])

        file_items = []

        results = self._search_stac_collection(item)

        for asset in item["assets"]:
            for result in results.items:
                try:
                    if str(result.assets[asset].href).startswith("s3"):
                        logger.warning(
                            "This is a 'requester pays' non public asset. Cannot download."
                        )
                        continue
                    file_to_store = Path(
                        self._download_path,
                        Path(
                            result.id
                            + "_"
                            + Path(result.assets[asset].href).stem
                            + ".tif"
                        ),
                    )
                    if file_to_store not in self._downloaded_files:
                        logger.debug("href: %s", (result.assets[asset].href))
                        self._downloaded_files.append(file_to_store)
                        file_items.append([file_to_store, result.assets[asset].href])
                except KeyError:
                    logger.info("There is no asset: %s for %s", asset, result.id)
        if file_items:
            click.echo(
                f"Total items to be downloaded for {item['collection']}: {len(file_items)} \n"
                f"Avoided {len(results.items) - len(file_items)} duplicates or private assets."
            )
            self._download_path.mkdir(parents=True, exist_ok=True)

            results = pqdm(file_items, self._download_file, n_jobs=8)

        return item["collection"], len(file_items)

    def describe(self, collection):
        """Not implemented for Earthsearch. Service is not provided."""
        logger.error("Describe is not available for Earthdata.")
        raise NotImplementedError(
            "Earthdata (earthaccess) does not have a describe collection function"
        )

    def _search_stac_collection(self, item: dict) -> tuple[str, int]:
        """
        Search from Earthsearch item[collection] and item[version] for item["search_terms"]] items.

        Parameters:
            item (dict): Dictionary as per config file structure.

        Returns:
            tuple (string, int):  Collection name, sum of downloaded files.
        """
        logger.debug("Searching. Arguments: %s", item["search_terms"])

        search_terms = item["search_terms"]

        # INFO: adding the version number of this provider (v0 or v1). It seems
        # that v1 has more products but lets TODO check that in the
        # near future
        catalog = pystac_client.Client.open(self._STAC_URL + item["version"])
        catalog.add_conforms_to("ITEM_SEARCH")

        results = catalog.search(
            collections=[item["collection"]],
            bbox=str(search_terms["box"]),
            datetime=[search_terms["startDate"], search_terms["completionDate"]],
            query={"eo:cloud_cover": {"lt": search_terms.get("cloud_cover_lt", 100)}},
        ).item_collection()

        return results

    # TODO put this in utils
    def _download_file(self, file_item):

        timeout_in_sec = 60
        filename = str(file_item[0])
        response = requests.get(file_item[1], stream=True, timeout=timeout_in_sec)
        if response.status_code == 200:
            if not file_item[0].is_file():
                with open(filename, "wb") as f:
                    # This is to cap memory usage for large files at 1MB per write to disk per thread
                    # https://docs.python-requests.org/en/latest/user/quickstart/#raw-response-content
                    # TODO check if this is response.raw or response.content
                    logger.debug("Downloading %s", filename)
                    shutil.copyfileobj(response.raw, f, length=1024 * 1024)
            else:
                logger.debug("File %s already exists", filename)
        else:
            logger.error("Failed to download file: %s", filename)

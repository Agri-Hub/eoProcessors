"""Earthdata data provider class. Implements Provider ABC."""

from __future__ import annotations

import logging
import click

import earthaccess

from noaharvester.providers import DataProvider


logger = logging.getLogger(__name__)


class Earthdata(DataProvider):
    """
    The Earthdata service provider, implementing query and download
    functions. It uses (wraps) the earthaccess Python package.

    Methods:
        query (item): Query a collection based on search terms in [item].
                Item also includes the collection name.
        download (item): Download a collection [item].
        describe (collection): Output available search terms of [collection].
    """

    def __init__(self, output_path) -> Earthdata:
        """
        Earthdata provider. Constructor also performs the login operation based
        on credentials present in the .netrc file.
        """
        super().__init__(output_path=output_path)

        # From .netrc
        logger.debug("Checking Earthdata credentials - trying to acquire token")
        self._downloaded_links = []
        earthaccess.login()

    def query(self, item: dict) -> tuple[str, int]:
        """
        Query Earthdata for item["collection"], item["search_terms"]] items.

        Parameters:
            item (dict): Dictionary as per config file structure.

        Returns:
            tuple (str, int):  Collection name, sum of available items.
        """
        logger.debug("Search terms: %s", item["search_terms"])

        search_terms = item["search_terms"]
        bbox = tuple(float(i) for i in search_terms["box"].split(","))
        start_date = search_terms["startDate"]
        end_date = search_terms["completionDate"]

        results = earthaccess.search_data(
            short_name=search_terms["short_name"],
            cloud_hosted=True,
            bounding_box=bbox,
            temporal=(start_date, end_date),
        )
        click.echo(f"Available items for {item['collection']}: {len(results)}")
        return item["collection"], len(results)

    def single_download(self, uri: str) -> tuple[str, int]:
        logger.error("Not implemented for Earthdata provider")
        pass


    def download(self, item: dict) -> tuple[str, int]:
        """
        Download from Earthdata from item["collection"] the item["search_terms"]] items.
        Download is using a concurrency setting of 8 threads and stored in local execution
        folder, under /data.

        Parameters:
            item (dict): Dictionary as per config file structure.

        Returns:
            tuple (string, int):  Collection name, sum of downloaded files.
        """
        logger.debug("Download search terms: %s", item["search_terms"])

        self._download_path.mkdir(parents=True, exist_ok=True)
        search_terms = item["search_terms"]

        bbox = tuple(float(i) for i in search_terms["box"].split(","))
        start_date = search_terms["startDate"]
        end_date = search_terms["completionDate"]

        results = earthaccess.search_data(
            short_name=search_terms["short_name"],
            cloud_hosted=True,
            bounding_box=bbox,
            temporal=(start_date, end_date),
        )
        initial_results = len(results)

        for result in results.copy():
            if result.data_links() not in self._downloaded_links:
                self._downloaded_links.append(result.data_links())
            else:
                results.remove(result)
        click.echo(
            f"Total items to be downloaded for {item['collection']}: {len(results)} \n"
            f"Avoided {initial_results - len(results)} duplicates."
        )
        if results:
            earthaccess.download(results, self._download_path)
        return item["collection"], len(results)

    def describe(self, collection):
        """Not implemented for Earthdata. Service is not provided."""
        logger.error("Describe is not available for Earthdata.")
        raise NotImplementedError(
            "Earthdata (earthaccess) does not have a describe collection function"
        )

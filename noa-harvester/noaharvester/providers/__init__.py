"""Abstract Data Provider class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class DataProvider(ABC):
    """
    Abstract Data Provider.

    Methods:
        query: Query for specific search terms.
        download: Download items based on search terms.
        describe(optional): Describe collection.
    """

    def __init__(self, output_path) -> DataProvider:
        """
        Instantiates a new Data Provider class.

        Attributes:
            _download_path: Data are stored under /data of local execution folder.
        """
        if not output_path:
            output_path = "./data"
        if not output_path.startswith("s3"):
            self._download_path = Path(output_path).resolve()
        else:
            self._download_path = output_path

    # @property
    # def config(self):
    #     return self._config

    @abstractmethod
    def query(self, item):
        """
        Query data provider for collection items.
        """

    @abstractmethod
    def download(self, item):
        """
        Download data for collection items.
        """

    @abstractmethod
    def single_download(self, uuid, title) -> Path:
        """
        Download of a single item, by providing its uuid and title.
        """

    @abstractmethod
    def describe(self, collection):
        """
        Describe available collection query parameters.
        """

"""Main Ingest module."""
from __future__ import annotations
from pathlib import Path

from stactools.sentinel2.commands import create_item


class Ingest:
    """
    A class
    """

    def __init__(
        self,
        config: str | None
    ) -> Ingest:
        """
        Ingest main class implementing single and batch item creation.
        """
        if config:
            self._config = config

    def single_item(self, path):
        """
        Just an item
        """

        item = create_item(path)

        # Define the path to save the JSON file
        json_file_path = str(Path(Path(path).parent, "output.json"))

        # Save the item as a JSON file
        item.save_object(dest_href=json_file_path)

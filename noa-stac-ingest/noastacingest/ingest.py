"""Main Ingest module."""
from __future__ import annotations
from pathlib import Path

from stactools.sentinel1.commands import create_sentinel1_command as create_item_s1
from stactools.sentinel2.commands import create_item as create_item_s2


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
        filename = Path(path).absolute()
        platform = filename.name.split("_")[0]
        satellite = platform[:2]
        match satellite:
            case "S1":
                item = create_item_s1(path)
            case "S2":
                item = create_item_s2(path)

        json_file_path = str(Path(filename.parent, filename.name + ".STAC.json"))
        print(json_file_path)
        # Save the item as a JSON file
        item.save_object(dest_href=json_file_path)

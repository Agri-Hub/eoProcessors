"""Main Ingest module."""
from __future__ import annotations
from pathlib import Path

from stactools.sentinel1.grd.stac import create_item as create_item_s1_grd
from stactools.sentinel1.rtc.stac import create_item as create_item_s1_rtc
from stactools.sentinel1.slc.stac import create_item as create_item_s1_slc
from stactools.sentinel2.commands import create_item as create_item_s2
from stactools.sentinel3.commands import create_item as create_item_s3

FILETYPES = ("SAFE", "SEN3")


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

    def single_item(self, path: Path):
        """
        Just an item
        """
        if path.name.endswith(FILETYPES):
            platform = str(path.name).split("_")[0]
            satellite = platform[:2]
            item = {}
            match satellite:
                case "S1":
                    sensor = str(path.name).split("_")[:3]
                    match sensor:
                        case "GRD":
                            item = create_item_s1_grd(str(path))
                        case "RTC":
                            item = create_item_s1_rtc(str(path))
                        case "SLC":
                            item = create_item_s1_slc(str(path))
                case "S2":
                    item = create_item_s2(str(path))
                case "S3":
                    item = create_item_s3(str(path))
            json_file_path = str(Path(path.parent, str(path.name) + ".STAC.json"))
            print(json_file_path)
            # Save the item as a JSON file
            item.save_object(dest_href=json_file_path)

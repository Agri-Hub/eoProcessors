"""
Generic helper functions for creating Copernicus specific STAC items
"""
from pathlib import Path

from pystac import Provider

from stactools.sentinel1.grd.stac import create_item as create_item_s1_grd
from stactools.sentinel1.rtc.stac import create_item as create_item_s1_rtc
from stactools.sentinel1.slc.stac import create_item as create_item_s1_slc
from stactools.sentinel2.commands import create_item as create_item_s2
from stactools.sentinel3.commands import create_item as create_item_s3

FILETYPES = ("SAFE", "SEN3")


def create_copernicus_item(
        path: Path,
        collection: str | None,
        additional_providers: list[Provider]
):
    item = {}
    if path.name.endswith(FILETYPES):
        platform = str(path.name).split("_", maxsplit=1)[0]
        satellite = platform[:2]
        match satellite:
            case "S1":
                sensor = str(path.name).split("_")[2][:3]
                match sensor:
                    case "GRD":
                        item = create_item_s1_grd(str(path))
                        if not collection:
                            collection = "sentinel1-grd"
                    case "RTC":
                        item = create_item_s1_rtc(
                            granule_href=str(path),
                            additional_providers=additional_providers,
                        )
                        if not collection:
                            collection = "sentinel1-rtc"
                    case "SLC":
                        item = create_item_s1_slc(str(path))
                        if not collection:
                            collection = "sentinel1-slc"
            case "S2":
                item = create_item_s2(
                    granule_href=str(path),
                    additional_providers=additional_providers,
                )
                if not collection:
                    collection = "sentinel2-l2a"
            case "S3":
                item = create_item_s3(str(path))
                if not collection:
                    collection = "sentinel3"
    return item

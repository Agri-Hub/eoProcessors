"""
Generic helper functions for creating Beyond specific STAC items
"""
from typing import Final

from pathlib import Path
import antimeridian
from shapely import Geometry
from shapely.geometry import mapping as shapely_mapping
from shapely.geometry import shape as shapely_shape
from shapely.validation import make_valid

from pystac import Item, Provider
from pystac.utils import now_to_rfc3339_str

COORD_ROUNDING: Final[int] = 6

def create_wrf_item(
    path: Path,
    additional_providers: list[Provider]
):
    """
    Weather Research and Forecasting Beyond data.
    STAC Item creation based on Sentinel2 stactools item creation
    """

    # ensure that we have a valid geometry, fixing any antimeridian issues
    # get the Geometry and create a shapely Geometry
    geometry = Geometry()
    shapely_geometry = shapely_shape(antimeridian.fix_shape(geometry))
    geometry = make_valid(shapely_geometry)
    if (ga := geometry.area) > 100:
        raise Exception(f"Area of geometry is {ga}, which is too large to be correct.")
    bbox = [round(v, COORD_ROUNDING) for v in antimeridian.bbox(geometry)]

    # id: filename or something. Should first read the file
    # datetime whatever you want for that item
    item = Item(
        id=metadata.scene_id,
        geometry=shapely_mapping(geometry),
        bbox=bbox,
        datetime=metadata.datetime,
        properties={"created": now_to_rfc3339_str()},
    )
    item.common_metadata.providers = additional_providers

    return item

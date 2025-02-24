import logging
from pyproj import Transformer, CRS
import shapefile


logger = logging.getLogger(__name__)


def get_bbox_from_shp(shp_path: str, bbox_only: bool) -> list:
    """
    Get bbox from shape file path. The path should have two files: .shp and .prj.
    Function transforms from source CRS (through prj file) to default EPSG:4326
    projection, which is used by the providers.

    Parameters:
        shp_path (str): The shapefile path. It should contain .shp and .prj files.
        bbox_only (bool): Calculate the whole bbox instead of creating a bbox list.
    Returns:
        [west, south, east, north] (list(float)): Bounding box coordinates.
    """

    bboxes = []
    shp_path_shape = shp_path + ".shp"
    shp_path_projection = shp_path + ".prj"

    target_crs = "EPSG:4326"  # default CRS for majority of providers
    with open(shp_path_projection, "r", encoding="utf-8") as f:
        wkt = f.read()
        prj_crs = CRS.from_wkt(wkt)
    logger.debug("Source CRS: %s", prj_crs)
    transformer = Transformer.from_crs(prj_crs, target_crs)

    sf = shapefile.Reader(shp_path_shape)
    logger.debug("Transforming...")

    if bbox_only:
        minx, miny, maxx, maxy = sf.bbox
        south, west = transformer.transform(
            minx, miny
        )  # pylint:disable=unpacking-non-sequence
        north, east = transformer.transform(
            maxx, maxy
        )  # pylint:disable=unpacking-non-sequence
        bboxes.append([west, south, east, north])
    else:
        logger.debug("Total polygons: %s", len(sf.shapeRecords()))
        for single_shape in sf.shapeRecords():
            minx, miny, maxx, maxy = single_shape.shape.bbox
            south, west = transformer.transform(
                minx, miny
            )  # pylint:disable=unpacking-non-sequence
            north, east = transformer.transform(
                maxx, maxy
            )
            bboxes.append([west, south, east, north])

    return bboxes

"""
Aggregate
"""
import datetime
import os
from openeo import Connection

import logging

logger = logging.getLogger(__name__)


def month_median(connection: Connection, start_date, end_date, shape, max_cloud_cover):

    visual_bands = ["B02", "B03", "B04"]
    # Build the openEO process
    scl = connection.load_collection(
        collection_id="SENTINEL2_L2A",
        spatial_extent=shape,
        temporal_extent=[start_date, end_date],
        bands=["SCL"],
        properties={"eo:cloud_cover": lambda x: x.lte(max_cloud_cover)}
    )

    cloud_mask = scl.process(
        "to_scl_dilation_mask",
        data=scl,
        kernel1_size=17, kernel2_size=77,
        mask1_values=[2, 4, 5, 6, 7],
        mask2_values=[3, 8, 9, 10, 11],
        erosion_kernel_size=3)

    s2_cube = connection.load_collection(
            collection_id="SENTINEL2_L2A",
            spatial_extent=shape,
            temporal_extent=[start_date, end_date],
            bands=visual_bands,
            properties={"eo:cloud_cover": lambda x: x.lte(max_cloud_cover)}
        )
    s2_cube = s2_cube.mask(cloud_mask)

    for band in visual_bands:

        band_cube = s2_cube.band(band)
        band_cube_aggregate = band_cube.aggregate_temporal_period(
            period="month",
            reducer="mean"
        )

        # Fill gaps in the data using linear interpolation
        band_cube_interpolation = band_cube_aggregate.apply_dimension(
            dimension="t",
            process="array_interpolate_linear"
        )

        output_dir = "cloud_free_composites"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{band}_{start_date}_{end_date}.tif")
        # s2_cube.save_result(format="GTiff")
        # Execute
        band_cube_interpolation.execute_batch(output_file, out_format="GTiff")

        logger.info("Saved: %s ", output_file)


def aggregate_per_month(connection: Connection, start_date, end_date, shape, max_cloud_cover):

    # BANDS. Please include SCL for Sentinel 2 to mask clouds
    bands = ["B02", "B03", "B04", "B08", "SCL"]
    visual_bands = ["B02", "B03", "B04", "B08"]
    output_dir = "cloud_free_composites"
    os.makedirs(output_dir, exist_ok=True)

    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    current_dt = start_dt

    while current_dt <= end_dt:
        year = current_dt.year
        month = current_dt.month

        month_start = f"{year}-{month:02d}-01"
        last_day = (
            datetime.date(year, month, 1).replace(day=28) +
            datetime.timedelta(days=4)
        ).replace(day=1) - datetime.timedelta(days=1)
        month_end = last_day.strftime("%Y-%m-%d")

        print(f"Processing: {year}-{month:02d} for shape file")

        # target_crs = "EPSG:4326"
        datacube = connection.load_collection(
            "SENTINEL2_L2A",
            spatial_extent=shape,
            temporal_extent=[month_start, month_end],
            bands=bands,
            max_cloud_cover=max_cloud_cover
        )  # .resample_spatial(projection=target_crs, resolution=10.0)

        scl_mask = datacube.process(
            "to_scl_dilation_mask",
            data=datacube.filter_bands(["SCL"]),
            scl_band_name="SCL",
            kernel1_size=17,  # 17px dilation on a 20m layer
            kernel2_size=77,   # 77px dilation on a 20m layer
            mask1_values=[2, 4, 5, 6, 7],
            mask2_values=[3, 8, 9, 10, 11],
            erosion_kernel_size=3
        ).rename_labels("bands", ["SCL_DILATED_MASK"])

        datacube = datacube.merge_cubes(scl_mask)

        # Apply cloud masking using the Scene Classification Layer (SCL)
        # cloud_free = datacube.process(
        #     "mask_scl_dilation",
        #     data=datacube,
        #     scl_band_name="SCL",
        #     # You can experiment with the following
        #     valid_scl_values=[3, 4, 5, 6, 7, 11]
        # )

        for band in visual_bands:
            band_cube = datacube.band(band)
            composite = band_cube.reduce_dimension(dimension="t", reducer="median")
            output_file = os.path.join(output_dir, f"{band}_{year}_{month:02d}.tif")

            # Execute
            composite.execute_batch(output_file, out_format="GTiff")

            logger.info("Saved: %s ", output_file)

        # Move to next month
        current_dt = (current_dt.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

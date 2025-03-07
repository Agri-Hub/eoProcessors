"""
Aggregate
"""

import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pathlib import Path
from openeo import Connection

import logging

log_filename = f"openeo_log_{datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(message)s')


def monthly_median_daydelta(
    connection, start_date, end_date, shape, max_cloud_cover, day_delta, output_path
):
    """Iterates over each month in the range and calls process_dates with expanded range."""
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    print(f"====== Cloud free composites from {start_date} to {end_date} ======")

    current_date = start_date.replace(day=1)  # Move to the first day of the start month
    while current_date <= end_date:
        month_start = current_date
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

        # Expand range by 10 days before and after
        start_range = month_start - timedelta(days=day_delta)
        end_range = month_end + timedelta(days=day_delta)

        print(
            f"Cloud free composites from {start_range.strftime("%Y-%m-%d")} to {end_range.strftime("%Y-%m-%d")}"
        )
        mask_and_complete(
            connection,
            start_range.strftime("%Y-%m-%d"),
            end_range.strftime("%Y-%m-%d"),
            shape,
            max_cloud_cover,
            output_path
        )

        # Move to the next month
        current_date += relativedelta(months=1)


def mask_and_complete(
    connection: Connection, start_date, end_date, shape, max_cloud_cover, output_path
):

    bands = [
        "B01",
        "B02",
        "B03",
        "B04",
        "B05",
        "B06",
        "B07",
        "B08",
        "B8A",
        "B09",
        "B11",
        "B12",
    ]

    s2_cube = connection.load_collection(
        collection_id="SENTINEL2_L2A",
        spatial_extent=shape,
        temporal_extent=[start_date, end_date],
        bands=bands,
        properties={"eo:cloud_cover": lambda x: x.lte(max_cloud_cover)},
    )

    scl_cube = connection.load_collection(
        collection_id="SENTINEL2_L2A",
        spatial_extent=shape,
        temporal_extent=[start_date, end_date],
        bands=["SCL"],
        properties={"eo:cloud_cover": lambda x: x.lte(max_cloud_cover)},
    )

    # Cloudy pixels are identified as where SCL is 3, 8, 9, or 10.
    # Here we assume that the client overloads comparison operators and bitwise OR (|) for boolean operations.
    # [0, 1, 2, 3, 7, 8, 9, 10]
    # Clouds only [0, 3, 8, 9, 10]
    cloud_mask = (
        (scl_cube == 0)
        | (scl_cube == 1)
        | (scl_cube == 2)
        | (scl_cube == 3)
        | (scl_cube == 7)
        | (scl_cube == 8)
        | (scl_cube == 9)
        | (scl_cube == 10)
    )
    # water_mask = (scl_cube == 6)
    # snow_mask = (scl_cube == 11)

    masked_cube = s2_cube.mask(cloud_mask, replacement=None)

    for band in bands:
        logging.info("%s %s %s - START", band, start_date, end_date)
        print(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Trying band {band} from {start_date} to {end_date}")
        masked_band = masked_cube.band(band)
        # not_masked_band = masked_cube.band(band)

        # 6. Reduce the time dimension to create a composite.
        # For example, use a median reducer over time.
        composite = masked_band.reduce_dimension(
            dimension="t", reducer="median"  # or use a custom reducer if needed
        )
        #  not_masked_composite = not_masked_band.reduce_dimension(
        #     dimension="t",
        #     reducer="median"  # or use a custom reducer if needed
        # )

        output_dir = str(Path(output_path, "cloud_free_composites"))
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(
            output_dir, f"{Path(shape).stem}_{start_date}_{end_date}_{band}.tif"
        )
        # output_file_not_masked = os.path.join(output_dir, f"{Path(shape).stem}_{start_date}_{end_date}_{band}_not_masked.tif")
        try:
            composite.execute_batch(output_file, out_format="GTiff")
        except RuntimeError as e:
            print("something went wrong: %e", e)
            logging.error("something went wrong: %s ", e)
            continue
        # not_masked_composite.execute_batch(output_file_not_masked, out_format="GTiff")
        logging.info(
            band,
            start_date,
            end_date,
            output_file
        )

    # Compute probability composites (mean occurrence over time)
    # cloud_probability = cloud_mask.reduce_dimension(dimension="t", reducer="mean")
    # water_probability = water_mask.reduce_dimension(dimension="t", reducer="mean")
    # snow_probability = snow_mask.reduce_dimension(dimension="t", reducer="mean")

    # cloud_output_file = os.path.join(output_dir, f"{Path(shape).stem}_{start_date}_{end_date}_{band}_cloud.tif")
    # water_output_file = os.path.join(output_dir, f"{Path(shape).stem}_{start_date}_{end_date}_{band}_water.tif")
    # snow_output_file = os.path.join(output_dir, f"{Path(shape).stem}_{start_date}_{end_date}_{band}_snow.tif")

    # cloud_probability.execute_batch(cloud_output_file, out_format="GTiff")
    # water_probability.execute_batch(water_output_file, out_format="GTiff")
    # snow_probability.execute_batch(snow_output_file, out_format="GTiff")

"""
Aggregate
"""

import os
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pathlib import Path
from openeo import Connection
from openeo import collection_property

import logging

log_filename = f"openeo_log_{datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}.log"
logging.basicConfig(
    filename=log_filename, level=logging.INFO, format="%(asctime)s - %(message)s"
)


MAX_RETRIES = 5
SLEEPING_TIME_SEC = 30


def monthly_median_daydelta(
    connection,
    bands,
    start_date,
    end_date,
    shape,
    max_cloud_cover,
    day_delta,
    output_path,
):
    """Iterates over each month in the range and calls process_dates with expanded range."""
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    print(f"====== Cloud free composites from {start_date} to {end_date} ======")

    current_date = start_date.replace(day=1)  # Move to the first day of the start month
    while current_date <= end_date:
        month_start = current_date
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

        # Expand range by "day_delta" days before and after
        start_range = month_start - timedelta(days=day_delta)
        end_range = month_end + timedelta(days=day_delta)

        print(
            f"Cloud free composites from {start_range.strftime("%Y-%m-%d")} to {end_range.strftime("%Y-%m-%d")}"
        )
        mask_and_complete(
            connection=connection,
            bands=bands,
            start_date=start_range.strftime("%Y-%m-%d"),
            end_date=end_range.strftime("%Y-%m-%d"),
            shape=shape,
            max_cloud_cover=max_cloud_cover,
            output_path=output_path,
        )

        # Move to the next month
        current_date += relativedelta(months=1)


def mask_and_complete(
    connection: Connection,
    bands,
    start_date,
    end_date,
    shape,
    max_cloud_cover,
    output_path,
):

    s2_cube = connection.load_collection(
        collection_id="SENTINEL2_L2A",
        spatial_extent=shape,
        temporal_extent=[start_date, end_date],
        bands=bands,
        properties=[
            collection_property("processingBaseline")  == "05.10", # or "05.00"
        ],
        max_cloud_cover=max_cloud_cover
    )

    scl_cube = connection.load_collection(
        collection_id="SENTINEL2_L2A",
        spatial_extent=shape,
        temporal_extent=[start_date, end_date],
        bands=["SCL"],
        properties=[
            collection_property("processingBaseline")  == "05.10", # or "05.00"
        ],
        max_cloud_cover=max_cloud_cover
    )

    # Cloudy pixels are identified as where SCL is 3, 8, 9, or 10.
    # Clouds and 0 as noted from SCL [0, 3, 8, 9, 10]
    cloud_mask = (
        (scl_cube == 0)
        | (scl_cube == 3)
        | (scl_cube == 8)
        | (scl_cube == 9)
        | (scl_cube == 10)  # remove thin cirrus
    )
    # water_mask = (scl_cube == 6)
    # snow_mask = (scl_cube == 11)

    # Mask clouds
    masked_cube_full = s2_cube.mask(cloud_mask, replacement=None)
    # Keep only AOI
    masked_cube = masked_cube_full.filter_spatial(shape)
    # TODO print count of images after filtering for QA metrics
    for band in bands:
        for retry in range(MAX_RETRIES):
            try:
                logging.info("%s %s %s - START", band, start_date, end_date)
                print(
                    f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]"
                    f"Trying band {band} from {start_date} to {end_date}"
                )
                masked_band = masked_cube.band(band)
                # not_masked_band = masked_cube.band(band)

                composite = masked_band.reduce_dimension(
                    dimension="t", reducer="median"
                )
                #  not_masked_composite = not_masked_band.reduce_dimension(
                #     dimension="t",
                #     reducer="median"
                # )

                output_dir = str(Path(output_path, "cloud_free_composites"))
                os.makedirs(output_dir, exist_ok=True)
                title = f"{Path(shape).stem} {start_date} {end_date} {band}"
                output_file = os.path.join(
                    output_dir, f"{Path(shape).stem}_{start_date}_{end_date}_{band}.tif"
                )
                # output_file_not_masked = os.path.join(
                #     output_dir,
                #     f"{Path(shape).stem}_{start_date}_{end_date}_{band}_not_masked.tif"
                # )

                # TODO job options: tweak CPU/mem etc to check credit usage
                composite.execute_batch(output_file, out_format="GTiff", title=title)
            except Exception as e:
                print(
                    f"Something went wrong: {e}.\n"
                    f"RETRYING({retry} attempt out of {MAX_RETRIES})"
                )
                logging.warning(
                    "Something went wrong: %s. RETRYING(%s attempt out of %s)",
                    e,
                    retry,
                    MAX_RETRIES,
                )
                time.sleep(SLEEPING_TIME_SEC + (retry * SLEEPING_TIME_SEC * 2))
                continue
            else:
                print(f"DONE: {band} {start_date} {end_date} {output_file}")
                logging.info(
                    "DONE: %s %s %s %s", band, start_date, end_date, output_file
                )
                break
        else:
            print(
                f"Something went wrong after {MAX_RETRIES} attempts. Aborting jobs of {title}"
            )
            logging.error(
                "Something went wrong after %s attempts. Aborting jobs of %s",
                MAX_RETRIES,
                title,
            )
            # Some months (especially early 2017) do not have data. Continue to next month.
            return
            # raise RuntimeError("Something is terribly wrong. Aborting")

            # not_masked_composite.execute_batch(output_file_not_masked, out_format="GTiff")

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

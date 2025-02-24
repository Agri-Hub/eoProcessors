"""
Aggregate
"""
import datetime
import os
from openeo import Connection

import logging

logger = logging.getLogger(__name__)


def aggregate():
    pass

def aggegate_per_tile(connection: Connection, start_date, end_date, tile):
    # Define the area of interest (tile T34SEJ) in MGRS
    tile_id = tile
    # tile_id = "T34SEJ"
    # Sentinel-2 bands of interest
    bands = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12"]

    # Output directory
    output_dir = "cloud_free_composites"
    os.makedirs(output_dir, exist_ok=True)

    # Convert input string dates to datetime objects
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    # Loop through each month in the given date range
    current_dt = start_dt
    while current_dt <= end_dt:
        year = current_dt.year
        month = current_dt.month

        # Generate start and end date for the month as strings
        month_start = f"{year}-{month:02d}-01"
        last_day = (datetime.date(year, month, 1).replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        month_end = last_day.strftime("%Y-%m-%d")

        print(f"Processing: {year}-{month:02d} for tile {tile_id}")

        # Load Sentinel-2 collection for the specified month
        datacube = connection.load_collection(
            "SENTINEL2_L2A",
            spatial_extent={"tile": tile_id},
            temporal_extent=[month_start, month_end],  # Passed as string
            bands=bands
        )

        # Apply cloud masking using the Scene Classification Layer (SCL)
        cloud_free = datacube.process(
            "mask_scl_dilation",
            data=datacube,
            scl_band_name="SCL",
            valid_scl_values=[3, 4, 5, 6, 7, 11]
        )

        # Process each band separately
        for band in bands:
            band_cube = cloud_free.band(band)

            # Compute median composite per month
            composite = band_cube.reduce_dimension(dimension="t", reducer="median")

            # Define the output file name
            output_file = os.path.join(output_dir, f"{tile_id}_{band}_{year}_{month:02d}.tif")

            # Execute and save the result
            composite.execute_batch(output_file, out_format="GTiff")

            print(f"Saved: {output_file}")

        # Move to the next month
        current_dt = (current_dt.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

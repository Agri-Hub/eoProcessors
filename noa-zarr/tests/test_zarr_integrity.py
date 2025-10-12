# tests/test_zarr_integrity.py
import logging
import xarray as xr
import numpy as np
import os
import pytest

logger = logging.getLogger("test_zarr_integrity")


@pytest.mark.parametrize(
    "zarr_path",
    [
        r"C:/Users/thana/Desktop/noa/DataRelayHubs/cogs/T34SEJ.zarr",
    ],
)
def test_zarr_structure(zarr_path):
    logger.info(f"Checking Zarr structure at: {zarr_path}")
    assert os.path.exists(zarr_path), f"Zarr not found: {zarr_path}"

    ds = xr.open_zarr(zarr_path, consolidated=True)
    logger.info(
        f"Opened dataset with dims: {dict(ds.dims)} and coords: {list(ds.coords)}"
    )

    assert "reflectance" in ds.data_vars, "Missing 'reflectance' variable"
    assert all(
        k in ds.coords for k in ["time", "band", "x", "y"]
    ), "Missing coordinates"

    arr = ds["reflectance"]
    logger.info(f"Reflectance dtype: {arr.dtype}, shape: {arr.shape}")

    assert arr.ndim == 4
    assert arr.dtype in (np.float32, np.float64)
    assert arr.shape[0] > 0
    assert arr.shape[1] >= 2

    finite_pixels = np.isfinite(arr.isel(time=0, band=0).values).sum()
    logger.info(f"Finite pixel count in first band: {finite_pixels}")
    assert finite_pixels > 0, "All pixels are NaN!"


def test_time_monotonic(
    zarr_path=r"C:/Users/thana/Desktop/noa/DataRelayHubs/cogs/T34SEJ.zarr",
):
    ds = xr.open_zarr(zarr_path, consolidated=True)
    logger.info(f"Checking monotonic time order for {len(ds.time)} timestamps.")
    times = ds.time.values
    diffs = np.diff(times).astype("timedelta64[D]")
    logger.info(f"Time deltas (days): {diffs}")
    assert np.all(diffs >= np.timedelta64(0, "D")), "Non-monotonic time order"

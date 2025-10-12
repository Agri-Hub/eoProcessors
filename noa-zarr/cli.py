#!/usr/bin/env python3
"""
Generic Sentinel-2 bands → Zarr processor driven by config.yaml
"""

from __future__ import annotations
import argparse, dataclasses, logging, re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import numpy as np, xarray as xr, rioxarray
from rasterio.enums import Resampling
from numcodecs import Blosc
import zarr
import yaml

# --------------------------- Logging ---------------------------


def setup_logging(verbosity: int):
    """
    Configure and initialize application-wide logging.

    Parameters
    ----------
    verbosity : int
        CLI verbosity flag (-v, -vv) controlling log detail:
        0 → WARNING, 1 → INFO, 2+ → DEBUG

    Notes
    -----
    Removes any existing handlers to avoid duplicate logs (useful for
    pytest and Jupyter reruns). All output is printed to stdout using
    a unified timestamped format.
    """
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler()],
    )

    logging.getLogger().setLevel(level)
    logging.info(f"Logging initialized at level: {logging.getLevelName(level)}")


# ---------------------------------------------------------------------
# Configuration models
# ---------------------------------------------------------------------


@dataclass
class InputCfg:
    """Configuration for input data discovery."""

    root: str
    recursive: bool = True
    globs: List[str] = dataclasses.field(default_factory=lambda: ["*.tif", "*.tiff"])


@dataclass
class FilenameCfg:
    """Configuration for filename parsing using regex."""

    mode: str
    pattern: str
    date_format: str = "%Y%m"
    date_normalization: str = "mid_month"


@dataclass
class ReflectanceCfg:
    """Configuration for reflectance scaling and missing band handling."""

    scale: float = 1.0
    dtype: str = "float32"
    fill_missing_bands: bool = True
    fill_value: float = 0.0


@dataclass
class BandsCfg:
    """Configuration for band order (auto or user-defined)."""

    order: Iterable[str] | str = "auto"


@dataclass
class GroupingCfg:
    """Configuration for how files are grouped into Zarr stores."""

    by: str = "none"  # none|tile|tile_year|tile_month
    store_pattern: str = "{tile}.zarr"


@dataclass
class ZarrCfg:
    """Configuration for Zarr output (compression, chunking, consolidation)."""

    out: str
    chunks: Dict[str, int] = dataclasses.field(
        default_factory=lambda: {"time": 1, "band": -1, "y": 2048, "x": 2048}
    )
    compressor: str = "zstd:6"
    consolidate: bool = True


@dataclass
class SafetyCfg:
    """Configuration for safety and reprojection checks."""

    reproject_to_ref: bool = True
    strict_same_grid: bool = False
    dry_run: bool = False


@dataclass
class ProcessorCfg:
    """Root configuration combining all sections."""

    input: InputCfg
    filename: FilenameCfg
    reflectance: ReflectanceCfg
    bands: BandsCfg
    grouping: GroupingCfg
    zarr: ZarrCfg
    safety: SafetyCfg


# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------


def make_compressor(spec: str) -> Blosc:
    """
    Create a Blosc compressor from a string specification.

    Examples
    --------
    "zstd:6" → zstd compressor with level 6
    "lz4:5"  → lz4 compressor with level 5
    """
    cname, clevel = "zstd", 6

    if spec:
        parts = spec.split(":")

        if parts[0]:
            cname = parts[0].lower()

        if len(parts) > 1 and parts[1].isdigit():
            clevel = int(parts[1])

    return Blosc(cname=cname, clevel=clevel, shuffle=Blosc.BITSHUFFLE)


def normalize_date(s: str, fmt: str, norm: str) -> datetime:
    """
    Normalize a captured date string into a full datetime.

    Parameters
    ----------
    s : str
        Date string from filename (e.g. "202406").
    fmt : str
        Format to parse (e.g. "%Y%m" or "%Y%m%d").
    norm : str
        Normalization rule ("first", "mid_month", "last", "keep").
    """
    dt = datetime.strptime(s, fmt)

    if fmt == "%Y%m" and norm != "keep":

        if norm == "first":
            day = 1
        elif norm == "mid_month":
            day = 15
        elif norm == "last":
            next_month = datetime(dt.year + (dt.month // 12), ((dt.month % 12) + 1), 1)
            dt = next_month - timedelta(days=1)

            return dt

        dt = datetime(dt.year, dt.month, day)

    return dt


# ---------------------------------------------------------------------
# Filename parser
# ---------------------------------------------------------------------


class FilenameParser:
    """Extract date, band, and tile information from filenames."""

    def __init__(self, cfg: FilenameCfg):
        self.cfg = cfg
        self.log = logging.getLogger("FilenameParser")

        if cfg.mode != "regex":
            raise ValueError("Only 'regex' filename mode is supported.")

        self.pat = re.compile(cfg.pattern)
        self.log.debug(f"Compiled regex pattern: {cfg.pattern}")

    def parse(self, p: Path) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Return (date, band, tile) from a given filename."""
        m = self.pat.search(p.name)

        if not m:
            self.log.debug(f"No match for: {p.name}")

            return None, None, None

        date = m.groupdict().get("date")
        band = m.groupdict().get("band")
        tile = m.groupdict().get("tile")

        self.log.debug(f"Parsed {p.name} → date={date}, band={band}, tile={tile}")

        return date, (band.upper() if band else None), (tile.upper() if tile else None)


# ---------------------------------------------------------------------
# Main processor
# ---------------------------------------------------------------------


class S2BandsToZarr:
    """Main processor that converts Sentinel-2 bands to Zarr format."""

    def __init__(self, cfg: ProcessorCfg):
        self.cfg = cfg
        self.parser = FilenameParser(cfg.filename)
        self.compressor = make_compressor(cfg.zarr.compressor)
        self.dtype = (
            np.float32 if cfg.reflectance.dtype.lower() == "float32" else np.float64
        )
        self.log = logging.getLogger("S2BandsToZarr")

    def discover(self) -> List[Tuple[str, str, Optional[str], Path]]:
        """
        Discover all input raster files matching config patterns and extract metadata.
        """
        self.log.info("Scanning for input files...")
        root = Path(self.cfg.input.root)
        files = []

        for g in self.cfg.input.globs:
            found = list(root.rglob(g) if self.cfg.input.recursive else root.glob(g))
            self.log.debug(f"Pattern {g}: found {len(found)} files")
            files.extend(found)

        if not files:
            raise SystemExit("No files found matching input patterns.")

        records = []

        for p in sorted(files):
            date, band, tile = self.parser.parse(p)

            if date and band:
                records.append((date, band, tile, p))

        self.log.info(f"Valid input files: {len(records)}")

        return records

    def resolve_bands(self, records) -> List[str]:
        """Resolve band ordering."""
        if self.cfg.bands.order == "auto":
            order = sorted({b for _, b, _, _ in records})
        else:
            order = list(self.cfg.bands.order)

        self.log.info(f"Resolved bands: {order}")

        return order

    def group_records(self, records):
        """Group input files according to config (by tile/year/month)."""
        groups = defaultdict(list)
        by = self.cfg.grouping.by
        self.log.info(f"Grouping by: {by}")

        for date, band, tile, p in records:

            if by == "none":
                key = (None, None)
            elif by == "tile":
                key = (tile or "NO_TILE", None)
            elif by == "tile_year":
                key = (tile or "NO_TILE", date[:4])
            elif by == "tile_month":
                key = (tile or "NO_TILE", f"{date[:4]}-{date[4:6]}")
            else:
                raise ValueError(f"Unknown grouping mode: {by}")

            groups[key].append((date, band, tile, p))

        self.log.info(f"Formed {len(groups)} groups for Zarr writing.")

        return groups

    def target_store_path(self, group_key) -> Path:
        """Return the output path for a given group."""
        out = Path(self.cfg.zarr.out)
        root = out if out.suffix != ".zarr" else out.parent
        tile, suffix = group_key
        year, month = None, None

        if isinstance(suffix, str):

            if len(suffix) == 4:
                year = suffix
            else:
                year, month = suffix.split("-")

        sp = self.cfg.grouping.store_pattern.format(
            tile=tile, year=year or "", month=month or ""
        )
        path = root / sp

        self.log.debug(f"Target store for {group_key}: {path}")

        return path

    def run(self):
        """Main orchestration: discover → group → write."""
        self.log.info("Starting processor run...")
        recs = self.discover()
        bands = self.resolve_bands(recs)
        groups = self.group_records(recs)

        for gkey, items in sorted(groups.items(), key=lambda kv: str(kv[0])):
            store_path = self.target_store_path(gkey)
            self._write_group(store_path, items, bands)

        self.log.info("Processing completed successfully.")

    def _write_group(self, store_path: Path, items, bands: List[str]):
        """Write one Zarr group (tile/year)."""
        self.log.info(f"Writing group → {store_path}")
        by_date = defaultdict(dict)

        for date, band, tile, p in items:
            by_date[date][band] = p

        all_dates = sorted(by_date.keys())
        ref_path = next(iter(items))[3]

        ref2d = rioxarray.open_rasterio(ref_path, masked=True).squeeze(
            "band", drop=True
        )

        time_slices = []

        for date in all_dates:
            self.log.debug(f"Processing date {date}")
            band_arrays = []

            for b in bands:
                path = by_date[date].get(b)

                if not path:
                    self.log.warning(f"Missing band {b} at {date}, filling.")
                    missing = xr.full_like(
                        ref2d, self.cfg.reflectance.fill_value, dtype=self.dtype
                    )
                    band_arrays.append(missing)
                    continue

                da = rioxarray.open_rasterio(path, masked=True).squeeze(
                    "band", drop=True
                )

                if self.cfg.safety.reproject_to_ref and (
                    tuple(da.shape) != tuple(ref2d.shape)
                    or str(da.rio.crs) != str(ref2d.rio.crs)
                ):
                    self.log.debug(f"Reprojecting {path.name} to match reference grid.")
                    da = da.rio.reproject_match(ref2d, resampling=Resampling.nearest)

                da = da.astype(self.dtype) * float(self.cfg.reflectance.scale)

                band_arrays.append(da)

            stacked = xr.concat(band_arrays, dim="band").assign_coords(band=bands)

            tval = normalize_date(
                date,
                self.cfg.filename.date_format,
                self.cfg.filename.date_normalization,
            )

            stacked = stacked.expand_dims(time=[tval])

            time_slices.append(stacked)

        data = xr.concat(time_slices, dim="time").rio.write_crs(ref2d.rio.crs)
        ds = xr.Dataset({"reflectance": data})
        ds.attrs.update(
            {
                "source": "S2 composites",
                "scale_factor": float(self.cfg.reflectance.scale),
            }
        )

        enc = {
            "compressor": self.compressor,
            "chunks": (
                self.cfg.zarr.chunks.get("time", 1),
                self.cfg.zarr.chunks.get("band", -1),
                self.cfg.zarr.chunks.get("y", 2048),
                self.cfg.zarr.chunks.get("x", 2048),
            ),
        }

        ds["reflectance"].encoding = enc

        if self.cfg.safety.dry_run:
            self.log.info(
                f"[Dry run] Would write {store_path} (time={len(data.time)}, bands={len(bands)})"
            )
            return

        store_path.parent.mkdir(parents=True, exist_ok=True)
        ds.to_zarr(str(store_path), mode="w")

        if self.cfg.zarr.consolidate:
            zarr.convenience.consolidate_metadata(str(store_path))

        self.log.info(f"Written {store_path} successfully.")


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------


def load_config(path: Path) -> ProcessorCfg:
    """Load configuration YAML file."""
    log = logging.getLogger("load_config")
    log.info(f"Loading configuration from {path}")

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    p = raw.get("processor", {})

    cfg = ProcessorCfg(
        input=InputCfg(**p.get("input", {})),
        filename=FilenameCfg(**p.get("filename", {})),
        reflectance=ReflectanceCfg(**p.get("reflectance", {})),
        bands=BandsCfg(**p.get("bands", {})),
        grouping=GroupingCfg(**p.get("grouping", {})),
        zarr=ZarrCfg(**p.get("zarr", {})),
        safety=SafetyCfg(**p.get("safety", {})),
    )
    return cfg


def main(argv=None):
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="Sentinel-2 bands → Zarr (config-driven)")
    ap.add_argument("--config", required=True, help="Path to config.yaml")
    ap.add_argument("-v", "--verbose", action="count", default=0)
    args = ap.parse_args(argv)

    setup_logging(1)
    log = logging.getLogger("main")

    log.info("Initializing processor...")
    cfg = load_config(Path(args.config))
    proc = S2BandsToZarr(cfg)
    proc.run()
    log.info("Done.")


if __name__ == "__main__":
    main()

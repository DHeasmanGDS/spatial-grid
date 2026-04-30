"""Shapefile exporter (lines + stations)."""
from __future__ import annotations

from pathlib import Path

from ..core import Grid

# Shapefile DBF field names are limited to 10 characters.
_STATION_RENAME = {
    "station_id": "stn_id",
    "station_name": "stn_name",
    "line_offset_m": "line_off_m",
    "station_offset_m": "stn_off_m",
}
_LINE_RENAME = {
    "line_offset_m": "line_off_m",
    "azimuth_deg": "azimuth",
}


def write_shapefile(grid: Grid, output_dir: str | Path, basename: str) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stations_path = output_dir / f"{basename}_stations.shp"
    lines_path = output_dir / f"{basename}_lines.shp"

    grid.stations.rename(columns=_STATION_RENAME).to_file(
        stations_path, driver="ESRI Shapefile"
    )
    grid.lines.rename(columns=_LINE_RENAME).to_file(
        lines_path, driver="ESRI Shapefile"
    )
    return stations_path, lines_path

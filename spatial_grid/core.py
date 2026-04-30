"""Core grid generation."""
from __future__ import annotations

import math
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
from pyproj import CRS
from shapely.geometry import LineString, Point

from .naming import line_label, station_label


VALID_ANCHORS = ("center", "sw", "se", "nw", "ne")


@dataclass
class GridSpec:
    centre_easting: float
    centre_northing: float
    azimuth_deg: float
    line_spacing: float
    station_spacing: float
    num_lines: int
    num_stations: int
    crs: str
    grid_name: str = "GRID"
    line_naming: str = "chainage"
    station_naming: str = "chainage"
    anchor: str = "center"
    """Where (centre_easting, centre_northing) sits relative to the grid.

    'center'  - midpoint of the grid (default)
    'sw','se','nw','ne' - the named corner of the grid in the *unrotated* frame
                          (lines run N-S, line spacing runs E-W). Survey extends
                          NE / NW / SE / SW from the anchor accordingly.
    """

    def __post_init__(self):
        if self.num_lines < 1:
            raise ValueError("num_lines must be >= 1")
        if self.num_stations < 2:
            raise ValueError("num_stations must be >= 2")
        if self.line_spacing <= 0 or self.station_spacing <= 0:
            raise ValueError("spacings must be positive")
        if self.anchor not in VALID_ANCHORS:
            raise ValueError(f"anchor must be one of {VALID_ANCHORS}; got {self.anchor!r}")
        CRS.from_user_input(self.crs)


@dataclass
class Grid:
    spec: GridSpec
    stations: gpd.GeoDataFrame
    lines: gpd.GeoDataFrame

    @property
    def total_line_km(self) -> float:
        return float(self.lines.geometry.length.sum() / 1000.0)

    @property
    def total_stations(self) -> int:
        return len(self.stations)


def generate_grid(spec: GridSpec) -> Grid:
    """Generate a rectangular grid anchored at (centre_easting, centre_northing).

    The anchor point is the grid centre when spec.anchor == 'center', or the
    named corner (in the unrotated frame) for sw/se/nw/ne. Azimuth is measured
    clockwise from north and gives the direction lines run; line spacing is
    perpendicular to that.
    """
    az_rad = math.radians(spec.azimuth_deg)
    along = np.array([math.sin(az_rad), math.cos(az_rad)])
    perp = np.array([math.cos(az_rad), -math.sin(az_rad)])

    anchor_pt = np.array([spec.centre_easting, spec.centre_northing])

    n_l, n_s = spec.num_lines, spec.num_stations
    if spec.anchor == "center":
        line_indices = np.arange(n_l) - (n_l - 1) / 2
        station_indices = np.arange(n_s) - (n_s - 1) / 2
    else:
        # Anchor at a corner: one or both index ranges are non-negative.
        # 'sw' / 'nw' anchors are on the WEST side -> grid extends east  (line idx >= 0)
        # 'sw' / 'se' anchors are on the SOUTH side -> grid extends north (station idx >= 0)
        cross_sign = 1 if spec.anchor in ("sw", "nw") else -1
        along_sign = 1 if spec.anchor in ("sw", "se") else -1
        line_indices = cross_sign * np.arange(n_l)
        station_indices = along_sign * np.arange(n_s)

    is_centre = spec.anchor == "center"

    station_records = []
    line_records = []

    for li, l_idx in enumerate(line_indices):
        l_offset = float(l_idx * spec.line_spacing)
        line_origin = anchor_pt + perp * l_offset
        line_id = line_label(l_offset, spec.line_naming, li, signed=is_centre)

        line_pts = []
        for si, s_idx in enumerate(station_indices):
            s_offset = float(s_idx * spec.station_spacing)
            pos = line_origin + along * s_offset
            station_name = station_label(s_offset, spec.station_naming, si, signed=is_centre)
            station_id = f"{line_id}_{station_name}"

            station_records.append({
                "station_id": station_id,
                "line_id": line_id,
                "station_name": station_name,
                "line_offset_m": l_offset,
                "station_offset_m": s_offset,
                "easting": float(pos[0]),
                "northing": float(pos[1]),
                "geometry": Point(float(pos[0]), float(pos[1])),
            })
            line_pts.append((float(pos[0]), float(pos[1])))

        line_records.append({
            "line_id": line_id,
            "line_offset_m": l_offset,
            "length_m": float((spec.num_stations - 1) * spec.station_spacing),
            "azimuth_deg": float(spec.azimuth_deg),
            "geometry": LineString(line_pts),
        })

    stations_gdf = gpd.GeoDataFrame(station_records, crs=spec.crs)
    lines_gdf = gpd.GeoDataFrame(line_records, crs=spec.crs)

    return Grid(spec=spec, stations=stations_gdf, lines=lines_gdf)

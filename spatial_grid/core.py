"""Core grid generation."""
from __future__ import annotations

import math
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
from pyproj import CRS
from shapely.geometry import LineString, Point

from .naming import line_label, station_label


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

    def __post_init__(self):
        if self.num_lines < 1:
            raise ValueError("num_lines must be >= 1")
        if self.num_stations < 2:
            raise ValueError("num_stations must be >= 2")
        if self.line_spacing <= 0 or self.station_spacing <= 0:
            raise ValueError("spacings must be positive")
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
    """Generate a rectangular grid centred on (centre_easting, centre_northing).

    Azimuth is measured clockwise from north and gives the direction lines run.
    Line spacing is perpendicular to that direction.
    """
    az_rad = math.radians(spec.azimuth_deg)
    along = np.array([math.sin(az_rad), math.cos(az_rad)])
    perp = np.array([math.cos(az_rad), -math.sin(az_rad)])

    centre = np.array([spec.centre_easting, spec.centre_northing])

    line_indices = np.arange(spec.num_lines) - (spec.num_lines - 1) / 2
    station_indices = np.arange(spec.num_stations) - (spec.num_stations - 1) / 2

    station_records = []
    line_records = []

    for li, l_idx in enumerate(line_indices):
        l_offset = float(l_idx * spec.line_spacing)
        line_origin = centre + perp * l_offset
        line_id = line_label(l_offset, spec.line_naming, li)

        line_pts = []
        for si, s_idx in enumerate(station_indices):
            s_offset = float(s_idx * spec.station_spacing)
            pos = line_origin + along * s_offset
            station_name = station_label(s_offset, spec.station_naming, si)
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

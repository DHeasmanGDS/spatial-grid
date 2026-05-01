"""Drill-hole planning math.

Convention:
    azimuth_deg : degrees from north, clockwise (the direction the hole points)
    dip_deg     : downward angle from horizontal (0 = horizontal, 90 = vertical down)
    length_m    : total planned hole length, measured along the hole

Positions along a hole at depth d (measured along the hole, not vertical):
    horizontal_dist  = d * cos(dip)
    delta_easting    = horizontal_dist * sin(azimuth)
    delta_northing   = horizontal_dist * cos(azimuth)
    delta_rl         = -d * sin(dip)        # negative because going down
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import geopandas as gpd
import numpy as np
from pyproj import CRS
from shapely.geometry import LineString, Point


@dataclass
class DrillHoleSpec:
    name: str
    collar_easting: float
    collar_northing: float
    collar_rl: float = 0.0
    azimuth_deg: float = 0.0
    dip_deg: float = 90.0
    length_m: float = 100.0

    def __post_init__(self):
        if self.length_m <= 0:
            raise ValueError(f"{self.name}: length_m must be > 0 (got {self.length_m})")
        if not 0 <= self.dip_deg <= 90:
            raise ValueError(
                f"{self.name}: dip_deg must be in [0, 90] "
                f"(0 = horizontal, 90 = vertical down); got {self.dip_deg}"
            )


@dataclass
class DrillProgramSpec:
    name: str
    crs: str
    holes: list[DrillHoleSpec]
    survey_interval_m: float = 10.0
    cost_per_metre: Optional[float] = None

    def __post_init__(self):
        if self.survey_interval_m <= 0:
            raise ValueError("survey_interval_m must be > 0")
        if not self.holes:
            raise ValueError("at least one hole required")
        names = [h.name for h in self.holes]
        if len(set(names)) != len(names):
            dups = {n for n in names if names.count(n) > 1}
            raise ValueError(f"duplicate hole names: {sorted(dups)}")
        CRS.from_user_input(self.crs)


@dataclass
class DrillPlan:
    spec: DrillProgramSpec
    collars: gpd.GeoDataFrame
    surveys: gpd.GeoDataFrame
    traces: gpd.GeoDataFrame

    @property
    def total_metres(self) -> float:
        return float(sum(h.length_m for h in self.spec.holes))

    @property
    def total_cost(self) -> Optional[float]:
        if self.spec.cost_per_metre is None:
            return None
        return self.total_metres * self.spec.cost_per_metre

    @property
    def hole_count(self) -> int:
        return len(self.spec.holes)


def downhole_position(hole: DrillHoleSpec, depth_m: float) -> tuple[float, float, float]:
    """Return (easting, northing, rl) at the given depth along the hole."""
    az_rad = math.radians(hole.azimuth_deg)
    dip_rad = math.radians(hole.dip_deg)
    h_dist = depth_m * math.cos(dip_rad)
    e = hole.collar_easting + h_dist * math.sin(az_rad)
    n = hole.collar_northing + h_dist * math.cos(az_rad)
    rl = hole.collar_rl - depth_m * math.sin(dip_rad)
    return (e, n, rl)


def _survey_depths(length_m: float, interval_m: float) -> list[float]:
    """Depths at every interval, plus the toe (length_m) if not exactly aligned."""
    depths = list(np.arange(0.0, length_m, interval_m))
    if not depths or depths[-1] != length_m:
        depths.append(length_m)
    return [float(d) for d in depths]


def generate_drill_plan(spec: DrillProgramSpec) -> DrillPlan:
    """Generate a complete drill plan: collars, 3D traces, and downhole surveys."""
    collar_records = []
    survey_records = []
    trace_records = []

    for hole in spec.holes:
        depths = _survey_depths(hole.length_m, spec.survey_interval_m)
        positions = [downhole_position(hole, d) for d in depths]

        toe_e, toe_n, toe_rl = positions[-1]
        collar_records.append({
            "hole_name": hole.name,
            "collar_e": hole.collar_easting,
            "collar_n": hole.collar_northing,
            "collar_rl": hole.collar_rl,
            "toe_e": toe_e,
            "toe_n": toe_n,
            "toe_rl": toe_rl,
            "azimuth": hole.azimuth_deg,
            "dip": hole.dip_deg,
            "length_m": hole.length_m,
            "geometry": Point(hole.collar_easting, hole.collar_northing),
        })

        for d, (e, n, rl) in zip(depths, positions):
            survey_records.append({
                "hole_name": hole.name,
                "depth_m": float(d),
                "easting": e,
                "northing": n,
                "rl": rl,
                "geometry": Point(e, n, rl),
            })

        trace_records.append({
            "hole_name": hole.name,
            "length_m": hole.length_m,
            "azimuth": hole.azimuth_deg,
            "dip": hole.dip_deg,
            "geometry": LineString(positions),
        })

    return DrillPlan(
        spec=spec,
        collars=gpd.GeoDataFrame(collar_records, crs=spec.crs),
        surveys=gpd.GeoDataFrame(survey_records, crs=spec.crs),
        traces=gpd.GeoDataFrame(trace_records, crs=spec.crs),
    )

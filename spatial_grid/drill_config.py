"""YAML config loader for drill programs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .drill import DrillHoleSpec, DrillProgramSpec


_DEFAULT_KEYS = ("default_azimuth_deg", "default_dip_deg", "default_length_m")
_DEFAULT_TO_HOLE = {
    "default_azimuth_deg": "azimuth_deg",
    "default_dip_deg": "dip_deg",
    "default_length_m": "length_m",
}


def load_drill_config(path: str | Path) -> DrillProgramSpec:
    """Load a drill program spec from a YAML config file.

    Each hole inherits any default_* values not explicitly set on the hole.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Config {path} did not parse to a mapping")

    defaults = {
        _DEFAULT_TO_HOLE[k]: data.pop(k)
        for k in _DEFAULT_KEYS
        if k in data
    }
    holes_data = data.pop("holes", [])
    if not isinstance(holes_data, list):
        raise ValueError("'holes' must be a list")

    holes = [DrillHoleSpec(**{**defaults, **(h or {})}) for h in holes_data]
    return DrillProgramSpec(holes=holes, **data)

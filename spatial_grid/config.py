"""YAML config loader."""
from __future__ import annotations

from pathlib import Path

import yaml

from .core import GridSpec


def load_config(path: str | Path) -> GridSpec:
    """Load a grid spec from a YAML config file."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Config {path} did not parse to a mapping")
    return GridSpec(**data)

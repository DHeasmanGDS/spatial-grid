"""CRS resolution helpers."""
from __future__ import annotations

from pyproj import CRS


def resolve_crs(crs_input) -> CRS:
    """Accept EPSG code, proj string, WKT, dict — return a pyproj CRS."""
    return CRS.from_user_input(crs_input)


def utm_epsg_for_lonlat(lon: float, lat: float) -> int:
    """Return the WGS84 UTM EPSG code for the zone containing (lon, lat).

    Northern hemisphere → 326XX. Southern hemisphere → 327XX.
    """
    zone = int((lon + 180) // 6) + 1
    if not 1 <= zone <= 60:
        raise ValueError(f"Longitude {lon} out of range")
    return (32600 if lat >= 0 else 32700) + zone

"""GPX exporter — for handheld GPS / Avenza Maps."""
from __future__ import annotations

from pathlib import Path

import gpxpy
import gpxpy.gpx
from pyproj import Transformer

from ..core import Grid


def write_gpx(grid: Grid, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    transformer = Transformer.from_crs(grid.spec.crs, "EPSG:4326", always_xy=True)

    gpx = gpxpy.gpx.GPX()
    gpx.name = grid.spec.grid_name

    # Stations as waypoints
    for _, stn in grid.stations.iterrows():
        lon, lat = transformer.transform(stn["easting"], stn["northing"])
        gpx.waypoints.append(
            gpxpy.gpx.GPXWaypoint(latitude=lat, longitude=lon, name=stn["station_id"])
        )

    # Lines as tracks
    for _, line in grid.lines.iterrows():
        track = gpxpy.gpx.GPXTrack(name=line["line_id"])
        seg = gpxpy.gpx.GPXTrackSegment()
        for x, y in line.geometry.coords:
            lon, lat = transformer.transform(x, y)
            seg.points.append(gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon))
        track.segments.append(seg)
        gpx.tracks.append(track)

    with path.open("w", encoding="utf-8") as f:
        f.write(gpx.to_xml())
    return path

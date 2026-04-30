"""KML exporter — for Google Earth review."""
from __future__ import annotations

from pathlib import Path

import simplekml
from pyproj import Transformer

from ..core import Grid


def write_kml(grid: Grid, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    transformer = Transformer.from_crs(grid.spec.crs, "EPSG:4326", always_xy=True)

    kml = simplekml.Kml(name=grid.spec.grid_name)
    lines_folder = kml.newfolder(name="Lines")
    stations_folder = kml.newfolder(name="Stations")

    for _, line in grid.lines.iterrows():
        coords = [transformer.transform(x, y) for x, y in line.geometry.coords]
        ls = lines_folder.newlinestring(name=line["line_id"], coords=coords)
        ls.style.linestyle.color = simplekml.Color.red
        ls.style.linestyle.width = 2

    for _, stn in grid.stations.iterrows():
        lon, lat = transformer.transform(stn["easting"], stn["northing"])
        pt = stations_folder.newpoint(name=stn["station_id"], coords=[(lon, lat)])
        pt.style.iconstyle.scale = 0.5

    kml.save(str(path))
    return path

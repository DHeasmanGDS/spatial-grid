"""Interactive Folium / Leaflet map exporter."""
from __future__ import annotations

from pathlib import Path

import folium
from pyproj import Transformer

from ..core import Grid


def render_folium(grid: Grid) -> folium.Map:
    """Build a Folium Map for the grid (lat/lon, with OSM + satellite tiles)."""
    transformer = Transformer.from_crs(grid.spec.crs, "EPSG:4326", always_xy=True)

    anchor_lon, anchor_lat = transformer.transform(
        grid.spec.centre_easting, grid.spec.centre_northing
    )

    # Compute bounds in lat/lon for fit_bounds
    sample_e = [grid.stations["easting"].min(), grid.stations["easting"].max()]
    sample_n = [grid.stations["northing"].min(), grid.stations["northing"].max()]
    corners_lonlat = [transformer.transform(e, n) for e in sample_e for n in sample_n]
    lats = [lat for _, lat in corners_lonlat]
    lons = [lon for lon, _ in corners_lonlat]
    bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]

    m = folium.Map(location=[anchor_lat, anchor_lon], tiles="OpenStreetMap",
                   control_scale=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
        overlay=False,
        control=True,
    ).add_to(m)

    lines_layer = folium.FeatureGroup(name="Lines", show=True)
    for _, line in grid.lines.iterrows():
        coords = [transformer.transform(x, y) for x, y in line.geometry.coords]
        latlon = [[lat, lon] for lon, lat in coords]
        folium.PolyLine(
            latlon,
            color="red",
            weight=2,
            opacity=0.8,
            tooltip=f"Line {line['line_id']} — {line['length_m']:.0f} m",
        ).add_to(lines_layer)
    lines_layer.add_to(m)

    stations_layer = folium.FeatureGroup(name="Stations", show=True)
    for _, stn in grid.stations.iterrows():
        lon, lat = transformer.transform(stn["easting"], stn["northing"])
        folium.CircleMarker(
            location=[lat, lon],
            radius=2.5,
            color="black",
            weight=1,
            fill=True,
            fill_color="black",
            fill_opacity=0.85,
            tooltip=f"{stn['station_id']}<br>E {stn['easting']:.1f}, N {stn['northing']:.1f}",
        ).add_to(stations_layer)
    stations_layer.add_to(m)

    anchor_label = "Centre" if grid.spec.anchor == "center" else f"Anchor ({grid.spec.anchor.upper()})"
    folium.Marker(
        [anchor_lat, anchor_lon],
        tooltip=anchor_label,
        icon=folium.Icon(color="orange", icon="star", prefix="fa"),
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.fit_bounds(bounds, padding=(20, 20))
    return m


def write_folium(grid: Grid, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    m = render_folium(grid)
    m.save(str(path))
    return path

"""Folium map for a drill plan — collar pins + surface-projected traces."""
from __future__ import annotations

from pathlib import Path

import folium
from pyproj import Transformer

from ..drill import DrillPlan


def render_drill_folium(plan: DrillPlan) -> folium.Map:
    """Build a Folium Map for the drill plan.

    Surface projection only (lat/lon). Each hole shows as a collar pin and
    a projected surface line from collar to the toe's surface projection.
    """
    transformer = Transformer.from_crs(plan.spec.crs, "EPSG:4326", always_xy=True)

    eastings = plan.collars["collar_e"].tolist() + plan.collars["toe_e"].tolist()
    northings = plan.collars["collar_n"].tolist() + plan.collars["toe_n"].tolist()
    e_centre = sum(plan.collars["collar_e"]) / len(plan.collars)
    n_centre = sum(plan.collars["collar_n"]) / len(plan.collars)
    centre_lon, centre_lat = transformer.transform(e_centre, n_centre)

    m = folium.Map(location=[centre_lat, centre_lon], tiles="OpenStreetMap",
                   control_scale=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
        overlay=False,
        control=True,
    ).add_to(m)

    proj_layer = folium.FeatureGroup(name="Surface projection", show=True)
    collars_layer = folium.FeatureGroup(name="Collars", show=True)

    for _, row in plan.collars.iterrows():
        coll_lon, coll_lat = transformer.transform(row["collar_e"], row["collar_n"])
        toe_lon, toe_lat = transformer.transform(row["toe_e"], row["toe_n"])

        folium.PolyLine(
            locations=[[coll_lat, coll_lon], [toe_lat, toe_lon]],
            color="#7f1d1d",
            weight=2,
            opacity=0.85,
            tooltip=f"{row['hole_name']} surface projection",
        ).add_to(proj_layer)

        folium.CircleMarker(
            location=[coll_lat, coll_lon],
            radius=5,
            color="#002244",
            weight=2,
            fill=True,
            fill_color="#fb923c",
            fill_opacity=0.95,
            tooltip=(
                f"<b>{row['hole_name']}</b><br>"
                f"Az {row['azimuth']:.0f}° / Dip {row['dip']:.0f}°<br>"
                f"Length {row['length_m']:.0f} m<br>"
                f"Collar RL {row['collar_rl']:.1f} → Toe RL {row['toe_rl']:.1f}"
            ),
        ).add_to(collars_layer)

    proj_layer.add_to(m)
    collars_layer.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    corners = [transformer.transform(e, n) for e in (min(eastings), max(eastings))
               for n in (min(northings), max(northings))]
    lats = [lat for _, lat in corners]
    lons = [lon for lon, _ in corners]
    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(40, 40))
    return m


def write_drill_folium(plan: DrillPlan, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    render_drill_folium(plan).save(str(path))
    return path


def render_combined_map(
    drill_crs: str,
    grid_stations=None,
    plan: DrillPlan | None = None,
    height_hint: int = 550,
) -> folium.Map:
    """Combined map for the click-to-add picker.

    Optional grid stations (lighter circles) + optional planned holes
    (collars + surface-projected traces). Either or both can be empty;
    the map still renders so the user has something to click on.
    """
    transformer = Transformer.from_crs(drill_crs, "EPSG:4326", always_xy=True)

    # Determine map centre. Prefer grid centroid, fall back to plan centroid,
    # finally a generic default that gets overridden once data exists.
    if grid_stations is not None and len(grid_stations) > 0:
        e_centre = float(grid_stations["easting"].mean())
        n_centre = float(grid_stations["northing"].mean())
    elif plan is not None and len(plan.collars) > 0:
        e_centre = float(plan.collars["collar_e"].mean())
        n_centre = float(plan.collars["collar_n"].mean())
    else:
        e_centre = 500000.0
        n_centre = 5000000.0
    centre_lon, centre_lat = transformer.transform(e_centre, n_centre)

    m = folium.Map(location=[centre_lat, centre_lon], tiles="OpenStreetMap",
                   control_scale=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Satellite", overlay=False, control=True,
    ).add_to(m)

    # Grid stations layer
    if grid_stations is not None and len(grid_stations) > 0:
        gl = folium.FeatureGroup(name="Grid stations", show=True)
        for _, s in grid_stations.iterrows():
            lon, lat = transformer.transform(s["easting"], s["northing"])
            folium.CircleMarker(
                location=[lat, lon],
                radius=2.5,
                color="#475569",
                weight=1,
                fill=True,
                fill_color="#94a3b8",
                fill_opacity=0.7,
                tooltip=str(s["station_id"]),
            ).add_to(gl)
        gl.add_to(m)

    # Planned holes layers
    if plan is not None and len(plan.collars) > 0:
        proj_layer = folium.FeatureGroup(name="Surface projection", show=True)
        coll_layer = folium.FeatureGroup(name="Planned collars", show=True)
        for _, row in plan.collars.iterrows():
            coll_lon, coll_lat = transformer.transform(row["collar_e"], row["collar_n"])
            toe_lon, toe_lat = transformer.transform(row["toe_e"], row["toe_n"])
            folium.PolyLine(
                locations=[[coll_lat, coll_lon], [toe_lat, toe_lon]],
                color="#7f1d1d", weight=2, opacity=0.85,
                tooltip=f"{row['hole_name']} surface projection",
            ).add_to(proj_layer)
            folium.CircleMarker(
                location=[coll_lat, coll_lon],
                radius=5,
                color="#002244",
                weight=2,
                fill=True,
                fill_color="#fb923c",
                fill_opacity=0.95,
                tooltip=(
                    f"<b>{row['hole_name']}</b><br>"
                    f"Az {row['azimuth']:.0f}° / Dip {row['dip']:.0f}°<br>"
                    f"Length {row['length_m']:.0f} m"
                ),
            ).add_to(coll_layer)
        proj_layer.add_to(m)
        coll_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Fit bounds: prefer combined extent
    eastings, northings = [], []
    if grid_stations is not None and len(grid_stations) > 0:
        eastings += grid_stations["easting"].tolist()
        northings += grid_stations["northing"].tolist()
    if plan is not None and len(plan.collars) > 0:
        eastings += plan.collars["collar_e"].tolist() + plan.collars["toe_e"].tolist()
        northings += plan.collars["collar_n"].tolist() + plan.collars["toe_n"].tolist()
    if eastings:
        corners = [transformer.transform(e, n) for e in (min(eastings), max(eastings))
                   for n in (min(northings), max(northings))]
        lats = [lat for _, lat in corners]
        lons = [lon for lon, _ in corners]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(40, 40))
    return m

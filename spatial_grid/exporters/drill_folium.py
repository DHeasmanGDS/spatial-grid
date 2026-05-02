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


def render_drill_base_map(
    drill_crs: str,
    grid_stations=None,
) -> folium.Map:
    """Stable portion of the drill map — tiles + grid stations only.

    Designed to be passed as `m` to st_folium with planned holes added via
    `feature_group_to_add`. Because the base content is stable across
    sidebar interactions, st_folium preserves the iframe state (zoom/pan
    don't reset on every rerun).
    """
    transformer = Transformer.from_crs(drill_crs, "EPSG:4326", always_xy=True)

    if grid_stations is not None and len(grid_stations) > 0:
        e_centre = float(grid_stations["easting"].mean())
        n_centre = float(grid_stations["northing"].mean())
        e_min = float(grid_stations["easting"].min())
        e_max = float(grid_stations["easting"].max())
        n_min = float(grid_stations["northing"].min())
        n_max = float(grid_stations["northing"].max())
    else:
        e_centre, n_centre = 500000.0, 5000000.0
        e_min = e_max = e_centre
        n_min = n_max = n_centre
    centre_lon, centre_lat = transformer.transform(e_centre, n_centre)

    m = folium.Map(location=[centre_lat, centre_lon], tiles="OpenStreetMap",
                   control_scale=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Satellite", overlay=False, control=True,
    ).add_to(m)

    if grid_stations is not None and len(grid_stations) > 0:
        gl = folium.FeatureGroup(name="Grid stations", show=True)
        for _, s in grid_stations.iterrows():
            lon, lat = transformer.transform(s["easting"], s["northing"])
            folium.CircleMarker(
                location=[lat, lon],
                radius=6,
                color="#1e3a8a",
                weight=1,
                fill=True,
                fill_color="#bfdbfe",
                fill_opacity=0.85,
                tooltip=str(s["station_id"]),
            ).add_to(gl)
        gl.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    if e_max != e_min or n_max != n_min:
        corners = [transformer.transform(e, n)
                   for e in (e_min, e_max)
                   for n in (n_min, n_max)]
        lats = [lat for _, lat in corners]
        lons = [lon for lon, _ in corners]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(40, 40))
    return m


def render_planned_holes_group(
    plan: DrillPlan | None,
    drill_crs: str,
) -> folium.FeatureGroup:
    """Feature group containing planned hole collars + surface-projected traces.

    Pass to st_folium as `feature_group_to_add` so it updates without
    re-rendering the base map.
    """
    fg = folium.FeatureGroup(name="Planned holes")
    if plan is None or len(plan.collars) == 0:
        return fg

    transformer = Transformer.from_crs(drill_crs, "EPSG:4326", always_xy=True)

    for _, row in plan.collars.iterrows():
        coll_lon, coll_lat = transformer.transform(row["collar_e"], row["collar_n"])
        toe_lon, toe_lat = transformer.transform(row["toe_e"], row["toe_n"])

        folium.PolyLine(
            locations=[[coll_lat, coll_lon], [toe_lat, toe_lon]],
            color="#7f1d1d", weight=2, opacity=0.85,
            tooltip=f"{row['hole_name']} surface projection",
        ).add_to(fg)

        folium.CircleMarker(
            location=[coll_lat, coll_lon],
            radius=8,
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
        ).add_to(fg)
    return fg


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
                radius=6,
                color="#1e3a8a",
                weight=1,
                fill=True,
                fill_color="#bfdbfe",
                fill_opacity=0.85,
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
                radius=8,
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

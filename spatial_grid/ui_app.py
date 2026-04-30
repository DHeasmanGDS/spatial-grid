"""Streamlit UI for spatial-grid.

Run via the console script:
    spatial-grid-ui
or directly:
    streamlit run -m spatial_grid.ui_app
"""
from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st
from pyproj import Transformer
from streamlit_folium import st_folium

from spatial_grid.core import VALID_ANCHORS, GridSpec, generate_grid
from spatial_grid.crs import utm_epsg_for_lonlat
from spatial_grid.exporters.excel import write_excel
from spatial_grid.exporters.folium_map import render_folium, write_folium
from spatial_grid.exporters.gpx import write_gpx
from spatial_grid.exporters.kml import write_kml
from spatial_grid.exporters.preview import write_preview
from spatial_grid.exporters.shapefile import write_shapefile

NAMING_SCHEMES = ["chainage", "sequential", "signed"]


def _sidebar_inputs() -> GridSpec:
    st.sidebar.header("Grid parameters")

    grid_name = st.sidebar.text_input("Grid name", value="MY_GRID")

    st.sidebar.subheader("Reference point")
    coord_mode = st.sidebar.radio(
        "Input as", ["UTM (E/N)", "Lat / Lon (auto UTM)"], horizontal=True,
    )
    if coord_mode == "UTM (E/N)":
        crs = st.sidebar.text_input("CRS", value="EPSG:32617")
        ce = st.sidebar.number_input("Easting", value=567000.0, step=100.0, format="%.2f")
        cn = st.sidebar.number_input("Northing", value=5340000.0, step=100.0, format="%.2f")
    else:
        lat = st.sidebar.number_input("Latitude", value=48.150, format="%.6f")
        lon = st.sidebar.number_input("Longitude", value=-80.040, format="%.6f")
        epsg = utm_epsg_for_lonlat(lon, lat)
        crs = f"EPSG:{epsg}"
        t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        ce, cn = t.transform(lon, lat)
        st.sidebar.caption(f"→ {crs}: E={ce:,.1f}, N={cn:,.1f}")

    anchor = st.sidebar.radio("Anchor", VALID_ANCHORS, index=0, horizontal=True)

    st.sidebar.subheader("Geometry")
    azimuth = st.sidebar.slider("Azimuth (°)", min_value=0, max_value=359, value=45)
    line_spacing = st.sidebar.number_input("Line spacing (m)", value=100.0, min_value=1.0)
    station_spacing = st.sidebar.number_input("Station spacing (m)", value=25.0, min_value=1.0)
    num_lines = st.sidebar.number_input("Number of lines", value=21, min_value=1, step=1)
    num_stations = st.sidebar.number_input("Stations per line", value=41, min_value=2, step=1)

    st.sidebar.subheader("Naming")
    line_naming = st.sidebar.selectbox("Line naming", NAMING_SCHEMES, index=0)
    station_naming = st.sidebar.selectbox("Station naming", NAMING_SCHEMES, index=0)

    return GridSpec(
        centre_easting=float(ce),
        centre_northing=float(cn),
        azimuth_deg=float(azimuth),
        line_spacing=float(line_spacing),
        station_spacing=float(station_spacing),
        num_lines=int(num_lines),
        num_stations=int(num_stations),
        crs=crs,
        grid_name=grid_name,
        anchor=anchor,
        line_naming=line_naming,
        station_naming=station_naming,
    )


def _make_excel_bytes(grid) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "g.xlsx"
        write_excel(grid, p)
        return p.read_bytes()


def _make_shp_zip_bytes(grid, basename: str) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        write_shapefile(grid, td, basename)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in Path(td).iterdir():
                zf.write(f, f.name)
        return buf.getvalue()


def _make_kml_bytes(grid) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "g.kml"
        write_kml(grid, p)
        return p.read_bytes()


def _make_gpx_bytes(grid) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "g.gpx"
        write_gpx(grid, p)
        return p.read_bytes()


def _make_png_bytes(grid) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "g.png"
        write_preview(grid, p)
        return p.read_bytes()


def _make_html_bytes(grid) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "g.html"
        write_folium(grid, p)
        return p.read_bytes()


def main() -> None:
    st.set_page_config(page_title="spatial-grid", layout="wide", page_icon=":compass:")
    st.title("spatial-grid — geophysical grid generator")
    st.caption("Local survey grids for geophysical and drill-hole planning. Configure on the left, preview live, download below.")

    try:
        spec = _sidebar_inputs()
        grid = generate_grid(spec)
    except (ValueError, Exception) as e:  # noqa: BLE001
        st.error(f"Invalid configuration: {e}")
        return

    base = spec.grid_name.replace(" ", "_") or "grid"

    # Top metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stations", grid.total_stations)
    c2.metric("Lines", spec.num_lines)
    c3.metric("Line-km", f"{grid.total_line_km:.2f}")
    c4.metric("CRS", spec.crs)

    # Map + downloads
    map_col, dl_col = st.columns([3, 1])
    with map_col:
        st.subheader("Map preview")
        m = render_folium(grid)
        st_folium(m, width=None, height=600, returned_objects=[])

    with dl_col:
        st.subheader("Downloads")
        st.download_button("Excel (.xlsx)", _make_excel_bytes(grid),
                           file_name=f"{base}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Shapefile bundle (.zip)", _make_shp_zip_bytes(grid, base),
                           file_name=f"{base}_shp.zip", mime="application/zip")
        st.download_button("KML (Google Earth)", _make_kml_bytes(grid),
                           file_name=f"{base}.kml",
                           mime="application/vnd.google-earth.kml+xml")
        st.download_button("GPX (handheld GPS)", _make_gpx_bytes(grid),
                           file_name=f"{base}.gpx", mime="application/gpx+xml")
        st.download_button("Static map (.png)", _make_png_bytes(grid),
                           file_name=f"{base}_preview.png", mime="image/png")
        st.download_button("Interactive map (.html)", _make_html_bytes(grid),
                           file_name=f"{base}_map.html", mime="text/html")

    # Tables
    st.subheader("Stations")
    df = pd.DataFrame(grid.stations.drop(columns=["geometry"]))
    st.dataframe(df, use_container_width=True, height=300)

    with st.expander("Lines"):
        ldf = pd.DataFrame(grid.lines.drop(columns=["geometry"]))
        st.dataframe(ldf, use_container_width=True)


# Streamlit runs the file top-to-bottom on every interaction
main()

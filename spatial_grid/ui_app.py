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
from spatial_grid.drill import DrillHoleSpec, DrillProgramSpec, generate_drill_plan
from spatial_grid.exporters.drill_export import (
    write_drill_csv,
    write_drill_excel,
    write_drill_shapefiles,
)
from spatial_grid.exporters.drill_folium import render_drill_folium
from spatial_grid.exporters.excel import write_excel
from spatial_grid.exporters.folium_map import render_folium, write_folium
from spatial_grid.exporters.gpx import write_gpx
from spatial_grid.exporters.kml import write_kml
from spatial_grid.exporters.preview import write_preview
from spatial_grid.exporters.shapefile import write_shapefile

NAMING_SCHEMES = ["chainage", "sequential", "signed"]
MODES = ("Survey grid", "Drill program")

# Columns the drill holes table editor knows about.
HOLE_COLS = ["name", "easting", "northing", "rl", "azimuth_deg", "dip_deg", "length_m"]


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
    azimuth = st.sidebar.number_input(
        "Azimuth (°)", min_value=0.0, max_value=360.0, value=45.0, step=1.0,
        help="Direction the survey lines run, degrees clockwise from north.",
    )
    line_spacing = st.sidebar.number_input("Line spacing (m)", value=100.0, min_value=1.0)
    station_spacing = st.sidebar.number_input("Station spacing (m)", value=25.0, min_value=1.0)

    size_mode = st.sidebar.radio(
        "Specify grid size by", ["Counts", "Extents (m)"], horizontal=True,
        help="Counts = number of lines / stations. Extents = grid width and line length in metres; counts auto-derived from spacing.",
    )
    if size_mode == "Counts":
        num_lines = int(st.sidebar.number_input("Number of lines", value=21, min_value=1, step=1))
        num_stations = int(st.sidebar.number_input("Stations per line", value=41, min_value=2, step=1))
        grid_width_m = None
        line_length_m = None
        st.sidebar.caption(
            f"→ grid is {(num_lines - 1) * line_spacing:,.0f} m wide × "
            f"{(num_stations - 1) * station_spacing:,.0f} m long"
        )
    else:
        grid_width_m = st.sidebar.number_input(
            "Grid width (m)", value=2000.0, min_value=1.0, step=100.0,
            help="Total spread of lines, perpendicular to azimuth.",
        )
        line_length_m = st.sidebar.number_input(
            "Line length (m)", value=1000.0, min_value=1.0, step=100.0,
        )
        num_lines = None
        num_stations = None
        derived_lines = int(round(grid_width_m / line_spacing)) + 1
        derived_stations = int(round(line_length_m / station_spacing)) + 1
        st.sidebar.caption(
            f"→ {derived_lines} lines × {derived_stations} stations"
        )

    st.sidebar.subheader("Naming")
    line_naming = st.sidebar.selectbox("Line naming", NAMING_SCHEMES, index=0)
    station_naming = st.sidebar.selectbox("Station naming", NAMING_SCHEMES, index=0)

    return GridSpec(
        centre_easting=float(ce),
        centre_northing=float(cn),
        azimuth_deg=float(azimuth),
        line_spacing=float(line_spacing),
        station_spacing=float(station_spacing),
        num_lines=num_lines,
        num_stations=num_stations,
        grid_width_m=grid_width_m,
        line_length_m=line_length_m,
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


_HERO_HTML = """
<div style="
    background: linear-gradient(135deg, #002244 0%, #1e3a8a 100%);
    padding: 1.6rem 1.8rem;
    border-radius: 8px;
    margin: 0 0 1.5rem 0;
    color: #ffffff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
">
    <div style="display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:.5rem">
        <h1 style="margin:0;color:#ffffff;font-size:1.9rem;font-weight:700;letter-spacing:-0.01em">
            spatial-grid
        </h1>
        <a href="https://www.smcg-services.com" target="_blank"
           style="color:#cbd5e1;text-decoration:none;font-size:.85rem;opacity:.9">
            an SMCG tool &rarr;
        </a>
    </div>
    <p style="margin:.4rem 0 0;opacity:.92;font-size:1rem;line-height:1.45">
        Local geophysical grids and drill-hole plans for lean exploration teams.
        Configure on the left, preview live, download below.
    </p>
</div>
"""


def _grid_main() -> None:
    """Survey-grid mode: existing behaviour."""
    try:
        spec = _sidebar_inputs()
        grid = generate_grid(spec)
    except (ValueError, Exception) as e:  # noqa: BLE001
        st.error(f"Invalid configuration: {e}")
        return

    base = spec.grid_name.replace(" ", "_") or "grid"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stations", grid.total_stations)
    c2.metric("Lines", spec.num_lines)
    c3.metric("Line-km", f"{grid.total_line_km:.2f}")
    c4.metric("CRS", spec.crs)

    map_col, dl_col = st.columns([3, 1])
    with map_col:
        st.subheader("Map preview")
        m = render_folium(grid)
        st_folium(m, width=None, height=600, returned_objects=[])

    with dl_col:
        st.subheader("Downloads")
        st.download_button(
            "Excel (.xlsx)", _make_excel_bytes(grid),
            file_name=f"{base}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary", use_container_width=True,
        )
        st.download_button(
            "Shapefile bundle (.zip)", _make_shp_zip_bytes(grid, base),
            file_name=f"{base}_shp.zip", mime="application/zip",
            type="primary", use_container_width=True,
        )
        st.download_button(
            "KML (Google Earth)", _make_kml_bytes(grid),
            file_name=f"{base}.kml",
            mime="application/vnd.google-earth.kml+xml",
            type="primary", use_container_width=True,
        )
        st.download_button(
            "GPX (handheld GPS)", _make_gpx_bytes(grid),
            file_name=f"{base}.gpx", mime="application/gpx+xml",
            type="primary", use_container_width=True,
        )
        st.download_button(
            "Static map (.png)", _make_png_bytes(grid),
            file_name=f"{base}_preview.png", mime="image/png",
            type="primary", use_container_width=True,
        )
        st.download_button(
            "Interactive map (.html)", _make_html_bytes(grid),
            file_name=f"{base}_map.html", mime="text/html",
            type="primary", use_container_width=True,
        )

    st.subheader("Stations")
    df = pd.DataFrame(grid.stations.drop(columns=["geometry"]))
    st.dataframe(df, use_container_width=True, height=300)

    with st.expander("Lines"):
        ldf = pd.DataFrame(grid.lines.drop(columns=["geometry"]))
        st.dataframe(ldf, use_container_width=True)


# ---------------------------------------------------------------------------
# Drill program mode
# ---------------------------------------------------------------------------

def _default_holes_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"name": "H-001", "easting": 567050.0, "northing": 5340075.0, "rl": 320.0,
         "azimuth_deg": None, "dip_deg": None, "length_m": None},
        {"name": "H-002", "easting": 567150.0, "northing": 5340150.0, "rl": 320.0,
         "azimuth_deg": None, "dip_deg": None, "length_m": None},
    ], columns=HOLE_COLS)


def _drill_sidebar_inputs() -> dict:
    """Render drill defaults to the sidebar; return a dict."""
    st.sidebar.header("Drill defaults")
    name = st.sidebar.text_input("Program name", value="MY_PROGRAM")
    crs = st.sidebar.text_input("CRS", value="EPSG:32617")
    survey_interval_m = st.sidebar.number_input(
        "Survey interval (m)", value=10.0, min_value=1.0,
        help="Spacing between downhole survey points.",
    )
    cost_per_metre = st.sidebar.number_input(
        "Cost per metre (CAD)", value=200.0, min_value=0.0,
        help="Set to 0 to omit cost from the program summary.",
    )

    st.sidebar.subheader("Per-hole defaults")
    st.sidebar.caption("Used for any hole row that leaves the field blank.")
    default_azimuth_deg = st.sidebar.number_input(
        "Default azimuth (°)", min_value=0.0, max_value=360.0, value=270.0, step=1.0,
    )
    default_dip_deg = st.sidebar.number_input(
        "Default dip (°)", min_value=0.0, max_value=90.0, value=60.0, step=1.0,
        help="0 = horizontal, 90 = vertical down.",
    )
    default_length_m = st.sidebar.number_input(
        "Default length (m)", min_value=1.0, value=200.0, step=10.0,
    )

    return {
        "name": name,
        "crs": crs,
        "survey_interval_m": float(survey_interval_m),
        "cost_per_metre": float(cost_per_metre) if cost_per_metre > 0 else None,
        "default_azimuth_deg": float(default_azimuth_deg),
        "default_dip_deg": float(default_dip_deg),
        "default_length_m": float(default_length_m),
    }


def _coerce_holes_df(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case headers, ensure all expected columns exist."""
    df = df.copy()
    df.columns = [c.lower().strip() for c in df.columns]
    for col in HOLE_COLS:
        if col not in df.columns:
            df[col] = None
    return df[HOLE_COLS]


def _build_holes(df: pd.DataFrame, defaults: dict) -> list[DrillHoleSpec]:
    holes = []
    for _, row in df.iterrows():
        name = row.get("name")
        if name is None or (isinstance(name, float) and pd.isna(name)) or str(name).strip() == "":
            continue
        easting = row.get("easting")
        northing = row.get("northing")
        if pd.isna(easting) or pd.isna(northing):
            raise ValueError(f"Hole '{name}' is missing easting or northing")

        def _val(col, fallback):
            v = row.get(col)
            return float(v) if v is not None and not pd.isna(v) else float(fallback)

        holes.append(DrillHoleSpec(
            name=str(name),
            collar_easting=float(easting),
            collar_northing=float(northing),
            collar_rl=_val("rl", 0.0),
            azimuth_deg=_val("azimuth_deg", defaults["default_azimuth_deg"]),
            dip_deg=_val("dip_deg", defaults["default_dip_deg"]),
            length_m=_val("length_m", defaults["default_length_m"]),
        ))
    return holes


def _make_drill_excel_bytes(plan) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "drill.xlsx"
        write_drill_excel(plan, p)
        return p.read_bytes()


def _make_drill_shp_zip_bytes(plan, basename: str) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        write_drill_shapefiles(plan, td, basename)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in Path(td).iterdir():
                zf.write(f, f.name)
        return buf.getvalue()


def _make_drill_csv_bytes(plan) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "drill.csv"
        write_drill_csv(plan, p)
        return p.read_bytes()


def _drill_main() -> None:
    """Drill-program mode: edit holes inline + import CSV + preview + download."""
    defaults = _drill_sidebar_inputs()

    if "drill_holes_df" not in st.session_state:
        st.session_state.drill_holes_df = _default_holes_df()
    if "drill_editor_v" not in st.session_state:
        st.session_state.drill_editor_v = 0

    with st.expander("Import holes from CSV", expanded=False):
        st.caption(
            "Headers (case-insensitive): "
            "`name, easting, northing, rl, azimuth_deg, dip_deg, length_m`. "
            "Az / dip / length empty → uses the defaults from the sidebar."
        )
        csv_text = st.text_area("Paste CSV", height=140, key="drill_csv_input",
                                placeholder="name,easting,northing,rl,azimuth_deg,dip_deg,length_m\nKL-001,567050,5340075,320,,,\n...")
        if st.button("Apply CSV", type="primary"):
            try:
                df = pd.read_csv(io.StringIO(csv_text))
                df = _coerce_holes_df(df)
                st.session_state.drill_holes_df = df
                st.session_state.drill_editor_v += 1
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"CSV parse error: {e}")

    st.subheader("Holes")
    edited = st.data_editor(
        st.session_state.drill_holes_df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"drill_editor_{st.session_state.drill_editor_v}",
        column_config={
            "name": st.column_config.TextColumn("Hole name", required=True),
            "easting": st.column_config.NumberColumn("Easting", format="%.2f", required=True),
            "northing": st.column_config.NumberColumn("Northing", format="%.2f", required=True),
            "rl": st.column_config.NumberColumn("RL (collar)", format="%.2f"),
            "azimuth_deg": st.column_config.NumberColumn("Azimuth (°)", format="%.1f",
                                                          help="Empty → use default"),
            "dip_deg": st.column_config.NumberColumn("Dip (°)", format="%.1f",
                                                      help="Empty → use default; 0=horizontal, 90=vertical"),
            "length_m": st.column_config.NumberColumn("Length (m)", format="%.1f",
                                                       help="Empty → use default"),
        },
    )
    st.session_state.drill_holes_df = edited

    try:
        holes = _build_holes(edited, defaults)
    except ValueError as e:
        st.error(f"Holes table error: {e}")
        return

    if not holes:
        st.info("Add at least one hole to preview the program.")
        return

    try:
        program_spec = DrillProgramSpec(
            name=defaults["name"] or "PROGRAM",
            crs=defaults["crs"],
            holes=holes,
            survey_interval_m=defaults["survey_interval_m"],
            cost_per_metre=defaults["cost_per_metre"],
        )
        plan = generate_drill_plan(program_spec)
    except ValueError as e:
        st.error(f"Invalid program: {e}")
        return

    base = program_spec.name.replace(" ", "_") or "program"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Holes", plan.hole_count)
    c2.metric("Total metres", f"{plan.total_metres:,.0f}")
    if plan.total_cost is not None:
        c3.metric("Estimated cost", f"${plan.total_cost:,.0f}")
    else:
        c3.metric("Estimated cost", "—")
    c4.metric("CRS", program_spec.crs)

    map_col, dl_col = st.columns([3, 1])
    with map_col:
        st.subheader("Map preview")
        m = render_drill_folium(plan)
        st_folium(m, width=None, height=550, returned_objects=[])

    with dl_col:
        st.subheader("Downloads")
        st.download_button(
            "Excel (.xlsx)", _make_drill_excel_bytes(plan),
            file_name=f"{base}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary", use_container_width=True,
        )
        st.download_button(
            "Shapefile bundle (.zip)", _make_drill_shp_zip_bytes(plan, base),
            file_name=f"{base}_drill_shp.zip", mime="application/zip",
            type="primary", use_container_width=True,
        )
        st.download_button(
            "Surveys CSV", _make_drill_csv_bytes(plan),
            file_name=f"{base}_surveys.csv", mime="text/csv",
            type="primary", use_container_width=True,
        )

    with st.expander("Holes — computed collar/toe coordinates"):
        st.dataframe(plan.collars.drop(columns=["geometry"]),
                     use_container_width=True)
    with st.expander("Surveys"):
        st.dataframe(plan.surveys.drop(columns=["geometry"]),
                     use_container_width=True, height=300)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="spatial-grid — SMCG", layout="wide", page_icon=":compass:")
    st.markdown(_HERO_HTML, unsafe_allow_html=True)

    st.sidebar.markdown("### Mode")
    mode = st.sidebar.radio(
        "Mode", MODES, label_visibility="collapsed", horizontal=True, key="mode",
    )
    st.sidebar.divider()

    if mode == "Survey grid":
        _grid_main()
    else:
        _drill_main()


# Streamlit runs the file top-to-bottom on every interaction
main()

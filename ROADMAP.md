# Roadmap

Living list of planned and proposed work. Items are grouped by release; within a release they're rough priority order. Ranges (v0.2–0.3) mean "could land in either, depends on demand."

## v0.1 — shipped

- Core orthogonal grid generation (centre + azimuth + spacings)
- Anchor selection: `center | sw | se | nw | ne`
- Naming schemes: sequential / chainage / signed
- Exporters: Excel, shapefile, KML, GPX, PNG preview, interactive Folium HTML
- YAML config + CLI
- Streamlit browser UI
- Grid sized by **counts OR extents** (`num_lines` / `num_stations`, or `grid_width_m` / `line_length_m` — counts auto-derived from spacing)
- Azimuth as numeric input (precise) rather than slider
- Public deploy at tools.smcg-services.com behind Cloudflare Tunnel

---

## v0.2 — drill-hole planning is the headline

Make this the tool exploration teams actually use to plan a program, not just lay out stations. Items in priority order:

### Drill — UI + ergonomics
- ✅ **Drill UI integration** — sidebar mode selector switches between Survey grid and Drill program. Drill mode has defaults panel (program name, CRS, survey interval, cost/m, default azimuth/dip/length), an inline editable holes table, live Folium preview (collars + surface-projected traces), and downloads (Excel, shapefile bundle zip, surveys CSV).
- ✅ **Bulk CSV hole import** — paste a `name,easting,northing,rl,azimuth_deg,dip_deg,length_m` CSV in the Import expander; case-insensitive headers; missing az/dip/length fall back to sidebar defaults.
- ✅ **Click-to-add hole picker** — main map in Drill mode is clickable. Each click adds a hole, snapping to the nearest grid station within a configurable threshold (default 50 m). Sidebar configures hole naming as **prefix + counter + zero-pad** (e.g. `ANG_DD_` + 14 + pad 3 → `ANG_DD_014`); next-click name is previewed above the map. Bulk "populate every Nth station" is kept as a power-user expander below.
- **Combined map view** — show grid + drill collars + drill traces overlaid in the same Folium map; collars as orange pins, traces as projected lines coloured by hole length

### Drill — analytics + visualisation
- **3D Plotly preview** — true 3D drill traces with terrain shading; rotates / zooms in the browser. The 2D Folium projection misses dip; this fixes that
- **Section views** — given a strike orientation, generate cross-section "strip maps" with holes projected onto the section plane. Standard exploration deliverable
- **Hole proximity / collision warning** — flag pairs of planned holes whose traces come within a configurable threshold (default 5 m) — catches errors before the rig moves
- **Cost breakdown by category** — phase / depth class / hole type tables in the Summary sheet, not just a single total

### Drill — integrations
- **Existing-collar import + diff** — read previously-drilled collars from CSV, overlay them, and (optionally) generate an infill program around them
- **Section line generator** — given a strike orientation (or interpreted from a target polygon), generate cross-section lines through priority targets, perpendicular to strike

### Grid quality-of-life (smaller items)
- **Tenement / permit clipping** — read a polygon (shp / GeoJSON / KML), clip the grid to inside; report the count of stations dropped
- **Exclusion-zone buffers** — buffer features (creeks, roads, heritage) and drop stations within the buffer; report which lines are partially affected
- **Auto UTM zone in CLI / config** — already in the UI; promote to YAML config via a `centre_lat` / `centre_lon` alternative to easting/northing
- **PDF report generation** — one-click drill plan report with map, hole table, summary metrics

### Already shipped (v0.2 alpha)
- ✅ Drill-hole planning core — explicit collar list with azimuth/dip/length; outputs collars (2D), traces (3D LineStrings), downhole surveys at user-set interval; Excel + shapefile + CSV. New CLI: `spatial-grid-drill`.
- ✅ Drill metres + cost estimate — `cost_per_metre` in the config produces a total program cost on the Summary sheet.

## v0.3 — terrain awareness + alternative survey geometries

- **DEM drape** — sample elevation at each station from a user-supplied raster (GeoTIFF); compute true-ground length per segment vs. planar; flag steep segments by slope threshold; add `z` and `slope_pct` columns to outputs
- **Walking time estimate** — using slope + a Tobler-style hiking function, estimate field crew time per line
- **Survey patterns** — additional `pattern` types beyond the default orthogonal: baseline + crosslines (common for ground mag/IP), TEM loop layouts, dipole-dipole and gradient IP arrays (Tx/Rx pair generation), drone mag flight plans (with altitude column)
- **3D outputs** — once stations have z, write 3D shapefiles and a 3D-aware folium-equivalent (CesiumJS HTML or Plotly 3D)

## v0.4 — field-ready outputs

Stuff a crew can actually take into the bush.

- **GeoPDF / printable map** — ReportLab or `geopdf`-style output: page-sized map with grid overlay, station IDs, reference grid, scale bar, north arrow, title block
- **DXF / DWG** — for surveyor handoff (`ezdxf`)
- **GeoPackage** — single-file, multi-layer alternative to shapefile bundles
- **QR codes per station** — printable sheet matching station IDs to QR codes for tablet field workflow
- **Avenza Maps templates** — drop straight into the field tablet workflow

## v0.5 — reverse + QC

The other direction: take what was actually collected, compare to plan.

- **Read collected GPS** — ingest GPX / CSV from handheld units, snap to nearest planned station, report distance off-plan
- **Hit / miss report** — which stations were collected, which were missed, line-by-line completion %
- **Replan tool** — given a planned grid + a partial collected dataset, generate a "remaining work" config

## v0.6 — integrations + smarter inputs

- **Read existing collars** — drop a CSV of historical drill collars; auto-pick a centre / orientation that maximizes infill coverage
- **Target-driven placement** — read a target polygon set, centre the grid on the highest-priority target with auto azimuth = perpendicular to interpreted strike
- **Industry exports** — Leapfrog Geo, Micromine, Surpac, Vulcan format adapters (probably one or two of these, based on real demand)
- **ArcGIS Online / QGIS server** — push outputs to a hosted layer, not just files on disk

## v0.7 — collaboration + automation

- **Public deploy** at `tools.smcg-services.com` — k3s manifest + Cloudflare Tunnel hostname (see [DEPLOY.md](DEPLOY.md)) — *in progress*
- **Multi-grid plans** — define several grids in one config (regional + infill + drill collars) and export as a bundle
- **Versioned plans** — `spatial-grid diff plan_v1.yaml plan_v2.yaml` shows what changed between iterations
- **GitHub Action** — run `spatial-grid` on PRs that touch a `*.grid.yaml`, post the preview map as a PR comment
- **Tools landing page** — `tools.smcg-services.com` becomes a directory of small geo tools as the family grows

---

## Quality of life (any release)

- GitHub Actions CI: ruff + pytest matrix on push / PR
- Pre-commit hooks (ruff format, ruff check, end-of-file fixer)
- Docker image for the CLI (avoids the "geopandas needs GDAL" install dance)
- Sphinx / mkdocs site with the API reference + worked examples
- Better error messages — currently a bad CRS string gives a deep pyproj traceback; should be caught and rewritten with a hint
- Progress bars on big grids (>10k stations)
- Performance: vectorise station/line generation (current per-station loop is fine up to ~50k stations, will start to drag beyond that)

## Discarded / explicitly out of scope

- Full GIS app — this is a generator, not QGIS. If you need to edit, use QGIS.
- 3D inversion / forward modelling — pretend this is a SimPEG bridge if you want; this tool stops at survey planning.
- Web hosting / multi-user — the Streamlit UI is single-user; if a team needs shared planning, deploy your own instance and put it behind SSO.

## Contributing ideas

Open an issue with the `enhancement` label or just edit this file in a PR.

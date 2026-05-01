# spatial-grid

Generate local geophysical grids for survey and drill-hole planning.

Given a reference point, azimuth, line spacing, and station spacing, `spatial-grid` produces:

- **Excel** workbook (Parameters, Summary, Lines, Stations sheets)
- **Shapefile** pair (`*_lines.shp`, `*_stations.shp`) with `.prj`
- **KML** for Google Earth review
- **GPX** for handheld GPS / Avenza Maps
- **PNG preview** map (matplotlib)
- **HTML map** (interactive Folium / Leaflet — OSM + satellite layers)

Driven by a YAML config so every grid is reproducible and reviewable in a PR — or by a Streamlit browser UI for ad-hoc planning.

## Quick start

```bash
pip install -e .                   # CLI only
pip install -e .[ui]               # add the browser UI

spatial-grid examples/example_grid.yaml -o output
spatial-grid-ui                    # opens the Streamlit app in your browser
```

## Config

```yaml
grid_name: KIRKLAND_LAKE_GRID
crs: EPSG:32617          # UTM Zone 17N (WGS84) — Ontario
centre_easting: 567000
centre_northing: 5340000
anchor: center           # center | sw | se | nw | ne
azimuth_deg: 45          # NE-SW lines (degrees from north, clockwise)
line_spacing: 100        # metres between lines
station_spacing: 25      # metres between stations along a line
num_lines: 21
num_stations: 41
line_naming: chainage    # sequential | chainage | signed
station_naming: chainage
```

`(centre_easting, centre_northing)` is the **reference point** of the grid. With `anchor: center` (default) it's the midpoint, and the survey extends symmetrically. With `anchor: sw|se|nw|ne` it specifies that named corner of the grid (in the unrotated frame, where lines run N-S), and the survey extends away from it.

## Naming conventions

| Scheme       | Lines             | Stations          |
| ------------ | ----------------- | ----------------- |
| `sequential` | L1, L2, L3...     | S1, S2, S3...     |
| `chainage`   | L+100, L0, L-100  | 1+00, 0+00, -1+00 |
| `signed`     | L+100, L0, L-100  | S+100, S0, S-100  |

## CLI

```bash
# Survey grid generator
spatial-grid CONFIG [-o OUTPUT_DIR] [--formats excel,shp,kml,gpx,preview,html]

# Drill program generator (v0.2)
spatial-grid-drill CONFIG [-o OUTPUT_DIR] [--formats excel,shp,csv]
```

Skip formats you don't need: `--formats excel,shp` is fine.

## Drill program (v0.2)

Plan a list of holes — collar position, azimuth, dip, length — and get back collars, 3D drill traces, downhole survey points, and a metres + cost summary.

```yaml
name: KIRKLAND_LAKE_INFILL
crs: EPSG:32617
survey_interval_m: 10        # downhole survey spacing
cost_per_metre: 200          # CAD/m, optional

default_azimuth_deg: 270     # inherited by every hole unless overridden
default_dip_deg: 60          # 0 = horizontal, 90 = vertical down
default_length_m: 200

holes:
  - name: KL-001
    collar_easting: 567050
    collar_northing: 5340075
    collar_rl: 320
  - name: KL-002
    collar_easting: 567150
    collar_northing: 5340150
    collar_rl: 320
    length_m: 250            # override default
```

Outputs:
- **Excel** workbook (Parameters / Summary / Holes / Surveys)
- **Shapefiles** — `*_collars.shp` (2D points), `*_traces.shp` (**3D** linestrings), `*_surveys.shp` (3D points at every survey interval)
- **CSV** of all surveys

The 3D trace shapefile loads directly into Leapfrog Geo, Micromine, ArcGIS Pro 3D scenes, etc.

## Browser UI

```bash
pip install -e .[ui]
spatial-grid-ui
```

A Streamlit app opens in your browser. Configure on the left (lat/lon or UTM, anchor, azimuth, spacings, naming). The map updates live; download any output format from the sidebar.

## Deployment

Streamlit UI is deployable on a k3s cluster behind a Cloudflare Tunnel. See [DEPLOY.md](DEPLOY.md) for the runbook (Dockerfile, k8s manifest, tunnel hostname mapping).

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## License

MIT

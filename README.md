# spatial-grid

Generate local geophysical grids for survey and drill-hole planning.

Given a centre point, azimuth, line spacing, and station spacing, `spatial-grid` produces:

- **Excel** workbook (Parameters, Summary, Lines, Stations sheets)
- **Shapefile** pair (`*_lines.shp`, `*_stations.shp`) with `.prj`
- **KML** for Google Earth review
- **GPX** for handheld GPS / Avenza Maps
- **PNG preview** map

Driven by a YAML config so every grid is reproducible and reviewable in a PR.

## Quick start

```bash
pip install -e .
spatial-grid examples/example_grid.yaml -o output
```

## Config

```yaml
grid_name: KIRKLAND_LAKE_GRID
crs: EPSG:32617          # UTM Zone 17N (WGS84) — Ontario
centre_easting: 567000
centre_northing: 5340000
azimuth_deg: 45          # NE-SW lines (degrees from north, clockwise)
line_spacing: 100        # metres between lines
station_spacing: 25      # metres between stations along a line
num_lines: 21
num_stations: 41
line_naming: chainage    # sequential | chainage | signed
station_naming: chainage
```

The grid is centred on `centre_easting / centre_northing`. With `num_lines=21` and `line_spacing=100`, lines run from `-1000m` to `+1000m` perpendicular to the strike azimuth. Same logic for stations along each line.

## Naming conventions

| Scheme       | Lines             | Stations          |
| ------------ | ----------------- | ----------------- |
| `sequential` | L1, L2, L3...     | S1, S2, S3...     |
| `chainage`   | L+100, L0, L-100  | 1+00, 0+00, -1+00 |
| `signed`     | L+100, L0, L-100  | S+100, S0, S-100  |

## CLI

```bash
spatial-grid CONFIG [-o OUTPUT_DIR] [--formats excel,shp,kml,gpx,preview]
```

Skip formats you don't need: `--formats excel,shp` is fine.

## Roadmap

- v0.2 — drill-hole planning (collar → toe geometry, section lines)
- v0.2 — tenement clipping, exclusion-zone buffers
- v0.3 — DEM drape (true ground length / slope per segment)
- v0.3 — alternative array geometries (dipole-dipole, TEM loops)
- v0.4 — Streamlit UI

## License

MIT

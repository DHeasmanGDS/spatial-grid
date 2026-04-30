"""CLI entrypoint."""
from __future__ import annotations

from pathlib import Path

import click

from .config import load_config
from .core import generate_grid
from .exporters.excel import write_excel
from .exporters.folium_map import write_folium
from .exporters.gpx import write_gpx
from .exporters.kml import write_kml
from .exporters.preview import write_preview
from .exporters.shapefile import write_shapefile


@click.command()
@click.argument("config", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output-dir", "-o", default="output",
              type=click.Path(path_type=Path), show_default=True)
@click.option("--formats", default="excel,shp,kml,gpx,preview,html", show_default=True,
              help="Comma-separated outputs: excel, shp, kml, gpx, preview, html")
def main(config: Path, output_dir: Path, formats: str) -> None:
    """Generate a geophysical grid from a YAML config."""
    spec = load_config(config)
    click.echo(f"Generating grid: {spec.grid_name}")
    grid = generate_grid(spec)
    click.echo(
        f"  {grid.total_stations} stations across {spec.num_lines} lines "
        f"({grid.total_line_km:.2f} line-km)"
    )

    output_dir = Path(output_dir)
    fmts = {f.strip().lower() for f in formats.split(",") if f.strip()}
    base = spec.grid_name.replace(" ", "_")

    if "excel" in fmts:
        p = output_dir / f"{base}.xlsx"
        write_excel(grid, p)
        click.echo(f"  wrote {p}")
    if "shp" in fmts:
        s, l = write_shapefile(grid, output_dir, base)
        click.echo(f"  wrote {s}")
        click.echo(f"  wrote {l}")
    if "kml" in fmts:
        p = output_dir / f"{base}.kml"
        write_kml(grid, p)
        click.echo(f"  wrote {p}")
    if "gpx" in fmts:
        p = output_dir / f"{base}.gpx"
        write_gpx(grid, p)
        click.echo(f"  wrote {p}")
    if "preview" in fmts:
        p = output_dir / f"{base}_preview.png"
        write_preview(grid, p)
        click.echo(f"  wrote {p}")
    if "html" in fmts:
        p = output_dir / f"{base}_map.html"
        write_folium(grid, p)
        click.echo(f"  wrote {p}")


if __name__ == "__main__":
    main()

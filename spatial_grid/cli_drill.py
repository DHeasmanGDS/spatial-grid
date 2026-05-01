"""CLI for drill program generation."""
from __future__ import annotations

from pathlib import Path

import click

from .drill import generate_drill_plan
from .drill_config import load_drill_config
from .exporters.drill_export import write_drill_csv, write_drill_excel, write_drill_shapefiles


@click.command()
@click.argument("config", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output-dir", "-o", default="output",
              type=click.Path(path_type=Path), show_default=True)
@click.option("--formats", default="excel,shp,csv", show_default=True,
              help="Comma-separated outputs: excel, shp, csv")
def main(config: Path, output_dir: Path, formats: str) -> None:
    """Generate a drill plan from a YAML config."""
    spec = load_drill_config(config)
    click.echo(f"Drill program: {spec.name}")
    plan = generate_drill_plan(spec)
    click.echo(f"  {plan.hole_count} holes, {plan.total_metres:.1f} m total")
    if plan.total_cost is not None:
        click.echo(f"  Estimated cost: ${plan.total_cost:,.0f}")

    output_dir = Path(output_dir)
    fmts = {f.strip().lower() for f in formats.split(",") if f.strip()}
    base = spec.name.replace(" ", "_")

    if "excel" in fmts:
        p = output_dir / f"{base}.xlsx"
        write_drill_excel(plan, p)
        click.echo(f"  wrote {p}")
    if "shp" in fmts:
        c, t, s = write_drill_shapefiles(plan, output_dir, base)
        click.echo(f"  wrote {c}")
        click.echo(f"  wrote {t}")
        click.echo(f"  wrote {s}")
    if "csv" in fmts:
        p = output_dir / f"{base}_surveys.csv"
        write_drill_csv(plan, p)
        click.echo(f"  wrote {p}")


if __name__ == "__main__":
    main()

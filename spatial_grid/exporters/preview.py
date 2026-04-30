"""Static map preview using matplotlib."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from ..core import Grid


def write_preview(grid: Grid, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 10))
    grid.lines.plot(ax=ax, color="red", linewidth=0.8, alpha=0.7)
    grid.stations.plot(ax=ax, color="black", markersize=4)

    ax.plot(
        grid.spec.centre_easting,
        grid.spec.centre_northing,
        marker="*",
        markersize=20,
        color="gold",
        markeredgecolor="black",
        zorder=5,
        label="Centre",
    )

    ax.set_aspect("equal")
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    ax.set_title(
        f"{grid.spec.grid_name} — {grid.total_stations} stations, "
        f"{grid.total_line_km:.2f} line-km, az {grid.spec.azimuth_deg}°"
    )
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path

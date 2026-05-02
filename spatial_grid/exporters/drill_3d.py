"""3D drill-plan visualization with Plotly.

Renders each hole as a 3D line from collar to toe, with downhole survey
points along the way. Z axis is RL (elevation in metres). Plotly's
default mouse controls let the user rotate, zoom, and pan in-browser.
"""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from ..drill import DrillPlan


# A small qualitative palette — enough to distinguish ~10 holes at a glance,
# repeats beyond that (which is fine; tooltips disambiguate).
_PALETTE = [
    "#1e3a8a", "#7f1d1d", "#166534", "#9a3412",
    "#581c87", "#0e7490", "#a16207", "#7e22ce",
]


def render_drill_3d(plan: DrillPlan, vertical_exaggeration: float = 1.0) -> go.Figure:
    """Build a Plotly Figure showing the drill plan in 3D.

    Args:
        plan: the DrillPlan to render.
        vertical_exaggeration: multiply the Z axis by this. >1 makes
            shallow dips visually obvious; 1.0 is geometrically truthful.
    """
    fig = go.Figure()

    if len(plan.collars) == 0:
        fig.update_layout(
            title="Add holes to see the 3D preview",
            scene=dict(
                xaxis_title="Easting (m)",
                yaxis_title="Northing (m)",
                zaxis_title="RL (m)",
            ),
            margin=dict(l=0, r=0, t=40, b=0),
        )
        return fig

    # One trace per hole (lines + collar/toe markers) — gives independent
    # legend entries and per-hole hover info.
    for i, (_, row) in enumerate(plan.collars.iterrows()):
        colour = _PALETTE[i % len(_PALETTE)]
        ce, cn, crl = float(row["collar_e"]), float(row["collar_n"]), float(row["collar_rl"])
        te, tn, trl = float(row["toe_e"]), float(row["toe_n"]), float(row["toe_rl"])
        z_collar = crl * vertical_exaggeration
        z_toe = trl * vertical_exaggeration

        fig.add_trace(go.Scatter3d(
            x=[ce, te], y=[cn, tn], z=[z_collar, z_toe],
            mode="lines+markers",
            line=dict(color=colour, width=5),
            marker=dict(
                size=[7, 5],
                color=[colour, colour],
                symbol=["circle", "diamond"],
                line=dict(width=1, color="#0f172a"),
            ),
            name=str(row["hole_name"]),
            hovertemplate=(
                f"<b>{row['hole_name']}</b><br>"
                "E %{x:.1f} N %{y:.1f} RL %{z:.1f}<br>"
                f"Az {row['azimuth']:.0f}° / Dip {row['dip']:.0f}°<br>"
                f"Length {row['length_m']:.0f} m"
                "<extra></extra>"
            ),
        ))

    # All survey points as one trace (lighter, for downhole context)
    fig.add_trace(go.Scatter3d(
        x=plan.surveys["easting"],
        y=plan.surveys["northing"],
        z=plan.surveys["rl"] * vertical_exaggeration,
        mode="markers",
        marker=dict(size=2, color="#475569", opacity=0.55),
        name="Surveys",
        hovertemplate=(
            "%{customdata[0]} @ %{customdata[1]:.1f} m<br>"
            "RL %{z:.1f}"
            "<extra></extra>"
        ),
        customdata=list(zip(plan.surveys["hole_name"], plan.surveys["depth_m"])),
        visible="legendonly",
    ))

    fig.update_layout(
        scene=dict(
            xaxis_title="Easting (m)",
            yaxis_title="Northing (m)",
            zaxis_title=("RL (m)" if vertical_exaggeration == 1.0
                         else f"RL × {vertical_exaggeration:g} (m)"),
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(
            yanchor="top", y=0.99, xanchor="left", x=0.01,
            bgcolor="rgba(255,255,255,0.85)",
        ),
        showlegend=True,
    )
    return fig


def write_drill_3d_html(
    plan: DrillPlan,
    path: str | Path,
    vertical_exaggeration: float = 1.0,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = render_drill_3d(plan, vertical_exaggeration=vertical_exaggeration)
    fig.write_html(str(path), include_plotlyjs="cdn", full_html=True)
    return path

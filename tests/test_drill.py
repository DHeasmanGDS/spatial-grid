"""Tests for drill-hole planning."""
import math
import pytest

from spatial_grid.drill import (
    DrillHoleSpec,
    DrillProgramSpec,
    downhole_position,
    generate_drill_plan,
)


def _hole(**overrides):
    base = dict(
        name="H1",
        collar_easting=1000.0,
        collar_northing=2000.0,
        collar_rl=300.0,
        azimuth_deg=0.0,
        dip_deg=90.0,
        length_m=100.0,
    )
    base.update(overrides)
    return DrillHoleSpec(**base)


def _program(holes=None, **overrides):
    base = dict(name="T", crs="EPSG:32617", holes=holes or [_hole()])
    base.update(overrides)
    return DrillProgramSpec(**base)


# ---- pure math ----

def test_vertical_hole_toe_directly_below_collar():
    h = _hole(azimuth_deg=0, dip_deg=90, length_m=100)
    e, n, rl = downhole_position(h, 100)
    assert e == pytest.approx(1000.0)
    assert n == pytest.approx(2000.0)
    assert rl == pytest.approx(200.0)  # 300 - 100


def test_horizontal_hole_no_rl_change():
    h = _hole(azimuth_deg=90, dip_deg=0, length_m=50)  # due east, horizontal
    e, n, rl = downhole_position(h, 50)
    assert e == pytest.approx(1050.0)
    assert n == pytest.approx(2000.0)
    assert rl == pytest.approx(300.0)


def test_45deg_dip_equal_horizontal_and_vertical_components():
    h = _hole(azimuth_deg=0, dip_deg=45, length_m=math.sqrt(2) * 100)  # north, 45 deg down
    e, n, rl = downhole_position(h, math.sqrt(2) * 100)
    assert e == pytest.approx(1000.0)
    assert n == pytest.approx(2100.0)
    assert rl == pytest.approx(200.0)


def test_azimuth_45_horizontal_goes_NE():
    h = _hole(azimuth_deg=45, dip_deg=0, length_m=math.sqrt(2) * 100)  # NE, horizontal
    e, n, rl = downhole_position(h, math.sqrt(2) * 100)
    assert e == pytest.approx(1100.0)
    assert n == pytest.approx(2100.0)
    assert rl == pytest.approx(300.0)


# ---- validation ----

def test_invalid_dip_rejected():
    with pytest.raises(ValueError):
        _hole(dip_deg=-5)
    with pytest.raises(ValueError):
        _hole(dip_deg=120)


def test_zero_length_rejected():
    with pytest.raises(ValueError):
        _hole(length_m=0)


def test_duplicate_hole_names_rejected():
    h1 = _hole(name="A")
    h2 = _hole(name="A")
    with pytest.raises(ValueError, match="duplicate"):
        _program(holes=[h1, h2])


# ---- plan generation ----

def test_generate_basic():
    plan = generate_drill_plan(_program())
    assert plan.hole_count == 1
    assert plan.total_metres == pytest.approx(100.0)
    assert len(plan.collars) == 1
    assert len(plan.traces) == 1
    # 100m hole, 10m interval -> 11 surveys (0, 10, 20, ..., 100)
    assert len(plan.surveys) == 11


def test_survey_endpoints_aligned_to_collar_and_toe():
    plan = generate_drill_plan(_program(survey_interval_m=10))
    surveys = plan.surveys.sort_values("depth_m")
    first = surveys.iloc[0]
    last = surveys.iloc[-1]
    assert first.depth_m == pytest.approx(0)
    assert first.easting == pytest.approx(1000.0)
    assert first.rl == pytest.approx(300.0)
    assert last.depth_m == pytest.approx(100.0)
    assert last.rl == pytest.approx(200.0)  # vertical hole, 100m down


def test_total_cost():
    plan = generate_drill_plan(_program(cost_per_metre=200))
    assert plan.total_cost == pytest.approx(20000.0)


def test_no_cost_per_metre_returns_none():
    plan = generate_drill_plan(_program())
    assert plan.total_cost is None


def test_3d_trace_geometry():
    plan = generate_drill_plan(_program())
    geom = plan.traces.iloc[0].geometry
    coords = list(geom.coords)
    # First point is collar, last is toe
    assert coords[0] == pytest.approx((1000.0, 2000.0, 300.0))
    assert coords[-1] == pytest.approx((1000.0, 2000.0, 200.0))
    # Geometry should be 3D
    assert geom.has_z


def test_uneven_length_includes_toe():
    """A hole length not divisible by survey interval should still survey to the toe."""
    plan = generate_drill_plan(_program(holes=[_hole(length_m=95)],
                                         survey_interval_m=10))
    depths = sorted(plan.surveys.depth_m.tolist())
    assert depths[-1] == pytest.approx(95.0)

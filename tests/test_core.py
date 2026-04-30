"""Tests for core grid generation."""
import pytest

from spatial_grid.core import GridSpec, generate_grid


def _spec(**overrides):
    base = dict(
        centre_easting=500000,
        centre_northing=5000000,
        azimuth_deg=0,
        line_spacing=100,
        station_spacing=25,
        num_lines=5,
        num_stations=11,
        crs="EPSG:32617",
    )
    base.update(overrides)
    return GridSpec(**base)


def test_grid_counts():
    grid = generate_grid(_spec())
    assert len(grid.stations) == 5 * 11
    assert len(grid.lines) == 5


def test_centre_station_at_centre():
    grid = generate_grid(_spec())
    centre = grid.stations[
        (grid.stations.line_offset_m == 0) & (grid.stations.station_offset_m == 0)
    ]
    assert len(centre) == 1
    assert centre.iloc[0].easting == pytest.approx(500000)
    assert centre.iloc[0].northing == pytest.approx(5000000)


def test_azimuth_zero_lines_run_north():
    grid = generate_grid(_spec(centre_easting=0, centre_northing=0,
                               azimuth_deg=0, num_lines=3, num_stations=3,
                               station_spacing=10))
    centre_line = grid.stations[grid.stations.line_offset_m == 0].sort_values("northing")
    # az=0: lines run N-S, so all stations on a line share an easting
    assert centre_line.easting.tolist() == pytest.approx([0, 0, 0])
    assert centre_line.northing.tolist() == pytest.approx([-10, 0, 10])


def test_azimuth_90_lines_run_east():
    grid = generate_grid(_spec(centre_easting=0, centre_northing=0,
                               azimuth_deg=90, num_lines=3, num_stations=3,
                               station_spacing=10))
    centre_line = grid.stations[grid.stations.line_offset_m == 0].sort_values("easting")
    # az=90: lines run E-W
    assert centre_line.northing.tolist() == pytest.approx([0, 0, 0], abs=1e-9)
    assert centre_line.easting.tolist() == pytest.approx([-10, 0, 10])


def test_total_line_km():
    grid = generate_grid(_spec(num_lines=10, num_stations=41,
                               station_spacing=25, line_spacing=100))
    # 41 stations -> 40 segments × 25m = 1000m per line × 10 lines = 10 km
    assert grid.total_line_km == pytest.approx(10.0)


def test_invalid_spec_rejected():
    with pytest.raises(ValueError):
        _spec(num_stations=1)
    with pytest.raises(ValueError):
        _spec(line_spacing=0)


def test_chainage_naming():
    grid = generate_grid(_spec(num_lines=3, num_stations=3,
                               line_spacing=100, station_spacing=100))
    line_ids = sorted(grid.lines.line_id.tolist())
    assert line_ids == ["L+100", "L-100", "L0"]
    centre_line_stations = grid.stations[grid.stations.line_id == "L0"].station_name.tolist()
    assert "0+00" in centre_line_stations

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


def test_invalid_anchor_rejected():
    with pytest.raises(ValueError):
        _spec(anchor="northwest")


def test_anchor_sw_extends_ne():
    """SW anchor: grid extends north and east from the reference point."""
    grid = generate_grid(_spec(centre_easting=0, centre_northing=0,
                               azimuth_deg=0, num_lines=3, num_stations=3,
                               line_spacing=100, station_spacing=100,
                               anchor="sw"))
    # Reference point should be the minimum easting and minimum northing
    assert grid.stations.easting.min() == pytest.approx(0)
    assert grid.stations.northing.min() == pytest.approx(0)
    assert grid.stations.easting.max() == pytest.approx(200)
    assert grid.stations.northing.max() == pytest.approx(200)


def test_anchor_nw_extends_se():
    """NW anchor: grid extends south and east from the reference point."""
    grid = generate_grid(_spec(centre_easting=0, centre_northing=0,
                               azimuth_deg=0, num_lines=3, num_stations=3,
                               line_spacing=100, station_spacing=100,
                               anchor="nw"))
    assert grid.stations.easting.min() == pytest.approx(0)
    assert grid.stations.northing.max() == pytest.approx(0)
    assert grid.stations.easting.max() == pytest.approx(200)
    assert grid.stations.northing.min() == pytest.approx(-200)


def test_grid_sized_by_extent():
    """Providing grid_width_m / line_length_m derives counts from spacing."""
    grid = generate_grid(GridSpec(
        centre_easting=0, centre_northing=0, azimuth_deg=0,
        line_spacing=100, station_spacing=25,
        grid_width_m=2000, line_length_m=1000,
        crs="EPSG:32617",
    ))
    # 2000m / 100m + 1 = 21 lines, 1000m / 25m + 1 = 41 stations
    assert len(grid.lines) == 21
    assert len(grid.stations) == 21 * 41


def test_extent_and_count_both_rejected():
    with pytest.raises(ValueError, match="not both"):
        GridSpec(
            centre_easting=0, centre_northing=0, azimuth_deg=0,
            line_spacing=100, station_spacing=25,
            num_lines=21, grid_width_m=2000,  # both
            num_stations=41,
            crs="EPSG:32617",
        )


def test_neither_extent_nor_count_rejected():
    with pytest.raises(ValueError, match="must provide"):
        GridSpec(
            centre_easting=0, centre_northing=0, azimuth_deg=0,
            line_spacing=100, station_spacing=25,
            num_stations=41,  # missing line count/extent
            crs="EPSG:32617",
        )


def test_extent_mixed_with_count():
    """User can specify counts on one axis and extent on the other."""
    grid = generate_grid(GridSpec(
        centre_easting=0, centre_northing=0, azimuth_deg=0,
        line_spacing=100, station_spacing=25,
        num_lines=11, line_length_m=500,
        crs="EPSG:32617",
    ))
    # 500/25 + 1 = 21 stations, 11 lines as given
    assert len(grid.lines) == 11
    assert len(grid.stations) == 11 * 21


def test_anchor_corner_uses_unsigned_chainage():
    """Corner-anchored grids drop the +/- prefix on chainage labels."""
    grid = generate_grid(_spec(num_lines=3, num_stations=3,
                               line_spacing=100, station_spacing=100,
                               anchor="sw"))
    line_ids = set(grid.lines.line_id.tolist())
    assert line_ids == {"L0", "L100", "L200"}
    station_names = set(grid.stations.station_name.tolist())
    assert station_names == {"0+00", "1+00", "2+00"}

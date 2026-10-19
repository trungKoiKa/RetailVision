import pytest

from retailvision.analytics.geometry import (
    point_in_polygon,
    segments_intersect,
    signed_distance,
    to_pixels,
)

VERTICAL = ((50.0, 0.0), (50.0, 100.0))


def test_to_pixels_scales_normalized_points():
    assert to_pixels([(0.5, 0.25), (1.0, 1.0)], 200, 100) == [(100.0, 25.0), (200.0, 100.0)]


def test_signed_distance_opposite_sides_have_opposite_signs():
    left = signed_distance((40.0, 50.0), *VERTICAL)
    right = signed_distance((60.0, 50.0), *VERTICAL)
    assert left * right < 0
    assert abs(left) == pytest.approx(10.0)


def test_signed_distance_on_line_is_zero():
    assert signed_distance((50.0, 70.0), *VERTICAL) == pytest.approx(0.0)


def test_signed_distance_rejects_degenerate_line():
    with pytest.raises(ValueError):
        signed_distance((1.0, 1.0), (5.0, 5.0), (5.0, 5.0))


def test_segments_intersect_when_path_crosses_line_segment():
    assert segments_intersect((40.0, 50.0), (60.0, 50.0), *VERTICAL)


def test_segments_do_not_intersect_when_path_passes_beyond_endpoint():
    # đi ngang phía trên đầu mút A của vạch (y nhỏ hơn A.y)
    assert not segments_intersect((40.0, 10.0), (60.0, 10.0), (50.0, 20.0), (50.0, 80.0))


def test_point_in_polygon_inside_and_outside():
    square = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
    assert point_in_polygon((50.0, 50.0), square)
    assert not point_in_polygon((150.0, 50.0), square)
    assert not point_in_polygon((50.0, -5.0), square)

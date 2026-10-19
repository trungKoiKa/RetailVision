import numpy as np

from retailvision.core.types import Track
from retailvision.presentation.overlay import draw


def test_draw_keeps_shape_and_marks_pixels():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    tracks = [Track(7, (50.0, 80.0), (40.0, 40.0, 60.0, 80.0), 0.9)]
    out = draw(image, tracks, ((50.0, 0.0), (50.0, 99.0)), [(60.0, 20.0), (95.0, 20.0), (95.0, 90.0)], "t=0.0s")
    assert out.shape == image.shape
    assert out.any()  # có nét vẽ
    assert not image.any()  # ảnh gốc không bị sửa

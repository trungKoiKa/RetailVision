import cv2
import numpy as np
import pytest

from retailvision.pipeline.capture import VideoFileSource


def make_clip(path, frames=10, fps=10.0, size=(64, 48)):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, size)
    if not writer.isOpened():
        pytest.skip("OpenCV không ghi được video MJPG trên máy này")
    for i in range(frames):
        writer.write(np.full((size[1], size[0], 3), i * 10, dtype=np.uint8))
    writer.release()


def test_video_source_reads_all_frames_with_video_timestamps(tmp_path):
    clip = tmp_path / "clip.avi"
    make_clip(clip, frames=10, fps=10.0)
    src = VideoFileSource(clip)
    assert src.frame_size == (64, 48)
    got = []
    while (f := src.read()) is not None:
        got.append(f)
    src.close()
    assert len(got) == 10
    assert got[0].ts == pytest.approx(0.0, abs=1e-3)
    assert got[-1].ts == pytest.approx(0.9, abs=0.05)


def test_missing_video_raises(tmp_path):
    with pytest.raises(RuntimeError):
        VideoFileSource(tmp_path / "nope.mp4")

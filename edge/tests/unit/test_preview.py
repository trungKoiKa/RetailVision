import threading
import time
import urllib.error
import urllib.request

import numpy as np
import pytest

from retailvision.presentation.preview import PreviewServer


@pytest.fixture
def server():
    s = PreviewServer("127.0.0.1", 0).start()
    yield s
    s.close()


def _image():
    return np.full((48, 64, 3), 128, dtype=np.uint8)


def test_no_viewers_means_nothing_to_encode(server):
    assert not server.has_viewers


def test_snapshot_waits_for_a_fresh_frame_and_marks_a_viewer(server):
    got = {}

    def fetch():
        with urllib.request.urlopen(f"http://127.0.0.1:{server.port}/snapshot.jpg", timeout=5) as r:
            got["type"] = r.headers["Content-Type"]
            got["body"] = r.read()

    t = threading.Thread(target=fetch)
    t.start()
    deadline = time.monotonic() + 3
    while not server.has_viewers and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.has_viewers  # vòng xử lý sẽ biết cần mã hoá
    server.publish(_image())
    t.join(5)
    assert got["type"] == "image/jpeg"
    assert got["body"][:2] == b"\xff\xd8"
    assert not server.has_viewers


def test_snapshot_without_frames_is_503(server, monkeypatch):
    monkeypatch.setattr("retailvision.presentation.preview.time.monotonic", _fast_clock())
    with pytest.raises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(f"http://127.0.0.1:{server.port}/snapshot.jpg", timeout=5)
    assert err.value.code == 503


def _fast_clock():
    t = {"v": 0.0}

    def clock():
        t["v"] += 10.0
        return t["v"]

    return clock


def test_stream_delivers_multipart_jpeg_and_counts_viewer(server):
    req = urllib.request.urlopen(f"http://127.0.0.1:{server.port}/stream.mjpg", timeout=5)
    assert "multipart/x-mixed-replace" in req.headers["Content-Type"]
    deadline = time.monotonic() + 3
    while not server.has_viewers and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.has_viewers
    server.publish(_image())
    chunk = req.read(200)
    assert b"--rvframe" in chunk and b"image/jpeg" in chunk
    req.close()


def test_index_page_and_unknown_path(server):
    with urllib.request.urlopen(f"http://127.0.0.1:{server.port}/", timeout=5) as r:
        assert b"stream.mjpg" in r.read()
    with pytest.raises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(f"http://127.0.0.1:{server.port}/x", timeout=5)
    assert err.value.code == 404


def test_closing_stops_serving():
    s = PreviewServer("127.0.0.1", 0).start()
    port = s.port
    s.close()
    with pytest.raises(urllib.error.URLError):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)


def test_observer_encodes_only_when_someone_watches(server):
    from types import SimpleNamespace

    from retailvision.app import _preview_observer

    pl = SimpleNamespace(
        in_count=1, out_count=0, last_queue_count=2, line_px=((0, 0), (10, 10)),
        polygon_px=[(0, 0), (30, 0), (30, 30)], alert=SimpleNamespace(state=SimpleNamespace(value="NORMAL")),
    )
    frame = SimpleNamespace(image=_image())
    obs = _preview_observer(server)
    obs(frame, [], pl)
    assert server._jpeg is None  # không ai xem: không mã hoá
    with server._viewer():
        obs(frame, [], pl)
    assert server._jpeg is not None

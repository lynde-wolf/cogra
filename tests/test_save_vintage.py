import matplotlib.pyplot as plt
import pytest
from PIL import Image

import cogra
from cogra import style


def _fig():
    cogra.use()
    fig, ax = plt.subplots(figsize=(2, 1.5))
    ax.plot([0, 1, 2], [1, 3, 2])
    ax.set_title("wear")
    return fig


@pytest.mark.parametrize("look,mode", [("scan", "1"), ("xerox", "L"), ("aged", "RGB")])
def test_writes_each_look(tmp_path, look, mode):
    out = cogra.save_vintage(_fig(), tmp_path / "f.png", look=look, dpi=300, scan_dpi=150)
    im = Image.open(out)
    assert im.mode == mode
    assert im.info["dpi"][0] == pytest.approx(
        150 if look == "scan" else 300, abs=0.1
    )  # PNG stores pixels per metre


def test_scan_size_follows_scan_dpi(tmp_path):
    fig = _fig()
    clean = style.render_gray(fig, 300)
    im = Image.open(cogra.save_vintage(fig, tmp_path / "s.png", dpi=300, scan_dpi=100))
    assert im.size == (round(clean.shape[1] / 3), round(clean.shape[0] / 3))


def test_cache_hit_skips_wear(tmp_path, monkeypatch):
    fig = _fig()
    a = cogra.save_vintage(fig, tmp_path / "a.png", dpi=200, scan_dpi=100)
    monkeypatch.setattr(style.wear, "apply", lambda *a, **k: pytest.fail("cache miss"))
    b = cogra.save_vintage(fig, tmp_path / "b.png", dpi=200, scan_dpi=100)
    assert a.read_bytes() == b.read_bytes()


def test_cache_key_covers_settings_and_content(tmp_path):
    fig = _fig()
    cogra.save_vintage(fig, tmp_path / "a.png", dpi=200, scan_dpi=100)
    cogra.save_vintage(fig, tmp_path / "b.png", dpi=200, scan_dpi=100, strength=1.5)
    fig.axes[0].set_title("changed")
    cogra.save_vintage(fig, tmp_path / "c.png", dpi=200, scan_dpi=100)
    assert len(list(cogra.cache_dir().iterdir())) == 3


def test_cache_off_and_clear(tmp_path):
    cogra.save_vintage(_fig(), tmp_path / "a.png", dpi=200, scan_dpi=100, cache=False)
    assert not cogra.cache_dir().exists()
    cogra.save_vintage(_fig(), tmp_path / "a.png", dpi=200, scan_dpi=100)
    assert cogra.cache_dir().exists()
    cogra.clear_cache()
    assert not cogra.cache_dir().exists()


def test_bad_look(tmp_path):
    with pytest.raises(ValueError):
        cogra.save_vintage(_fig(), tmp_path / "x.png", look="sepia", dpi=100)

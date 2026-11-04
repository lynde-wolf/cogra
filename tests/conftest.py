import importlib.util
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Default rcParams, a private wear cache, and no figures left open, so
    tests cannot leak style into each other."""
    matplotlib.rcdefaults()
    monkeypatch.setenv("COGRA_CACHE", str(tmp_path / "cache"))
    yield
    plt.close("all")


@pytest.fixture
def rng():
    return np.random.default_rng(0)


def text_page(
    w=900,
    h=500,
    size=34,
    lines=("Mid-century journal page", "Stop-signal reaction time", "Fig. 1. 0123456789"),
):
    """A small grayscale raster with real glyphs, for wear tests."""
    from cogra.style import HERE

    img = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(HERE / "fonts" / "texgyreschola-regular.otf"), size)
    for i, t in enumerate(lines):
        d.text((40, 40 + i * (size + 30)), t, fill=0, font=font)
    d.rectangle((40, h - 90, w - 40, h - 86), fill=0)  # a rule
    return np.asarray(img)


@pytest.fixture
def page():
    return text_page()


def load_example(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "examples" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

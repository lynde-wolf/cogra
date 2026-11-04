import numpy as np
import pytest

from cogra import wear
from cogra.wear import _Noise

# ---------- noise fields ----------


@pytest.mark.parametrize("sigma", [0.8, 1.6, 2.9, 3.6, 14.0, 120.0])
def test_noise_window_matches_full_field(sigma):
    n = _Noise(5, (600, 700))
    full = n.full("f", sigma)
    win = n.field("f", sigma, 123, 456, 200, 650)
    np.testing.assert_allclose(win, full[123:456, 200:650], rtol=1e-5, atol=1e-5)


@pytest.mark.parametrize("sigma", [0.8, 1.6, 3.6, 14.0])
def test_noise_is_unit_variance(sigma):
    f = _Noise(1, (1200, 1200)).full("v", sigma)
    assert f.dtype == np.float32
    assert abs(f.mean()) < 0.1 and f.std() == pytest.approx(1.0, abs=0.12)


def test_noise_fields_are_independent_and_seeded():
    a = _Noise(1, (300, 300)).full("a", 1.5)
    b = _Noise(1, (300, 300)).full("b", 1.5)
    a2 = _Noise(1, (300, 300)).full("a", 1.5)
    c = _Noise(2, (300, 300)).full("a", 1.5)
    assert np.array_equal(a, a2)
    assert abs(np.corrcoef(a.ravel(), b.ravel())[0, 1]) < 0.05
    assert abs(np.corrcoef(a.ravel(), c.ravel())[0, 1]) < 0.05


def test_noise_window_beyond_image_edge():
    n = _Noise(3, (100, 100))
    assert n.field("e", 1.2, -30, 20, 90, 140).shape == (50, 50)


# ---------- looks ----------


def test_scan_is_bilevel_at_scan_resolution(page):
    bw = wear.scan(page, dpi=300, scan_dpi=150, specks=False)
    assert bw.dtype == bool and bw.shape == (page.shape[0] // 2, page.shape[1] // 2)
    ink = 1 - bw.mean()
    clean = (page < 128).mean()
    assert 0.5 * clean < ink < 2.0 * clean


@pytest.mark.parametrize("look", ["scan", "xerox", "aged"])
def test_result_does_not_depend_on_tile_size(page, look):
    f = getattr(wear, look)
    a = f(page, dpi=300, tile=96)
    b = f(page, dpi=300, tile=512)
    # Exact up to float32 rounding: numpy's SIMD exp can differ by an ulp
    # between the vector body and the tail of an array, so a handful of
    # pixels may land one grey level apart.
    assert np.abs(a.astype(int) - b).max() <= 1
    assert (a != b).mean() < 1e-4


@pytest.mark.parametrize("look", ["scan", "xerox", "aged"])
def test_deterministic_per_seed(page, look):
    f = getattr(wear, look)
    a, b, c = f(page, dpi=300, seed=1), f(page, dpi=300, seed=1), f(page, dpi=300, seed=2)
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_blank_page_stays_blank():
    blank = np.full((400, 500), 255, np.uint8)
    assert wear.scan(blank, dpi=300, specks=False).all()
    x = wear.xerox(blank, dpi=300, specks=False)
    assert x.min() > 128  # paper texture but no ink


def test_ink_outside_the_page_is_not_lost():
    """Strokes touching the image border must still be worn, not dropped."""
    img = np.full((300, 300), 255, np.uint8)
    img[:, :6] = 0
    img[-6:, :] = 0
    bw = wear.scan(img, dpi=300, scan_dpi=300, specks=False)
    assert (~bw[:, :6]).mean() > 0.8 and (~bw[-6:, :]).mean() > 0.8


def test_strength_zero_keeps_shapes(page):
    bw = wear.scan(page, dpi=300, scan_dpi=300, strength=0, weight=0, specks=False)
    clean = page < 128
    assert (bw == ~clean).mean() > 0.97


def test_specks_add_ink(page):
    with_s = wear.scan(page, dpi=300, strength=2, specks=True)
    without = wear.scan(page, dpi=300, strength=2, specks=False)
    assert (~with_s).sum() > (~without).sum()


def test_xerox_and_aged_formats(page):
    x = wear.xerox(page, dpi=300, generations=3, skew=0.4)
    a = wear.aged(page, dpi=300, paper="white")
    assert x.shape == page.shape and x.dtype == np.uint8
    assert a.shape == (*page.shape, 3) and a.dtype == np.uint8
    paper = a[page == 255]
    assert paper[:, 0].mean() > paper[:, 2].mean()  # toned, yellowish stock


def test_more_generations_darken_copy(page):
    one = wear.xerox(page, dpi=300, generations=1, specks=False, fade=0)
    four = wear.xerox(page, dpi=300, generations=4, specks=False, fade=0)
    assert (four < 128).sum() > (one < 128).sum()


def test_apply_dispatch(page):
    img, dpi = wear.apply(page, "scan", dpi=300, scan_dpi=150)
    assert img.mode == "1" and dpi == 150
    assert wear.apply(page, "xerox", dpi=300)[0].mode == "L"
    assert wear.apply(page, "aged", dpi=300)[0].mode == "RGB"
    with pytest.raises(ValueError):
        wear.apply(page, "sepia")


def test_matches_legacy_look(page):
    """Grain changed in 0.1 (tiled, float32 noise); the amount of ink should not."""
    from _legacy import degrade_scan

    up = np.kron(page, np.ones((2, 2), np.uint8))  # 600 dpi
    old = degrade_scan(up, np.random.default_rng(0), 600, 1.0, 1.0, 200, 0.0, False)
    new = wear.scan(up, dpi=600, scan_dpi=200, specks=False)
    assert old.shape == new.shape
    assert (~new).mean() == pytest.approx((~old).mean(), rel=0.08)


def test_dust_specks_are_irregular_not_square():
    """Specks are soft-edged blobs of varying shape; in the scan look they
    come out as ragged 1-bit flecks, not the square stamps of old."""
    rng = np.random.default_rng(0)
    b = wear._blob(rng, 6.0)
    assert ((b > 0) & (b < 1)).any()  # a soft edge
    assert b[0, 0] == 0 and b[-1, -1] == 0  # corners clear: round, not square
    shapes = {tuple((wear._blob(np.random.default_rng(i), 6.0) > 0.5).sum(axis=0)) for i in range(5)}
    assert len(shapes) == 5  # each speck its own shape

    blank = np.full((1200, 1200), 255, np.uint8)
    bw = wear.scan(blank, dpi=600, scan_dpi=200, strength=1.0, specks=True, seed=3)
    from scipy.ndimage import label

    lab, n = label(~bw)
    assert n > 5
    sizes = np.bincount(lab.ravel())[1:]
    boxes = [np.argwhere(lab == i + 1) for i in range(n)]
    filled = [s / ((np.ptp(p[:, 0]) + 1) * (np.ptp(p[:, 1]) + 1)) for s, p in zip(sizes, boxes)]
    assert len(set(sizes.tolist())) > 2  # varied sizes
    assert min(filled) < 1.0  # at least some are not solid rectangles

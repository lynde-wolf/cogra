"""Property-based tests for the p-value labels, stars() and format_p()."""

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cogra import format_p, stars

p_values = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


@settings(database=None)
@given(p_values)
def test_stars_follow_the_thresholds(p):
    expected = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    assert stars(p) == expected


@settings(database=None)
@given(p_values, p_values)
def test_smaller_p_never_gets_fewer_stars(p, q):
    lo, hi = sorted((p, q))
    assert len(stars(lo)) >= len(stars(hi))


@settings(database=None)
@given(p_values)
def test_format_p_is_apa_style(p):
    label = format_p(p)
    assert label.startswith("$p$ ")
    if p < 0.001:
        assert label == "$p$ < .001"
    else:
        number = label.removeprefix("$p$ = ")
        assert not number.startswith("0")  # no leading zero
        assert math.isclose(float(number), p, abs_tol=0.0005)


@pytest.mark.parametrize("bad", [-0.01, 1.0001, float("nan"), float("inf")])
def test_impossible_p_raises(bad):
    with pytest.raises(ValueError, match="between 0 and 1"):
        stars(bad)
    with pytest.raises(ValueError, match="between 0 and 1"):
        format_p(bad)

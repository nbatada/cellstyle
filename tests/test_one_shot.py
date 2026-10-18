import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from cellstyle.plots import quantitative_scatter, replicate_distribution
from cellstyle.styling import style_plot
from cellstyle.theme import set_theme, theme_context
from cellstyle import theme as theme_module


def test_helpers_style_first_call_without_global_leak():
    before = mpl.rcParams.copy()
    x = pd.Series([1, 2], name="Dose")
    y = pd.Series([3, 4], name="Response")
    ax = quantitative_scatter(x, y)
    assert ax.get_xlabel() == "Dose" and ax.get_ylabel() == "Response"
    assert np.allclose(ax.figure.get_size_inches() * 25.4, [90, 48])
    assert ax.xaxis.label.get_fontsize() == 8
    plt.close(ax.figure)
    data = pd.DataFrame({"group": ["a", "a", "b"], "value": [1, 2, 3]})
    ax = replicate_distribution(data, "group", "value")
    assert np.allclose(ax.figure.get_size_inches() * 25.4, [90, 60])
    assert ax.xaxis.label.get_fontsize() == 8
    assert mpl.colors.to_hex(ax.collections[0].get_facecolors()[0]).upper() == "#1764AB"
    plt.close(ax.figure)
    assert mpl.rcParams == before


def test_helpers_preserve_explicit_theme_and_restore_nested_context():
    data = pd.DataFrame({"group": ["a", "b"], "value": [1, 2]})
    with theme_context("presentation"):
        for helper in (
            lambda: quantitative_scatter([1, 2], [3, 4]),
            lambda: replicate_distribution(data, "group", "value"),
        ):
            ax = helper()
            assert ax.xaxis.label.get_fontsize() == 12
            assert tuple(ax.figure.get_size_inches()) == tuple(plt.rcParams["figure.figsize"])
            plt.close(ax.figure)
        with theme_context("manuscript"):
            ax = quantitative_scatter([1], [2])
            assert ax.xaxis.label.get_fontsize() == 8
            plt.close(ax.figure)
        ax = quantitative_scatter([1], [2])
        assert ax.xaxis.label.get_fontsize() == 12
        plt.close(ax.figure)

    before = mpl.rcParams.copy()
    try:
        set_theme("manuscript")
        set_theme("presentation")
        ax = quantitative_scatter([1], [2])
        assert ax.xaxis.label.get_fontsize() == 12
        plt.close(ax.figure)
    finally:
        mpl.rcParams.update(before)
        theme_module._active_mode.set(None)


def test_caller_axes_and_encodings_stay_owned():
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.set_xlim(-10, 10)
    quantitative_scatter([1], [2], ax=ax, color="red", alpha=.3, size=42)
    assert tuple(fig.get_size_inches()) == (4, 3)
    assert ax.get_xlim() == (-10, 10)
    assert ax.collections[0].get_sizes()[0] == 42
    ax.set_xlabel("Caller x"); ax.set_ylabel("Caller y")
    replicate_distribution(pd.DataFrame({"g":["A","B"],"v":[2,3]}), "g", "v", ax=ax)
    assert ax.get_xlabel() == "Caller x" and ax.get_ylabel() == "Caller y"
    assert ax.xaxis.label.get_fontsize() != 8
    with pytest.raises(ValueError, match="size_mm"):
        style_plot(fig, size_mm=True)
    with pytest.raises(ValueError, match="size_mm"):
        style_plot(fig, size_mm=(float("nan"), 60))
    plt.close(fig)
    fig, ax = plt.subplots()
    ax.yaxis.tick_right()
    ax.spines["right"].set_visible(True)
    style_plot(ax)
    assert ax.spines["right"].get_visible()
    plt.close(fig)


def test_native_boxplot_one_call_export_and_no_overwrite(tmp_path):
    fig, ax = plt.subplots()
    ax.boxplot([[1, 2, 3], [2, 3, 4]])
    ax.set_title("Measured values")
    ax.set_title("Side title", loc="left")
    before_limits = ax.get_ylim()
    original_lines = [line.get_color() for line in ax.lines]
    out = tmp_path / "boxplot.pdf"
    with mpl.rc_context({"savefig.bbox": "tight"}):
        assert style_plot(ax, output=out) is ax
    assert out.exists() and out.stat().st_size > 0
    from pypdf import PdfReader
    page = PdfReader(str(out)).pages[0]
    assert abs(float(page.mediabox.width) - 90 / 25.4 * 72) < 1
    assert abs(float(page.mediabox.height) - 60 / 25.4 * 72) < 1
    assert np.allclose(fig.get_size_inches() * 25.4, [90, 60])
    assert ax.title.get_fontsize() == 9 and ax._left_title.get_fontsize() == 9
    assert ax.get_ylim() == before_limits
    assert [line.get_color() for line in ax.lines] == original_lines
    with pytest.raises(FileExistsError):
        style_plot(fig, output=out)
    link = tmp_path / "alias.pdf"
    link.symlink_to(tmp_path / "missing.pdf")
    with pytest.raises(FileExistsError):
        style_plot(fig, output=link)
    plt.close(fig)

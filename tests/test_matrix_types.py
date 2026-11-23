import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from cellstyle.matrices import dotplot, heatmap


@pytest.fixture
def summaries():
    means = pd.DataFrame([[0., 2.], [np.nan, 1.]], index=["B", "A"], columns=["G2", "G1"])
    fractions = pd.DataFrame([[0., .5], [.25, np.nan]], index=["B", "A"], columns=["G2", "G1"])
    return means, fractions


def test_dotplot_preserves_order_zero_and_missing(summaries):
    means, fractions = summaries
    means_before, fractions_before = means.copy(deep=True), fractions.copy(deep=True)
    ax = dotplot(means, fractions, colour_label="Mean log1p expression",
                 size_label="Cells with expression > 0 (%)", row_order=["A", "B"],
                 column_order=["G1", "G2"])
    try:
        assert [tick.get_text() for tick in ax.get_yticklabels()] == ["A", "B"]
        assert [tick.get_text() for tick in ax.get_xticklabels()] == ["G1", "G2"]
        dots = ax.collections[0]
        assert len(dots.get_offsets()) == 2  # two finite paired summaries; zero is retained
        assert 0 in dots.get_sizes()
        assert len(ax.collections[1].get_offsets()) == 2  # unavailable, visually distinct from zero
        assert np.allclose(ax.figure.get_size_inches() * 25.4, [135, 80])
        pd.testing.assert_frame_equal(means, means_before)
        pd.testing.assert_frame_equal(fractions, fractions_before)
    finally:
        plt.close(ax.figure)


def test_dotplot_rejects_misaligned_or_invalid_fraction(summaries):
    means, fractions = summaries
    with pytest.raises(ValueError, match="identical labels"):
        dotplot(means, fractions.rename(index={"A": "other"}), colour_label="x", size_label="y")
    with pytest.raises(ValueError, match="between 0 and 1"):
        dotplot(means.fillna(1), fractions.fillna(2), colour_label="x", size_label="y")
    with pytest.raises(ValueError, match="nonnegative"):
        dotplot(means.fillna(-1), fractions.fillna(.5), colour_label="x", size_label="y")
    with pytest.raises(ValueError, match="non-empty"):
        dotplot(means.fillna(1), fractions.fillna(.5), colour_label="", size_label="y")
    with pytest.raises(ValueError, match="infinite"):
        dotplot(means.fillna(1), fractions.replace(.5, np.inf), colour_label="x", size_label="y")


def test_heatmap_keeps_zero_missing_and_uses_explicit_scale(summaries):
    means, _ = summaries
    ax = heatmap(means, scale_label="Mean log1p expression", row_order=["A", "B"],
                 column_order=["G1", "G2"])
    try:
        image = ax.images[0]
        rendered = image.get_array()
        assert np.ma.is_masked(rendered[0, 1])  # A/G2 is unavailable; B/G2 remains finite zero
        assert image.cmap.name == "Blues"
        assert [tick.get_text() for tick in ax.get_yticklabels()] == ["A", "B"]
    finally:
        plt.close(ax.figure)


def test_heatmap_requires_explicit_scale_label(summaries):
    means, _ = summaries
    with pytest.raises(TypeError):
        heatmap(means)


def test_heatmap_constant_marker_midpoint_clipping_and_one_call_pdf(tmp_path):
    constant = pd.DataFrame([[0., 0.], [0., 0.]], index=["A", "B"], columns=["G1", "G2"])
    ax = heatmap(constant, scale_label="Mean log1p expression")
    try:
        assert ax.images[0].cmap.name == "Blues"
        assert ax.images[0].norm.vmin == 0 and ax.images[0].norm.vmax == 1
    finally:
        plt.close(ax.figure)
    signed = pd.DataFrame([[-2., 1.]], index=["A"], columns=["G1", "G2"])
    ax = heatmap(signed, scale="marker", scale_label="Centered marker score")
    try:
        assert ax.images[0].norm.vmin == -2 and ax.images[0].norm.vmax == 2
        assert ax.images[0].cmap.name == "cellstyle_marker"
    finally:
        plt.close(ax.figure)
    small = pd.DataFrame([[-.2, .1]], index=["A"], columns=["G1", "G2"])
    ax = heatmap(small, scale="marker", scale_label="Centered marker score")
    try:
        assert ax.images[0].norm.vmin == -.2 and ax.images[0].norm.vmax == .2
    finally:
        plt.close(ax.figure)
    positive = pd.DataFrame([[1., 2.]], index=["A"], columns=["G1", "G2"])
    ax = heatmap(positive, scale_label="Mean log1p expression")
    try:
        assert ax.images[0].norm.vmin == 0
    finally:
        plt.close(ax.figure)
    with pytest.raises(ValueError, match="midpoint"):
        heatmap(signed, scale="marker", scale_label="x", vmin=-1, vmax=2)
    with pytest.raises(ValueError, match="clip"):
        heatmap(pd.DataFrame([[1., 2.]], index=["A"], columns=["G1", "G2"]), scale_label="x", vmin=0, vmax=1)
    with pytest.raises(ValueError, match="infinite"):
        heatmap(pd.DataFrame([[np.inf, 1.]], index=["A"], columns=["G1", "G2"]), scale_label="x")
    output = tmp_path / "matrix.pdf"
    ax = heatmap(pd.DataFrame([[1., 2.]], index=["A"], columns=["G1", "G2"]),
                 scale_label="Mean log1p expression", output=output)
    try:
        assert output.exists() and (tmp_path / "matrix.pdf.cellstyle.json").exists()
    finally:
        plt.close(ax.figure)


@pytest.mark.parametrize("labels", [["", "B"], ["A", None]])
def test_tables_reject_visually_ambiguous_labels(labels):
    matrix = pd.DataFrame([[1., 2.], [3., 4.]], index=labels, columns=["G1", "G2"])
    with pytest.raises(ValueError, match="labels"):
        heatmap(matrix, scale_label="x")


def test_heatmap_rejects_all_missing_matrix():
    with pytest.raises(ValueError, match="at least one finite"):
        heatmap(pd.DataFrame([[np.nan]], index=["A"], columns=["G1"]), scale_label="x")


def test_numeric_labels_and_fraction_guides_are_supported():
    means = pd.DataFrame([[1., 2.]], index=[0], columns=[1, 2])
    fractions = pd.DataFrame([[.25, .5]], index=[0], columns=[1, 2])
    ax = dotplot(means, fractions, colour_label="Mean", size_label="Fraction positive", size_guide_unit="fraction")
    try:
        assert [tick.get_text() for tick in ax.get_yticklabels()] == ["0"]
        text = {item.get_text() for axis in ax.figure.axes for item in axis.texts}
        assert text >= {"0.25", "0.5", "1"}
    finally:
        plt.close(ax.figure)
    ambiguous = pd.DataFrame([[1., 2.]], index=["A"], columns=[1, "1"])
    with pytest.raises(ValueError, match="visibly unique"):
        heatmap(ambiguous, scale_label="x")


def test_external_axes_keep_caller_canvas_size():
    means = pd.DataFrame([[1., 2.]], index=["A"], columns=["G1", "G2"])
    fractions = pd.DataFrame([[.25, .5]], index=["A"], columns=["G1", "G2"])
    fig, ax = plt.subplots(figsize=(4, 3), layout="constrained")
    dotplot(means, fractions, colour_label="Mean", size_label="Fraction", ax=ax)
    assert tuple(fig.get_size_inches()) == (4, 3)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(4, 3), layout="constrained")
    heatmap(means, scale_label="Mean", ax=ax)
    assert tuple(fig.get_size_inches()) == (4, 3)
    plt.close(fig)

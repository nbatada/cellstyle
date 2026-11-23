import json
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_svg import FigureCanvasSVG
import numpy as np
import pytest

from cellstyle.delivery import save_for_paper_and_slides
from cellstyle.export import measure_panel


def native_figure():
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot([0, 1, 2], [1, 3, 2])
    ax.set(xlabel="Synthetic x", ylabel="Synthetic y", title="Native figure")
    fig.tight_layout()
    return fig, ax


def test_delivery_preserves_figure_and_writes_measured_paper_slide_bundle(tmp_path):
    pytest.importorskip("pypdf")
    fig, ax = native_figure()
    before_size = fig.get_size_inches().copy()
    before_lines = len(ax.lines)
    receipt = save_for_paper_and_slides(fig, tmp_path / "bundle", min_slide_text_pt=5)
    bundle = tmp_path / "bundle"
    assert receipt["status"] == "PASS"
    assert (bundle / "receipt.json").exists()
    assert np.allclose(measure_panel(bundle / "manuscript.pdf")["width_mm"], 101.6)
    slide = measure_panel(bundle / "slide.svg")
    assert np.allclose([slide["width_mm"], slide["height_mm"]], [193.333333, 145], atol=.02)
    svg = (bundle / "slide.svg").read_text()
    assert "viewBox=" in svg and "<text" in svg
    assert receipt["slide"]["svg_integrity"]["artwork_unchanged"] is True
    assert np.allclose(fig.get_size_inches(), before_size) and len(ax.lines) == before_lines
    assert json.loads((bundle / "receipt.json").read_text())["sha256"] == receipt["sha256"]
    plt.close(fig)


def test_delivery_reviews_small_text_refuses_overwrite_and_cleans_failed_bundle(tmp_path, monkeypatch):
    pytest.importorskip("pypdf")
    fig, _ = native_figure()
    receipt = save_for_paper_and_slides(fig, tmp_path / "review", min_slide_text_pt=100)
    assert receipt["status"] == "REVIEW"
    assert "MIN_SLIDE_TEXT_BELOW_THRESHOLD" in receipt["review_reasons"]
    with pytest.raises(FileExistsError):
        save_for_paper_and_slides(fig, tmp_path / "review")
    failed = tmp_path / "failed"
    original = fig.savefig
    def fail(*args, **kwargs):
        raise RuntimeError("render failed")
    monkeypatch.setattr(fig, "savefig", fail)
    with pytest.raises(RuntimeError, match="render failed"):
        save_for_paper_and_slides(fig, failed)
    assert not failed.exists()
    monkeypatch.setattr(fig, "savefig", original)
    plt.close(fig)


def test_delivery_rejects_bad_inputs_without_creating_output(tmp_path):
    fig, _ = native_figure()
    with pytest.raises(ValueError, match="slide_box_mm"):
        save_for_paper_and_slides(fig, tmp_path / "bad", slide_box_mm=(0, 145))
    with pytest.raises(ValueError, match="min_slide_text_pt"):
        save_for_paper_and_slides(fig, tmp_path / "bad", min_slide_text_pt=0)
    assert not (tmp_path / "bad").exists()
    plt.close(fig)


def test_delivery_marks_no_rendered_text_for_review(tmp_path):
    pytest.importorskip("pypdf")
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot([0, 1], [1, 2])
    ax.set_axis_off()
    receipt = save_for_paper_and_slides(fig, tmp_path / "no-text")
    assert receipt["status"] == "REVIEW"
    assert receipt["review_reasons"] == ["NO_RENDERED_TEXT"]
    plt.close(fig)


def test_delivery_supports_non_agg_caller_canvas(tmp_path):
    pytest.importorskip("pypdf")
    fig, _ = native_figure()
    FigureCanvasSVG(fig)
    receipt = save_for_paper_and_slides(fig, tmp_path / "svg-canvas", min_slide_text_pt=5)
    assert receipt["status"] == "PASS"
    plt.close(fig)

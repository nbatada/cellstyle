"""Apply CellStyle manuscript typography to existing Matplotlib plots."""

import math
import hashlib
import json
import shutil
import tempfile
import warnings
from pathlib import Path
from collections.abc import Sequence

import matplotlib as mpl

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .theme import MODES, theme_context
from .layout import correct_layout
from .checks import check_plot
from .provenance import _validate_recipe


def style_plot(plot, *, size_mm=None, output=None, recipe=None):
    """Style native axes or a figure, preserving its data and visual encodings."""
    _validate_recipe(recipe, verify=False)
    if isinstance(plot, Axes):
        figure = plot.figure
    elif isinstance(plot, Figure):
        figure = plot
    else:
        raise TypeError("plot must be a Matplotlib Axes or Figure")

    if size_mm is not None:
        if not isinstance(size_mm, Sequence) or len(size_mm) != 2 or any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0
            for value in size_mm
        ):
            raise ValueError("size_mm must contain two positive finite numbers")
    elif len(figure.axes) == 1:
        size_mm = (90, 60)

    destination = _destination(output)

    if size_mm is not None:
        figure.set_size_inches(size_mm[0] / 25.4, size_mm[1] / 25.4, forward=False)
        if len(figure.axes) == 1:
            figure.set_layout_engine("constrained")
    figure.patch.set_facecolor("white")
    roles = MODES["manuscript"]
    for ax in figure.axes:
        for title in (ax.title, ax._left_title, ax._right_title):
            title.set_fontsize(roles["axes.titlesize"])
            title.set_fontfamily("sans-serif")
        ax.xaxis.label.set_fontsize(roles["axes.labelsize"])
        ax.xaxis.label.set_fontfamily("sans-serif")
        ax.yaxis.label.set_fontsize(roles["axes.labelsize"])
        ax.yaxis.label.set_fontfamily("sans-serif")
        ax.tick_params(axis="both", which="major", width=roles["xtick.major.width"])
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontsize(roles["xtick.labelsize"])
            label.set_fontfamily("sans-serif")
        for spine in ax.spines.values():
            spine.set_linewidth(roles["axes.linewidth"])
        if "top" in ax.spines and ax.xaxis.get_ticks_position() not in ("top", "both"):
            ax.spines["top"].set_visible(False)
        if "right" in ax.spines and ax.yaxis.get_ticks_position() not in ("right", "both"):
            ax.spines["right"].set_visible(False)
        ax.grid(False)
        legend = ax.get_legend()
        if legend is not None:
            for label in legend.get_texts():
                label.set_fontsize(roles["legend.fontsize"])
                label.set_fontfamily("sans-serif")
            if legend.get_title() is not None:
                legend.get_title().set_fontsize(roles["legend.title_fontsize"])
                legend.get_title().set_fontfamily("sans-serif")

    correct_layout(figure)
    if destination is not None:
        _save_figure(figure, destination, recipe=recipe)
    return plot


def _destination(output):
    if output is None:
        return None
    destination = Path(output)
    if destination.suffix.lower() not in {".pdf", ".svg", ".png"}:
        raise ValueError("output must end in .pdf, .svg, or .png")
    if not destination.parent.is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {destination.parent}")
    for path in (destination, Path(str(destination) + ".cellstyle.json")):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Output already exists: {path}")
    return destination


def _save_figure(figure, destination, *, recipe=None):
    _validate_recipe(recipe)
    destination = _destination(destination)
    receipt_path = Path(str(destination) + ".cellstyle.json")
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        candidate = Path(temporary) / destination.name
        with theme_context("manuscript"), mpl.rc_context({"savefig.bbox": None, "svg.fonttype": "none"}):
            inspection = check_plot(figure)
            figure.savefig(candidate, dpi=300 if destination.suffix.lower() == ".png" else None)
        artifact = _artifact_dimensions(candidate)
        receipt = {"schema": "cellstyle-save-1", "asset_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                   "source_provenance": recipe.to_record(destination.parent.resolve()) if recipe is not None else "not supplied",
                   "inspection": inspection, "artifact": artifact,
                   "inspection_scope": "canvas geometry before export; saved-file dimensions when supported"}
        candidate_receipt = Path(temporary) / "report.json"
        candidate_receipt.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        created = []
        try:
            for source, target in ((candidate, destination), (candidate_receipt, receipt_path)):
                with target.open("xb") as stream:
                    created.append(target)
                    with source.open("rb") as input_stream:
                        shutil.copyfileobj(input_stream, stream)
        except Exception:
            for path in created:
                path.unlink()
            raise
    if inspection['diagnostics']:
        warnings.warn(f"CellStyle saved {destination.name} with {len(inspection['diagnostics'])} "
                      f"layout issue(s); see {receipt_path.name} for details.", UserWarning, stacklevel=3)


def _artifact_dimensions(path):
    kind = path.suffix[1:].lower()
    if kind == "png":
        from PIL import Image
        with Image.open(path) as image:
            return {"format": kind, "width_px": image.width, "height_px": image.height,
                    "dpi": list(image.info.get("dpi", ())) }
    if kind in ("svg", "pdf"):
        from .export import measure_panel
        try:
            return {"format": kind, **measure_panel(path)}
        except (ImportError, ValueError) as exc:
            return {"format": kind, "inspection": "unverified", "reason": str(exc)}
    return {"format": kind, "inspection": "unverified"}

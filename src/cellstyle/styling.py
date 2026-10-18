"""Apply CellStyle manuscript typography to existing Matplotlib plots."""

import math
from pathlib import Path
from collections.abc import Sequence

import matplotlib as mpl

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .theme import MODES, theme_context


def style_plot(plot, *, size_mm=None, output=None):
    """Style native axes or a figure, preserving its data and visual encodings."""
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
        if ax.xaxis.get_ticks_position() not in ("top", "both"):
            ax.spines["top"].set_visible(False)
        if ax.yaxis.get_ticks_position() not in ("right", "both"):
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

    if destination is not None:
        _save_figure(figure, destination)
    return plot


def _destination(output):
    if output is None:
        return None
    destination = Path(output)
    if destination.suffix.lower() not in {".pdf", ".svg", ".png"}:
        raise ValueError("output must end in .pdf, .svg, or .png")
    if not destination.parent.is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {destination.parent}")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Output already exists: {destination}")
    return destination


def _save_figure(figure, destination):
    with theme_context("manuscript"), mpl.rc_context({"savefig.bbox": None, "svg.fonttype": "none"}):
        figure.savefig(destination, dpi=300 if destination.suffix.lower() == ".png" else None)

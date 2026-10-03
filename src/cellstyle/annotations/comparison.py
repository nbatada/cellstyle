from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from numbers import Real
from matplotlib.colors import is_color_like
from matplotlib.axes import Axes

from .schema import ComparisonResult


def _coerce_comparison(x) -> ComparisonResult:
    if isinstance(x, ComparisonResult):
        return x

    if isinstance(x, Mapping):
        return ComparisonResult(**x)

    raise TypeError(
        "Each comparison must be a ComparisonResult or mapping."
    )


def _format_p(p: float) -> str:
    if p < 0.001:
        return "P < 0.001"

    if p < 0.01:
        return f"P = {p:.3f}"

    return f"P = {p:.2f}"


def _group_positions(
    ax: Axes,
    positions: Mapping[str, float] | None,
) -> dict[str, float]:

    if positions is not None:
        return dict(positions)

    labels = [
        tick.get_text()
        for tick in ax.get_xticklabels()
    ]

    if len(labels) != len(set(labels)) or any(not label for label in labels):
        raise ValueError("X tick labels must uniquely identify groups; otherwise supply positions.")
    ticks = list(ax.get_xticks())

    return {
        label: float(pos)
        for label, pos in zip(labels, ticks)
        if label
    }


def add_comparisons(
    ax: Axes,
    comparisons: Sequence[ComparisonResult | Mapping],
    *,
    positions: Mapping[str, float] | None = None,
    y_start: float | None = None,
    step_fraction: float = 0.08,
    bracket_height_fraction: float = 0.025,
    line_width: float = 0.9,
    color: str = "#202020",
    fontsize: float = 8.5,
    show_adjusted_marker: bool = True,
) -> Axes:
    """
    Render supplied statistical comparisons on an existing axis.

    Important
    ---------
    This function performs NO statistical test.

    Parameters
    ----------
    ax
        Existing Matplotlib axis.
    comparisons
        Statistical results already computed elsewhere.
    positions
        Optional mapping from group label to x coordinate.
        If omitted, CellStyle uses current x tick labels.
    """

    results = [
        _coerce_comparison(x)
        for x in comparisons
    ]

    if not results:
        return ax

    if ax.name != "rectilinear" or ax.get_xscale() != "linear" or ax.get_yscale() != "linear":
        raise ValueError("Comparisons require Cartesian axes with linear scales and categorical x positions.")
    def finite(value):
        return isinstance(value, Real) and not isinstance(value, bool) and np.isfinite(value)
    for name, value in (("step_fraction", step_fraction), ("bracket_height_fraction", bracket_height_fraction),
                        ("line_width", line_width), ("fontsize", fontsize)):
        if not finite(value) or value < 0:
            raise ValueError(f"{name} must be a finite nonnegative number.")
    if step_fraction <= bracket_height_fraction or line_width == 0 or fontsize == 0:
        raise ValueError("Spacing must exceed bracket height, and line width/font size must be positive.")
    if y_start is not None and not finite(y_start):
        raise ValueError("y_start must be finite.")
    if not is_color_like(color):
        raise ValueError("Invalid annotation color.")
    xpos = _group_positions(ax, positions)
    if any(not finite(pos) for pos in xpos.values()) or len(set(xpos.values())) != len(xpos):
        raise ValueError("Group positions must be finite and distinct.")
    # Validate every result before adding any artist or changing limits.
    for result in results:
        for field in ("group_a", "group_b"):
            if getattr(result, field) not in xpos:
                raise KeyError(f"Unknown {field}: {getattr(result, field)!r}")
        if result.label is None and result.display_p() is None:
            raise ValueError("Each comparison needs a label or supplied P value.")

    ymin, ymax = ax.get_ylim()
    yrange = ymax - ymin

    if not np.isfinite(yrange) or yrange <= 0:
        raise ValueError("Axis has invalid Y range.")

    if y_start is None:
        y_start = ymax + (0.05 * yrange)

    step = step_fraction * yrange
    bracket_h = bracket_height_fraction * yrange

    if not np.isfinite(y_start + len(results) * step + bracket_h):
        raise ValueError("Annotation geometry exceeds finite coordinates.")
    top = ymax

    for i, result in enumerate(results):

        if result.group_a not in xpos:
            raise KeyError(
                f"Unknown group_a: {result.group_a!r}"
            )

        if result.group_b not in xpos:
            raise KeyError(
                f"Unknown group_b: {result.group_b!r}"
            )

        x1 = xpos[result.group_a]
        x2 = xpos[result.group_b]

        if x2 < x1:
            x1, x2 = x2, x1

        y = y_start + (i * step)

        ax.plot(
            [x1, x1, x2, x2],
            [y, y + bracket_h, y + bracket_h, y],
            color=color,
            linewidth=line_width,
            clip_on=False,
            zorder=20,
        )

        if result.label is not None:
            label = result.label

        else:
            p = result.display_p()

            if p is None:
                label = ""

            else:
                label = _format_p(p)

                if (
                    show_adjusted_marker
                    and result.p_adjusted is not None
                ):
                    label += " adj."

        if label:
            ax.text(
                (x1 + x2) / 2,
                y + bracket_h + (0.012 * yrange),
                label,
                ha="center",
                va="bottom",
                fontsize=fontsize,
                color=color,
                clip_on=False,
            )

        top = max(
            top,
            y + bracket_h + (0.06 * yrange),
        )

    if top > ymax:
        ax.set_ylim(ymin, top)

    return ax

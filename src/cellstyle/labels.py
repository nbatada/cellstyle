from __future__ import annotations

from collections.abc import Sequence
from adjustText import adjust_text
from matplotlib.axes import Axes
from matplotlib.text import Text


def repel_labels(
    texts: Sequence[Text],
    ax: Axes,
    *,
    expand=(1.15, 1.25),
    force_text=(0.5, 0.7),
    force_points=(0.2, 0.3),
    force_static=None,
    leader_color="#777777",
    leader_width=0.6,
    leader_alpha=0.65,
):
    """Minimally repel text labels and their original anchor positions.

    ``force_points`` is retained as an alias for adjustText's ``force_static``.
    An explicit ``force_static`` takes precedence. No observation coordinates
    are supplied, so this does not guarantee avoidance of plotted data points.
    """
    return adjust_text(
        list(texts),
        ax=ax,
        expand=expand,
        force_text=force_text,
        force_static=force_points if force_static is None else force_static,
        arrowprops=dict(
            arrowstyle="-",
            color=leader_color,
            lw=leader_width,
            alpha=leader_alpha,
        ),
    )

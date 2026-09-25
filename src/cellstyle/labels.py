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
    leader_color="#777777",
    leader_width=0.6,
    leader_alpha=0.65,
):
    """Minimally repel existing Matplotlib text labels."""
    return adjust_text(
        list(texts),
        ax=ax,
        expand=expand,
        force_text=force_text,
        force_points=force_points,
        arrowprops=dict(
            arrowstyle="-",
            color=leader_color,
            lw=leader_width,
            alpha=leader_alpha,
        ),
    )

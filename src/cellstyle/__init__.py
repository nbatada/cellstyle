"""Scientifically semantic visualization helpers; native plotting remains primary."""

from importlib.metadata import version as _distribution_version

from .theme import set_theme, theme_context
from .colors import (
    EDITORIAL_VIVID,
    editorial_vivid,
    positive_cmap,
    marker_heatmap_cmap,
    context_color,
)
from .registry import ColorRegistry
from .plots import replicate_distribution, quantitative_scatter
from .annotations import ComparisonResult, add_comparisons
from .labels import repel_labels
from .embedding import categorical_embedding, focus_embedding

# Distribution metadata is generated from the repository's VERSION file.
__version__ = _distribution_version("cellstyle")

__all__ = [
    "__version__",
    "set_theme",
    "theme_context",
    "EDITORIAL_VIVID",
    "editorial_vivid",
    "positive_cmap",
    "marker_heatmap_cmap",
    "context_color",
    "ColorRegistry",
    "replicate_distribution",
    "quantitative_scatter",
    "ComparisonResult",
    "add_comparisons",
    "repel_labels",
    "categorical_embedding",
    "focus_embedding",
]

from .core.layout import FigureLayout, PanelSlot
from .export import export_panel, assemble_svg, measure_panel, validate_assembly
__all__ += ["FigureLayout", "PanelSlot", "export_panel", "assemble_svg", "measure_panel", "validate_assembly"]

# Opt-in semantic checks leave legacy plotting behavior unchanged.
from .core.semantics import semantic_fact, semantic_contract, read_semantic_contract, validate_semantics
from .semantic_plot import collect_semantic_text, prepare_semantic_plot
__all__ += ["semantic_fact", "semantic_contract", "read_semantic_contract", "validate_semantics",
            "collect_semantic_text", "prepare_semantic_plot"]

from .styling import style_plot
__all__ += ["style_plot"]

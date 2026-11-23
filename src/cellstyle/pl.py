"""Native CellStyle plots. Existing scatter and swarm names remain aliases."""
from .distributions import grouped_swarm, paired
from .facets import facet
from .intervals import forest
from .matrices import dotplot, heatmap
from .overview import cell_overview
from .plots import quantitative_scatter as scatter
from .plots import replicate_distribution as swarm
from .shapes import boxplot, violin

__all__ = [
    "boxplot", "cell_overview", "dotplot", "facet", "forest", "grouped_swarm",
    "heatmap", "paired", "scatter", "swarm", "violin",
]

from .outlines import cluster_outline
__all__ += ["cluster_outline"]

"""Contracts that must hold for an installed checkout and its release metadata."""

from importlib.metadata import distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

import cellstyle as cs


ROOT = Path(__file__).resolve().parents[1]


def test_version_and_release_metadata_agree():
    expected = (ROOT / "VERSION").read_text().strip()
    assert cs.__version__ == distribution("cellstyle").version == expected
    assert f"version: {expected}\n" in (ROOT / "CITATION.cff").read_text()
    assert f"## {expected} " in (ROOT / "CHANGELOG.md").read_text()


def test_public_api_preserves_v011_exports():
    v011_exports = {
        "__version__", "set_theme", "theme_context", "EDITORIAL_VIVID",
        "editorial_vivid", "positive_cmap", "marker_heatmap_cmap", "context_color",
        "ColorRegistry", "replicate_distribution", "quantitative_scatter",
        "ComparisonResult", "add_comparisons",
    }

    # Backward compatibility:
    # all v0.1.1 public names must remain available.
    assert v011_exports.issubset(set(cs.__all__))


def test_v012_public_api_additions():
    v012_additions = {
        "repel_labels",
        "categorical_embedding",
        "focus_embedding",
    }

    assert v012_additions.issubset(set(cs.__all__))
    from cellstyle.annotations import ComparisonResult, add_comparisons
    assert cs.ComparisonResult is ComparisonResult
    assert cs.add_comparisons is add_comparisons


def test_core_metadata_and_optional_scanpy():
    metadata = distribution("cellstyle").metadata
    requirements = [Requirement(item) for item in metadata.get_all("Requires-Dist")]
    core = {canonicalize_name(item.name) for item in requirements if item.marker is None}
    assert core == {"matplotlib", "numpy", "pandas", "seaborn", "adjusttext"}
    scanpy = next(item for item in requirements if item.name == "scanpy")
    assert scanpy.marker is not None
    assert not scanpy.marker.evaluate({"extra": ""})
    assert scanpy.marker.evaluate({"extra": "scanpy"})
    assert metadata["License-Expression"] == "MIT"
    assert metadata["Requires-Python"] == ">=3.10"

"""Scanpy-compatible plotting facade.

UMAP visual defaults are under development. At this checkpoint all nine named
functions are compatibility passthroughs, not visually validated styled plots.
Importing this module does not import Scanpy. Accessing a plot attribute loads
Scanpy metadata when available; calling that function requires Scanpy.
"""
from __future__ import annotations

from functools import wraps

__all__ = [
    "embedding", "umap", "tsne", "pca", "dotplot", "matrixplot", "heatmap",
    "violin", "stacked_violin",
]


def _require_scanpy():
    try:
        import scanpy as sc
    except ImportError as exc:
        raise ImportError(
            "cellstyle.pl requires Scanpy. "
            "Install with: pip install 'cellstyle[scanpy]'"
        ) from exc
    return sc


def _make_wrapper(name):
    def wrapper(*args, **kwargs):
        # Preserve native arguments, display/save controls, exceptions and return
        # objects. Defaults will be added only after the visual selection gate.
        return getattr(_require_scanpy().pl, name)(*args, **kwargs)

    wrapper.__name__ = name
    wrapper.__qualname__ = name
    wrapper.__doc__ = (
        f"Compatibility passthrough to scanpy.pl.{name}. "
        "No CellStyle visual defaults have been selected for this function."
    )
    try:
        native = getattr(_require_scanpy().pl, name)
    except ImportError:
        # Namespace discovery remains usable without the optional dependency.
        # Calling the function raises the installation guidance above.
        pass
    else:
        wrapper = wraps(native)(wrapper)
        wrapper.__module__ = __name__
        wrapper.__qualname__ = name
    return wrapper


def __getattr__(name):
    if name in __all__:
        wrapper = _make_wrapper(name)
        globals()[name] = wrapper
        return wrapper
    if name.startswith("_"):
        raise AttributeError(name)
    raise AttributeError(
        f"cellstyle.pl.{name} is not supported. Use scanpy.pl.{name} directly. "
        "Only the documented compatibility functions are exposed."
    )


def __dir__():
    return sorted(set(globals()) | set(__all__))

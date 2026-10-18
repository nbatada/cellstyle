"""Inspect native Matplotlib text after drawing a semantic plot."""

from __future__ import annotations

from collections.abc import Callable

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.text import Text

from .core.semantics import validate_semantics
from .theme import theme_context


def collect_semantic_text(plot):
    """Collect one fresh native text snapshot; unknown artists remain visible as limitations."""
    if isinstance(plot, Axes):
        figure, axes = plot.figure, [plot]
    elif isinstance(plot, Figure):
        figure, axes = plot, list(plot.axes)
    elif isinstance(plot, (list, tuple)) and plot and all(isinstance(ax, Axes) for ax in plot):
        axes = list(plot)
        figure = axes[0].figure
        if any(ax.figure is not figure for ax in axes):
            raise ValueError("UNSUPPORTED_PLOT: axes must share one Figure")
    else:
        raise ValueError("UNSUPPORTED_PLOT: expected Matplotlib Figure, Axes, or axes list")

    figure.canvas.draw()
    observed, supported, limitations = [], set(), []
    if any(ax not in axes for ax in figure.axes):
        limitations.append("other figure axes were not mapped")
    if figure.legends:
        limitations.append("figure-level legends were not mapped")

    def record(binding, role, native_text):
        supported.add(binding)
        if isinstance(native_text, Text) and not native_text.get_visible():
            return
        text = native_text.get_text() if isinstance(native_text, Text) else str(native_text)
        if text:
            observed.append({"binding": binding, "role": role, "text": text})

    record("figure.title", "figure_title", figure._suptitle if figure._suptitle else "")
    known_figure_text = {figure._suptitle} if figure._suptitle else set()
    for index, native_text in enumerate(figure.texts):
        if native_text not in known_figure_text:
            record(f"figure.text[{index}]", "annotation", native_text)
            known_figure_text.add(native_text)

    for ax_index, ax in enumerate(axes):
        prefix = "" if len(axes) == 1 else f"axes[{ax_index}]."
        if not ax.get_visible():
            limitations.append(f"{prefix}hidden axes cannot verify visible text")
            continue
        if ax.get_label().startswith("<colorbar>") or getattr(ax, "_colorbar", None) is not None:
            limitations.append(f"{prefix}colorbar native text not mapped")
            continue
        record(prefix + "x.title", "axis_title", ax.xaxis.label if ax.axison and ax.xaxis.get_visible() else "")
        record(prefix + "y.title", "axis_title", ax.yaxis.label if ax.axison and ax.yaxis.get_visible() else "")
        record(prefix + "title", "figure_title", ax.title)
        record(prefix + "title.left", "figure_title", ax._left_title)
        record(prefix + "title.right", "figure_title", ax._right_title)
        for axis_name, ticklabels in (("x", ax.get_xticklabels()), ("y", ax.get_yticklabels())):
            for index, native_text in enumerate(ticklabels):
                if ax.axison and getattr(ax, axis_name + "axis").get_visible() and native_text.get_visible():
                    record(prefix + f"{axis_name}.tick[{index}]", "axis_tick", native_text)
        legend = ax.get_legend()
        if isinstance(legend, Legend) and legend.get_visible():
            record(prefix + "legend.title", "legend_title", legend.get_title())
            for index, native_text in enumerate(legend.get_texts()):
                record(prefix + f"legend.item[{index}]", "legend_item", native_text)
        else:
            supported.add(prefix + "legend.title")
        for index, native_text in enumerate(ax.texts):
            record(prefix + f"annotation[{index}]", "annotation", native_text)
        known = {ax.xaxis.label, ax.yaxis.label, ax.title, ax._left_title, ax._right_title}
        known.update(ax.get_xticklabels())
        known.update(ax.get_yticklabels())
        known.update(ax.texts)
        if legend:
            known.add(legend.get_title())
            known.update(legend.get_texts())
        for native_text in ax.findobj(Text):
            if native_text.get_visible() and native_text.get_text() and native_text not in known:
                limitations.append(f"{prefix}unmapped native text: {native_text.get_text()!r}")
    return {"observed": observed, "supported_bindings": sorted(supported), "limitations": limitations}


def prepare_semantic_plot(plot_or_callback, contract, mode="ANALYSIS_RESULT",
                          visual_intent="review", base_dir=".", actual=None):
    """Preflight a declaration, then render and inspect the original native object."""
    preflight = validate_semantics(contract, mode=mode, base_dir=base_dir, actual=actual)
    disqualifying = [d for d in preflight["diagnostics"]
                     if d["severity"] == "FAIL" and d["code"] != "NO_RENDER"]
    if disqualifying:
        return {"plot": plot_or_callback if not callable(plot_or_callback) else None,
                "report": preflight, "preflight": preflight,
                "preflight_before_render": callable(plot_or_callback)}
    if isinstance(plot_or_callback, Callable):
        with theme_context(visual_intent):
            plot = plot_or_callback(preflight["resolved"])
            collected = collect_semantic_text(plot)
    else:
        plot = plot_or_callback
        collected = collect_semantic_text(plot)
    report = validate_semantics(contract, mode=mode, base_dir=base_dir, actual=actual,
                                observed=collected["observed"], rendered=True,
                                supported_bindings=collected["supported_bindings"])
    for limitation in collected["limitations"]:
        report["diagnostics"].append({"code": "UNSUPPORTED_SURFACE", "severity": "FAIL" if mode == "MANUSCRIPT_FINAL" else "WARN",
                                      "path": "$.render", "message": limitation})
    report["coverage"]["limitations"] = collected["limitations"]
    if collected["limitations"]:
        report["label_verdict"] = "FAIL" if mode == "MANUSCRIPT_FINAL" else (
            "WARN" if report["label_verdict"] == "PASS" else report["label_verdict"])
    return {"plot": plot, "report": report, "preflight": preflight,
            "preflight_before_render": callable(plot_or_callback)}

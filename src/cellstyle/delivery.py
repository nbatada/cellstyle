"""Export one untouched Matplotlib figure for paper and slide placement."""
from __future__ import annotations

import hashlib
import json
import math
import re
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib as mpl
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.backends.backend_agg import FigureCanvasAgg

from .checks import check_plot
from .export import measure_panel


_ROOT = re.compile(r"(<svg\b[^>]*)(>)", re.IGNORECASE)
_ATTRIBUTE = re.compile(r"\s(?:width|height)=(['\"]).*?\1", re.IGNORECASE)
_VIEWBOX = re.compile(r"\sviewBox=(['\"])(.*?)\1", re.IGNORECASE)
_ID = re.compile(r"\bid=(['\"])(.*?)\1")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _figure(plot) -> Figure:
    if isinstance(plot, Axes):
        return plot.figure
    if isinstance(plot, Figure):
        return plot
    raise TypeError("plot must be a Matplotlib Axes or Figure")


def _positive_pair(value, name):
    if (not isinstance(value, (tuple, list)) or len(value) != 2 or
            any(isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item) or item <= 0 for item in value)):
        raise ValueError(f"{name} must contain two positive numbers")
    return tuple(float(item) for item in value)


def _svg_type_sizes(path, placed_width_mm):
    """Inspect actual Matplotlib SVG lettering; flag unsupported transformed text."""
    root = ET.parse(path).getroot()
    units_per_page = float(root.attrib["viewBox"].split()[2])
    pt_per_unit = placed_width_mm * 72 / 25.4 / units_per_page
    sizes = []
    unknown = False
    def visit(node, transformed=False):
        nonlocal unknown
        changed = transformed or bool(re.search(r"scale|matrix|skew", node.get("transform", "")))
        if node.tag.endswith("}text"):
            # Matplotlib versions emit either CSS font-size or a font shorthand.
            match = re.search(r"(?:font-size:\s*|\b)([\d.]+)px\b", node.get("style", ""))
            if changed or match is None or len(node):
                unknown = True
            else:
                sizes.append(float(match.group(1)) * pt_per_unit)
        for child in node:
            visit(child, changed)
    visit(root)
    return sizes, unknown


def _rewrite_svg_size(raw: Path, slide: Path, width_mm: float, height_mm: float):
    content = raw.read_text(encoding="utf-8")
    match = _ROOT.search(content)
    if match is None:
        raise ValueError("Matplotlib SVG has no root element")
    original_root = match.group(1)
    viewbox = _VIEWBOX.search(original_root)
    if viewbox is None:
        raise ValueError("Matplotlib SVG has no viewBox")
    new_root = _ATTRIBUTE.sub("", original_root)
    new_root += f' width="{width_mm:.6f}mm" height="{height_mm:.6f}mm"'
    rewritten = content[:match.start(1)] + new_root + content[match.start(2):]
    new_match = _ROOT.search(rewritten)
    if new_match is None or _VIEWBOX.search(new_match.group(1)).group(2) != viewbox.group(2):
        raise ValueError("Slide export changed the SVG viewBox")
    # Only root physical dimensions may differ: every local ID, reference and text stays byte-identical.
    if content[match.end(2):] != rewritten[new_match.end(2):]:
        raise ValueError("Slide export changed SVG artwork")
    raw_ids = _ID.findall(content[match.end(2):])
    slide_ids = _ID.findall(rewritten[new_match.end(2):])
    if raw_ids != slide_ids:
        raise ValueError("Slide export changed SVG IDs")
    slide.write_text(rewritten, encoding="utf-8")
    return {"viewBox": viewbox.group(2), "id_count": len(raw_ids), "artwork_unchanged": True}


def _remove_partial(directory: Path, created: list[Path]) -> None:
    """Remove only artifacts created by this call; leave concurrent files alone."""
    for artifact in created:
        if artifact.exists() or artifact.is_symlink():
            artifact.unlink()
    if directory.exists() and not any(directory.iterdir()):
        directory.rmdir()


def save_for_paper_and_slides(plot, directory, *, slide_box_mm=(250, 145), min_slide_text_pt=16):
    """Save manuscript PDF and proportionally placed SVG for a slide.

    The original figure is never resized or otherwise transformed. The PDF keeps
    its existing physical dimensions. The SVG has the same viewBox and artwork;
    only its root width and height are changed to its fitted slide placement.
    """
    figure = _figure(plot)
    box_width, box_height = _positive_pair(slide_box_mm, "slide_box_mm")
    if (isinstance(min_slide_text_pt, bool) or not isinstance(min_slide_text_pt, (int, float))
            or not math.isfinite(min_slide_text_pt) or min_slide_text_pt <= 0):
        raise ValueError("min_slide_text_pt must be a positive number")
    output = Path(directory)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Delivery directory already exists: {output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(f"Delivery parent does not exist: {output.parent}")
    source_size = tuple(float(value) * 25.4 for value in figure.get_size_inches())
    scale = min(box_width / source_size[0], box_height / source_size[1])
    slide_size = (source_size[0] * scale, source_size[1] * scale)
    output.mkdir()
    created = []
    try:
        inspection_figure = copy.deepcopy(figure)
        FigureCanvasAgg(inspection_figure)
        geometry = check_plot(inspection_figure)
        manuscript = output / "manuscript.pdf"
        raw_svg = output / ".raw.svg"
        slide = output / "slide.svg"
        with mpl.rc_context({"pdf.fonttype": 42, "pdf.use14corefonts": False,
                             "svg.fonttype": "none", "savefig.bbox": None}):
            created.append(manuscript)
            figure.savefig(manuscript, format="pdf", bbox_inches=None)
            created.append(raw_svg)
            figure.savefig(raw_svg, format="svg", bbox_inches=None)
        created.append(slide)
        svg_integrity = _rewrite_svg_size(raw_svg, slide, *slide_size)
        raw_svg.unlink()
        created.remove(raw_svg)
        manuscript_measurement = measure_panel(manuscript)
        slide_measurement = measure_panel(slide)
        if any(abs(measured - expected) > .02 for measured, expected in zip(
                (manuscript_measurement["width_mm"], manuscript_measurement["height_mm"]), source_size)):
            raise ValueError("Manuscript PDF dimensions differ from the existing figure")
        if any(abs(measured - expected) > .02 for measured, expected in zip(
                (slide_measurement["width_mm"], slide_measurement["height_mm"]), slide_size)):
            raise ValueError("Slide SVG dimensions differ from its fitted placement")
        placed_sizes, unknown_type = _svg_type_sizes(slide, slide_size[0])
        reasons = []
        if not placed_sizes:
            reasons.append("NO_RENDERED_TEXT")
        elif min(placed_sizes) < min_slide_text_pt:
            reasons.append("MIN_SLIDE_TEXT_BELOW_THRESHOLD")
        if unknown_type or any(t.get_usetex() for t in figure.findobj(Text) if t.get_visible() and t.get_text()):
            reasons.append("UNVERIFIED_TEXT_SIZE")
        if geometry["status"] != "PASS":
            reasons.append("GEOMETRY_WARNINGS")
        receipt = {
            "schema": "cellstyle-paper-slides-1",
            "status": "PASS" if not reasons else "REVIEW",
            "manuscript": {"path": manuscript.name, "dimensions_mm": manuscript_measurement},
            "slide": {"path": slide.name, "dimensions_mm": slide_measurement,
                      "fit_scale": scale, "viewBox": svg_integrity["viewBox"],
                      "svg_integrity": svg_integrity},
            "slide_box_mm": [box_width, box_height],
            "source_size_mm": list(source_size),
            "typography": {"min_slide_text_pt": min(placed_sizes) if placed_sizes else None,
                           "required_min_slide_text_pt": float(min_slide_text_pt),
                           "measured_svg_text_count": len(placed_sizes)},
            "sha256": {"manuscript.pdf": _sha256(manuscript), "slide.svg": _sha256(slide)},
            "geometry": geometry,
            "review_reasons": reasons,
            "limitations": ["Scientific validity, content meaning and journal compliance are not inferred.",
                            "Font substitution after presentation import requires visual review.",
                            "Only root SVG physical dimensions change; editable SVG artwork is otherwise preserved."],
        }
        receipt_path = output / "receipt.json"
        created.append(receipt_path)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        if tuple(float(value) * 25.4 for value in figure.get_size_inches()) != source_size:
            raise RuntimeError("Delivery changed the caller figure size")
        return receipt
    except Exception:
        _remove_partial(output, created)
        raise

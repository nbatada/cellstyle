"""Opt-in exact-size panel export. Technical evidence is not visual acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

from .core.layout import FigureLayout, PanelSlot

TOLERANCE_MM = 0.02
NATURE_PROFILE = {
    'id': 'nature-flagship-final-research', 'checked_date': '2026-09-28',
    'journal': 'Nature', 'stage': 'final research artwork',
    'sources': ['https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/',
                'https://www.nature.com/nature/for-authors/final-submission'],
    'ordinary_text_pt': [5, 7], 'panel_letter_pt': 8,
    'status': 'recorded publisher rules; not a compliance certificate',
}


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def measure_panel(path):
    """Read actual single-page PDF boxes or explicit SVG physical dimensions."""
    path = Path(path)
    if path.suffix.lower() == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ImportError('PDF checking requires cellstyle[export] (pypdf)') from exc
        reader = PdfReader(path)
        if len(reader.pages) != 1:
            raise ValueError('panel PDF must have exactly one page')
        page = reader.pages[0]
        if page.rotation or float(page.get('/UserUnit', 1)) != 1:
            raise ValueError('rotated or scaled PDF page is unsupported')
        if list(page.cropbox) != list(page.mediabox):
            raise ValueError('PDF crop box differs from media box')
        fonts = []
        resources = page['/Resources'].get_object()
        for ref in resources.get('/Font', {}).values():
            font = ref.get_object()
            descendant = font.get('/DescendantFonts')
            actual = descendant[0].get_object() if descendant else font
            descriptor = actual.get('/FontDescriptor')
            descriptor = descriptor.get_object() if descriptor else {}
            embedded = any(k in descriptor for k in ('/FontFile', '/FontFile2', '/FontFile3'))
            fonts.append({'name': str(font.get('/BaseFont')), 'embedded': embedded})
        if any(not f['embedded'] for f in fonts):
            raise ValueError('PDF contains unembedded fonts')
        return {'width_mm': float(page.mediabox.width) * 25.4 / 72,
                'height_mm': float(page.mediabox.height) * 25.4 / 72, 'fonts': fonts}
    if path.suffix.lower() == '.svg':
        root = ET.parse(path).getroot()
        def mm(value):
            match = re.fullmatch(r'([0-9.eE+-]+)(mm|cm|in|pt)', value or '')
            if not match:
                raise ValueError('SVG must declare explicit physical units')
            return float(match[1]) * {'mm': 1, 'cm': 10, 'in': 25.4, 'pt': 25.4/72}[match[2]]
        return {'width_mm': mm(root.get('width')), 'height_mm': mm(root.get('height')),
                'live_text_count': len(root.findall('.//{http://www.w3.org/2000/svg}text'))}
    raise ValueError('panel format must be PDF or SVG')


def _check_size(measured, slot):
    if any(abs(measured[k] - getattr(slot, k)) > TOLERANCE_MM for k in ('width_mm', 'height_mm')):
        raise ValueError('exported page size differs from slot')


def export_panel(fig, layout, panel_id, path, *, source_path, font_family,
                 text_roles=None, bbox_inches=None):
    """Render a copy of a Matplotlib figure; never tight-crop or shrink text.

    text_roles maps Text artist gid strings to 'ordinary' or 'panel_letter'.
    Unspecified visible text is ordinary. Source file is required for provenance.
    """
    import matplotlib as mpl
    from matplotlib import font_manager
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.text import Text
    from matplotlib.legend import Legend
    if bbox_inches is not None:
        raise ValueError('bbox_inches is forbidden for physical slots')
    path = Path(path)
    if path.suffix.lower() not in ('.pdf', '.svg'):
        raise ValueError('panel format must be PDF or SVG')
    source_hash = _hash(source_path)
    slot = layout.slot(panel_id)
    roles = text_roles or {}
    if any(v not in ('ordinary', 'panel_letter') for v in roles.values()):
        raise ValueError('unsupported text role')
    if layout.letter_owner == 'assembly' and 'panel_letter' in roles.values():
        raise ValueError('panel letters are assembly-owned')
    if not isinstance(font_family, str) or font_family in ('sans-serif', 'serif', 'monospace'):
        raise ValueError('declare an installed concrete font family')
    font_manager.findfont(font_manager.FontProperties(family=font_family), fallback_to_default=False)
    work = copy.deepcopy(fig)
    work.set_size_inches(slot.width_mm / 25.4, slot.height_mm / 25.4, forward=False)
    canvas = FigureCanvasAgg(work)
    canvas.draw()
    renderer = canvas.get_renderer()
    observations = []
    # Observe only text actually drawn; Matplotlib keeps off-axis tick Text objects.
    drawn = []
    original_draw_text = renderer.draw_text
    def record_text(*args, **kwargs):
        artist = kwargs.get('mtext')
        if artist is not None and artist.get_text().strip() and artist not in drawn:
            drawn.append(artist)
        return original_draw_text(*args, **kwargs)
    renderer.draw_text = record_text
    try:
        canvas.draw()
    finally:
        renderer.draw_text = original_draw_text
    texts = drawn
    unknown_roles = set(roles) - {t.get_gid() for t in texts}
    if unknown_roles:
        raise ValueError(f'text role IDs not present: {sorted(unknown_roles)}')
    for t in texts:
        if t.get_usetex() or (t.get_parse_math() and mpl.cbook.is_math_text(t.get_text())):
            raise ValueError('math/TeX text requires separate font-role review')
        resolved = font_manager.findfont(t.get_fontproperties(), fallback_to_default=False)
        actual_family = font_manager.FontProperties(fname=resolved).get_name()
        if actual_family.casefold() != font_family.casefold():
            raise ValueError(f'font mismatch: {actual_family}; expected {font_family}')
        role = roles.get(t.get_gid(), 'ordinary')
        size = t.get_fontsize()
        if layout.profile == NATURE_PROFILE['id']:
            if role == 'ordinary' and not 5 <= size <= 7:
                raise ValueError(f'ordinary text must be 5–7 pt; found {size}')
            if role == 'panel_letter' and (size != 8 or t.get_fontstyle() != 'normal'
                    or t.get_fontweight() not in ('bold', 700) or not t.get_text().islower()):
                raise ValueError('panel letters must be lowercase bold upright 8 pt')
        observations.append({'text': t.get_text(), 'role': role, 'size_pt': size,
                             'family': actual_family, 'font_sha256': _hash(resolved)})
    tolerance_px = TOLERANCE_MM / 25.4 * work.dpi
    for artist in [*texts, *work.findobj(Legend)]:
        if not artist.get_visible():
            continue
        box = artist.get_window_extent(renderer)
        if (box.x0 < -tolerance_px or box.y0 < -tolerance_px or
                box.x1 > work.bbox.width + tolerance_px or box.y1 > work.bbox.height + tolerance_px):
            raise ValueError('text or legend outside panel canvas; rerender for the slot')
        if slot.letter_reserve_mm:
            x, y, w, h = slot.letter_reserve_mm
            factor = work.dpi / 25.4
            left, right = x * factor, (x + w) * factor
            bottom, top = (slot.height_mm-y-h)*factor, (slot.height_mm-y)*factor
            if box.x0 < right and box.x1 > left and box.y0 < top and box.y1 > bottom:
                raise ValueError('text or legend intersects reserved letter area')
    # A temporary sibling prevents failed validation from replacing an existing asset.
    with tempfile.TemporaryDirectory(dir=path.parent) as tmp:
        candidate = Path(tmp) / path.name
        with mpl.rc_context({'pdf.fonttype': 42, 'pdf.use14corefonts': False,
                             'svg.fonttype': 'none', 'savefig.bbox': None}):
            work.savefig(candidate, format=path.suffix[1:].lower(), bbox_inches=None)
        measured = measure_panel(candidate)
        _check_size(measured, slot)
        if path.suffix.lower() == '.svg' and texts and measured['live_text_count'] == 0:
            raise ValueError('SVG text was converted to paths')
        receipt = {'schema': 'cellstyle-panel-receipt-1', 'status': 'PANEL_GEOMETRY_TEXT_CHECKED',
                   'layout_id': layout.id, 'layout_sha256': layout.sha256, 'panel_id': panel_id,
                   'slot': slot.__dict__, 'source_path': str(Path(source_path).resolve()),
                   'source_sha256': source_hash, 'asset_sha256': _hash(candidate),
                   'measured': measured, 'tolerance_mm': TOLERANCE_MM,
                   'text': observations, 'profile': NATURE_PROFILE if layout.profile == NATURE_PROFILE['id'] else 'custom',
                   'review_required': ['marks and internal clipping', 'raster resolution',
                                       'font substitution after import', 'final-size visual and scientific review']}
        candidate.replace(path)
    Path(str(path) + '.receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def assemble_svg(layout, panels, path):
    """Create a portable editable SVG assembly from checked SVG panels at scale 1.

    panels maps every slot ID to an SVG path with its adjacent export receipt.
    PDF panels must be imported manually at their recorded physical dimensions.
    """
    if set(panels) != {s.id for s in layout.slots}:
        raise ValueError('assembly requires every panel exactly once')
    ns = 'http://www.w3.org/2000/svg'
    ET.register_namespace('', ns)
    root = ET.Element(f'{{{ns}}}svg', width=f'{layout.width_mm}mm', height=f'{layout.height_mm}mm',
                      viewBox=f'0 0 {layout.width_mm} {layout.height_mm}')
    placements = []
    for index, slot in enumerate(layout.slots):
        asset = Path(panels[slot.id])
        if asset.suffix.lower() != '.svg':
            raise ValueError('automatic assembly requires SVG panels')
        receipt = json.loads(Path(str(asset) + '.receipt.json').read_text())
        if (receipt['asset_sha256'] != _hash(asset) or receipt['layout_sha256'] != layout.sha256
                or receipt['panel_id'] != slot.id):
            raise ValueError('panel receipt hash/layout/slot mismatch')
        _check_size(measure_panel(asset), slot)
        panel = ET.parse(asset).getroot()
        # Namespace IDs and references to avoid clipPath/font collisions between panels.
        mapping = {e.get('id'): f'p{index}_{e.get("id")}' for e in panel.iter() if e.get('id')}
        for e in panel.iter():
            if e.get('id'):
                e.set('id', mapping[e.get('id')])
            for key, value in list(e.attrib.items()):
                for old, new in mapping.items():
                    value = value.replace(f'url(#{old})', f'url(#{new})')
                    if value == f'#{old}':
                        value = f'#{new}'
                e.set(key, value)
        panel.set('x', str(slot.x_mm)); panel.set('y', str(slot.y_mm))
        panel.set('width', str(slot.width_mm)); panel.set('height', str(slot.height_mm))
        root.append(panel)
        placements.append({'panel_id': slot.id, 'x_mm': slot.x_mm, 'y_mm': slot.y_mm,
                           'scale': 1.0, 'asset_sha256': _hash(asset)})
    path = Path(path)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
    result = {'status': 'ASSEMBLY_GEOMETRY_CHECKED', 'layout_sha256': layout.sha256,
              'asset_sha256': _hash(path), 'placements': placements,
              'letter_owner': layout.letter_owner, 'review_required': ['letter placement', 'final-size review', 'scientist acceptance']}
    Path(str(path) + '.receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def validate_assembly(path):
    """Verify an unchanged generated assembly against its scale-1 receipt.

    Edits invalidate this receipt, including apparently harmless edits. Re-export
    or review the edited assembly separately; this is not an Inkscape document linter.
    """
    path = Path(path)
    receipt = json.loads(Path(str(path) + '.receipt.json').read_text())
    if receipt.get('status') != 'ASSEMBLY_GEOMETRY_CHECKED':
        raise ValueError('not an assembly receipt')
    if receipt['asset_sha256'] != _hash(path):
        raise ValueError('assembly changed; scale/placement evidence must be renewed')
    if any(p['scale'] != 1.0 for p in receipt['placements']):
        raise ValueError('assembly scale must be 1.0')
    return receipt

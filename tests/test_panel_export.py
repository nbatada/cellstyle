import json
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pytest
from cellstyle import FigureLayout, PanelSlot, export_panel, assemble_svg, measure_panel, validate_assembly


def layout():
    return FigureLayout('synthetic-four', 183, 130, tuple(
        PanelSlot(k, x, y, 87, 60) for k,x,y in [('a',3,3),('b',93,3),('c',3,67),('d',93,67)]),
        profile='nature-flagship-final-research')


def plot():
    with matplotlib.rc_context({'font.family': 'DejaVu Sans', 'font.size': 6,
                                'axes.titlesize': 6, 'axes.labelsize': 6,
                                'xtick.labelsize': 6, 'ytick.labelsize': 6}):
        fig, ax = plt.subplots(figsize=(4,3))
        fig.subplots_adjust(left=.18,bottom=.22)
        ax.plot([0,1,2], [1,3,2])
        ax.set_xlabel('Synthetic x'); ax.set_ylabel('Synthetic y')
    return fig


def export(fig, path, panel='a', **kw):
    return export_panel(fig, layout(), panel, path, source_path=__file__, font_family='DejaVu Sans', **kw)


def test_layout_roundtrip(tmp_path):
    d = layout(); p = tmp_path/'layout.json'; d.write(p)
    assert FigureLayout.read(p) == d
    assert FigureLayout.read(p).sha256 == d.sha256
    assert d.slot('d').y_mm + d.slot('d').height_mm == 127


def test_invalid_geometry():
    for slots in [(PanelSlot('a',0,0,100,100),PanelSlot('b',1,1,10,10)),
                  (PanelSlot('a',180,0,10,10),),
                  (PanelSlot('a',0,0,10,10),PanelSlot('a',20,20,10,10))]:
        with pytest.raises(ValueError): FigureLayout('bad',183,130,slots)
    with pytest.raises(ValueError): PanelSlot('a',0,0,float('nan'),10)
    with pytest.raises(ValueError): FigureLayout('bad',100,130,(PanelSlot('a',0,0,10,10),),profile='nature-flagship-final-research')


def test_pdf_svg_and_original_unchanged(tmp_path):
    pytest.importorskip('pypdf')
    fig = plot(); before = fig.get_size_inches().copy()
    for suffix in ('pdf','svg'):
        p=tmp_path/f'a.{suffix}'; receipt=export(fig,p)
        assert abs(measure_panel(p)['width_mm']-87) < .02
        assert abs(measure_panel(p)['height_mm']-60) < .02
        assert receipt['source_sha256']
        if suffix == 'pdf': assert all(f['embedded'] for f in receipt['measured']['fonts'])
        else: assert receipt['measured']['live_text_count'] > 0
    assert (before == fig.get_size_inches()).all()
    plt.close(fig)


def test_text_font_crop_failures(tmp_path):
    fig=plot(); target=tmp_path/'a.svg'
    with pytest.raises(ValueError,match='bbox_inches'): export(fig,target,bbox_inches='tight')
    fig.text(1.1,.5,'Outside',fontsize=6,fontfamily='DejaVu Sans')
    with pytest.raises(ValueError,match='outside'): export(fig,target)
    assert not target.exists(); plt.close(fig)
    fig=plot(); fig.axes[0].set_title('Too large',fontsize=8)
    with pytest.raises(ValueError,match='5–7'): export(fig,target)
    fig.axes[0].set_title('Wrong font',fontsize=6,fontfamily='DejaVu Serif')
    with pytest.raises(ValueError,match='font mismatch'): export(fig,target)
    plt.close(fig)


def test_assembly_and_tampering(tmp_path):
    fig=plot(); panels={}
    for s in layout().slots:
        panels[s.id]=tmp_path/f'{s.id}.svg'; export(fig,panels[s.id],s.id)
    dest=tmp_path/'assembly.svg'; r=assemble_svg(layout(),panels,dest)
    assert all(p['scale']==1 for p in r['placements'])
    assert measure_panel(dest)['width_mm']==183
    assert validate_assembly(dest)['status']=='ASSEMBLY_GEOMETRY_CHECKED'
    panel = panels['a']
    receipt = panel.with_suffix('.svg.receipt.json')
    before = (panel.read_bytes(), receipt.read_bytes())
    with pytest.raises(FileExistsError):
        assemble_svg(layout(), panels, panel)
    assert before == (panel.read_bytes(), receipt.read_bytes())
    blocked = tmp_path / "blocked.svg"
    blocked.with_suffix(".svg.receipt.json").write_text("existing")
    with pytest.raises(FileExistsError):
        assemble_svg(layout(), panels, blocked)
    assert not blocked.exists()
    assert blocked.with_suffix(".svg.receipt.json").read_text() == "existing"
    original=dest.read_bytes()
    dest.write_text(dest.read_text().replace('<svg ', '<svg transform="scale(0.9)" ',1))
    with pytest.raises(ValueError,match='assembly changed'): validate_assembly(dest)
    dest.write_bytes(original)
    root=ET.parse(dest).getroot()
    ids=[e.get('id') for e in root.iter() if e.get('id')]
    assert len(ids)==len(set(ids))
    with pytest.raises(ValueError,match='every panel'): assemble_svg(layout(),{'a':panels['a']},dest)
    panels['a'].write_text(panels['a'].read_text()+'\n')
    with pytest.raises(ValueError,match='mismatch'): assemble_svg(layout(),panels,dest)
    plt.close(fig)


def test_svg_namespace_preserves_connectors_and_accessible_names():
    from cellstyle.export import _namespace_svg_ids
    root = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg"
        aria-labelledby="title desc"><title id="title">Patient workflow</title>
        <desc id="desc">Samples progress through analysis.</desc>
        <defs><marker id="arrow"/><clipPath id="clip"/></defs>
        <style>.edge { marker-end: url("#arrow"); }</style>
        <path id="edge" marker-end="url( '#arrow' )" clip-path="url(#clip)"/>
        <text>CD8+ T cells</text><use href="#edge"/></svg>''')
    _namespace_svg_ids(root, 'p0_')
    ns = {'s': 'http://www.w3.org/2000/svg'}
    assert root.get('aria-labelledby') == 'p0_title p0_desc'
    assert root.find('s:path', ns).get('marker-end') == 'url(#p0_arrow)'
    assert root.find('s:path', ns).get('clip-path') == 'url(#p0_clip)'
    assert 'url(#p0_arrow)' in root.find('s:style', ns).text
    assert root.find('s:use', ns).get('href') == '#p0_edge'
    assert root.find('s:text', ns).text == 'CD8+ T cells'


def test_svg_namespace_rejects_ambiguous_ids():
    from cellstyle.export import _namespace_svg_ids
    root = ET.fromstring('<svg><g id="same"/><g id="same"/></svg>')
    with pytest.raises(ValueError, match='duplicate SVG IDs'):
        _namespace_svg_ids(root, 'p0_')


def test_export_preserves_existing_asset_or_receipt(tmp_path):
    fig = plot()
    target = tmp_path / 'existing.svg'
    target.write_text('previous asset')
    with pytest.raises(FileExistsError):
        export(fig, target)
    assert target.read_text() == 'previous asset'
    target.unlink()
    receipt = tmp_path / 'existing.svg.receipt.json'
    receipt.write_text('previous receipt')
    with pytest.raises(FileExistsError):
        export(fig, target)
    assert receipt.read_text() == 'previous receipt'
    assert not target.exists()
    plt.close(fig)

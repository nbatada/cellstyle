"""Compare explicit scientific bindings across live Matplotlib panels."""
from collections import defaultdict
from collections.abc import Mapping
import hashlib

import numpy as np
from matplotlib import colors
from matplotlib.collections import PathCollection
from matplotlib.lines import Line2D
from matplotlib.image import AxesImage


def _name(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} must be a nonempty string')


class FigureSet:
    """Read actual encodings for explicitly bound identities and comparable quantities.

    Identity colors are copied at construction. Units and comparability are caller
    declarations, not biological conclusions. Only registered artists are covered.
    """
    def __init__(self, *, identity_colors=None, comparable_quantities=()):
        if identity_colors is not None and not isinstance(identity_colors, Mapping):
            raise TypeError('identity_colors must be a mapping or ColorRegistry')
        self.identity_colors = dict(identity_colors or {})
        for identity, color in self.identity_colors.items():
            _name(identity, 'identity')
            colors.to_rgba(color)
        if isinstance(comparable_quantities, str):
            raise TypeError('comparable_quantities must be a collection of quantity IDs')
        self.comparable_quantities = set(comparable_quantities)
        for quantity in self.comparable_quantities:
            _name(quantity, 'quantity')
        self._identities = []
        self._quantities = []

    def _add(self, records, panel, key, artist, **metadata):
        _name(panel, 'panel')
        _name(key, 'identity or quantity')
        if any(row['panel'] == panel and row['id'] == key for row in records):
            raise ValueError(f'{panel}/{key} already has a binding')
        records.append({'panel': panel, 'id': key, 'artist': artist, **metadata})
        return self

    def add_identity(self, panel_id, identity_id, artist):
        return self._add(self._identities, panel_id, identity_id, artist)

    def add_quantity(self, panel_id, quantity_id, artist, *, unit):
        _name(unit, 'unit')
        return self._add(self._quantities, panel_id, quantity_id, artist, unit=unit)

    def check(self):
        diagnostics, observed_identities, observed_quantities = [], [], []
        limitations = ['Only explicitly bound artists are inspected; unbound marks are not covered.',
                       'Units and comparability are declared, not inferred or scientifically validated.',
                       'Identity RGB is compared; opacity, marker shape and size are not compared.',
                       'Colormaps are compared at 256 samples and their under/over/missing colors.']

        def issue(code, message, *, failure=False, **details):
            diagnostics.append({'code': code, 'severity': 'FAIL' if failure else 'WARN',
                                'message': message, **details})

        figures = {getattr(row['artist'], 'figure', None) for row in self._identities + self._quantities}
        for figure in figures - {None}:
            figure.canvas.draw()
        if not self._identities and not self._quantities:
            issue('NO_BINDINGS', 'No artists were supplied; nothing was verified.')
        identity_groups = defaultdict(list)
        identity_artists = defaultdict(set)
        for row in self._identities:
            artist = row['artist']
            try:
                color = _identity_color(artist)
            except ValueError as exc:
                issue('UNSUPPORTED_IDENTITY', str(exc), panel=row['panel'], identity=row['id'])
                continue
            observation = {'panel': row['panel'], 'identity': row['id'], 'color': color}
            observed_identities.append(observation)
            identity_groups[row['id']].append(observation)
            identity_artists[row['id']].add(id(artist))
            if self.identity_colors:
                if row['id'] not in self.identity_colors:
                    issue('UNKNOWN_IDENTITY', 'Identity is absent from the supplied registry.',
                          failure=True, **observation)
                elif color != colors.to_hex(self.identity_colors[row['id']]):
                    issue('IDENTITY_COLOR_MISMATCH', 'Plotted color differs from the supplied identity color.',
                          failure=True, expected=colors.to_hex(self.identity_colors[row['id']]), **observation)
        for identity, rows in identity_groups.items():
            if not self.identity_colors and len(identity_artists[identity]) < 2:
                issue('INSUFFICIENT_IDENTITY_COMPARISON', 'Supply a registry or another panel for this identity.', identity=identity)
            if len({row['color'] for row in rows}) > 1:
                issue('IDENTITY_COLOR_MISMATCH', 'The same identity has different colors across panels.',
                      failure=True, identity=identity, observations=rows)
        quantity_groups = defaultdict(list)
        for row in self._quantities:
            try:
                scale = _quantity_scale(row['artist'])
            except ValueError as exc:
                issue('UNSUPPORTED_SCALE', str(exc), panel=row['panel'], quantity=row['id'])
                continue
            observation = {'panel': row['panel'], 'quantity': row['id'], 'unit': row['unit'], 'scale': scale,
                           'colormap': row['artist'].get_cmap().name}
            observed_quantities.append(observation)
            quantity_groups[row['id']].append((observation, id(row['artist'])))
            if row['id'] not in self.comparable_quantities:
                issue('COMPARABILITY_NOT_DECLARED', 'Scale comparison was skipped for this quantity.',
                      panel=row['panel'], quantity=row['id'])
        for quantity in sorted(self.comparable_quantities):
            pairs = quantity_groups[quantity]
            rows = [item[0] for item in pairs]
            if len({item[1] for item in pairs}) < 2 or len({row['panel'] for row in rows}) < 2:
                issue('INSUFFICIENT_COMPARISON', 'Bind at least two distinct panel artists to compare this quantity.',
                      quantity=quantity)
                continue
            if len({row['unit'] for row in rows}) > 1:
                issue('UNIT_MISMATCH', 'Declared units differ for a quantity marked comparable; no conversion was applied.',
                      failure=True, quantity=quantity, observations=rows)
            if any(row['scale'] != rows[0]['scale'] for row in rows[1:]):
                issue('SCALE_MISMATCH', 'Comparable panels use different normalization, limits or colormaps.',
                      failure=True, quantity=quantity, observations=rows)
        status = 'FAIL' if any(d['severity'] == 'FAIL' for d in diagnostics) else 'PARTIAL' if diagnostics else 'PASS'
        return {'schema': 'cellstyle-figure-set-1', 'status': status, 'diagnostics': diagnostics,
                'identities': observed_identities, 'quantities': observed_quantities,
                'coverage': {'bound_identities': len(self._identities), 'bound_quantities': len(self._quantities),
                             'comparable_quantities': sorted(self.comparable_quantities), 'limitations': limitations}}


def _identity_color(artist):
    if (getattr(artist, 'axes', None) is None or not artist.get_visible()
            or not artist.axes.get_visible()):
        raise ValueError('Identity artist is hidden or is not attached to an axes.')
    if isinstance(artist, PathCollection):
        if not np.isfinite(np.ma.asarray(artist.get_offsets(), dtype=float).filled(np.nan)).all(axis=1).any():
            raise ValueError('Identity scatter has no observations.')
        if artist.get_array() is not None:
            raise ValueError('Scalar-mapped colors cannot verify a constant identity color.')
        rgba = artist.get_facecolors()
        if len(rgba) == 0 or np.any(rgba[:, 3] == 0):
            raise ValueError('Identity face colors are absent or fully transparent.')
        unique = {colors.to_hex(color[:3]) for color in rgba}
        if len(unique) != 1:
            raise ValueError('Identity artist contains multiple face colors; bind a separate artist per identity.')
        return unique.pop()
    if isinstance(artist, Line2D):
        if not len(artist.get_xydata()) or not np.isfinite(artist.get_xydata()).all(axis=1).any():
            raise ValueError('Identity line has no finite observations.')
        if artist.get_alpha() == 0 or colors.to_rgba(artist.get_color())[3] == 0:
            raise ValueError('Identity line is fully transparent.')
        return colors.to_hex(artist.get_color())
    raise ValueError('Only scatter face colors and line colors are supported identity bindings.')


def _quantity_scale(artist):
    if (not isinstance(artist, (PathCollection, AxesImage)) or artist.axes is None
            or not artist.get_visible() or not artist.axes.get_visible()):
        raise ValueError('Bind a visible scalar-colored scatter or image on an axes.')
    if artist.get_array() is None or artist.get_array().size == 0:
        raise ValueError('Artist has no scalar data array; no quantitative color mapping was verified.')
    if artist.get_alpha() is not None and not np.any(np.asarray(artist.get_alpha()) > 0):
        raise ValueError("Quantitative artist is fully transparent.")
    if isinstance(artist, PathCollection):
        offsets = np.ma.asarray(artist.get_offsets(), dtype=float).filled(np.nan)
        if not np.isfinite(offsets).all(axis=1).any():
            raise ValueError("Quantitative scatter has no finite coordinates.")
    if isinstance(artist, AxesImage) and artist.get_array().ndim != 2:
        raise ValueError("Precolored images do not encode a scalar quantity.")
    if not np.isfinite(np.ma.asarray(artist.get_array(), dtype=float).filled(np.nan)).any():
        raise ValueError("No finite scalar observations.")
    norm = artist.norm
    if type(norm) not in (colors.Normalize, colors.LogNorm, colors.TwoSlopeNorm, colors.PowerNorm):
        raise ValueError(f'Normalization {type(norm).__name__} is not supported by this check.')
    if norm.vmin is None or norm.vmax is None or not np.isfinite([norm.vmin, norm.vmax]).all():
        raise ValueError('Scale limits are missing or nonfinite.')
    scale = {'normalization': type(norm).__name__, 'vmin': float(norm.vmin),
             'vmax': float(norm.vmax), 'clip': bool(norm.clip)}
    for parameter in ('vcenter', 'gamma'):
        if hasattr(norm, parameter):
            scale[parameter] = float(getattr(norm, parameter))
    cmap = artist.get_cmap()
    samples = np.concatenate([cmap(np.linspace(0, 1, 256)), cmap([-np.inf, np.inf, np.nan])])
    scale['colormap_sha256'] = hashlib.sha256(samples.astype('<f8').tobytes()).hexdigest()
    return scale

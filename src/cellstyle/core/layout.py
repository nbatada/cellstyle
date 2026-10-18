"""Physical artwork geometry, independent of plotting and identity specs."""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path


def _number(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'nonnegative'}")


def _id(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("IDs must be nonempty strings")


@dataclass(frozen=True)
class PanelSlot:
    id: str
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    # Rectangle relative to the slot, reserved for assembly-owned lettering.
    letter_reserve_mm: tuple | None = None

    def __post_init__(self):
        _id(self.id)
        for key in ('x_mm', 'y_mm', 'width_mm', 'height_mm'):
            _number(getattr(self, key), key, key in ('width_mm', 'height_mm'))
        if self.letter_reserve_mm is not None:
            r = tuple(self.letter_reserve_mm)
            if len(r) != 4:
                raise ValueError('letter reserve requires x, y, width, height')
            for i, v in enumerate(r):
                _number(v, 'letter reserve', i > 1)
            if r[0] + r[2] > self.width_mm or r[1] + r[3] > self.height_mm:
                raise ValueError('letter reserve outside slot')
            object.__setattr__(self, 'letter_reserve_mm', r)


@dataclass(frozen=True)
class FigureLayout:
    id: str
    width_mm: float
    height_mm: float
    slots: tuple[PanelSlot, ...]
    letter_owner: str = 'assembly'
    profile: str = 'custom'

    def __post_init__(self):
        _id(self.id)
        _number(self.width_mm, 'width_mm', True)
        _number(self.height_mm, 'height_mm', True)
        object.__setattr__(self, 'slots', tuple(self.slots))
        if not self.slots or any(not isinstance(s, PanelSlot) for s in self.slots):
            raise ValueError('layout requires PanelSlot records')
        if self.letter_owner not in ('assembly', 'panel'):
            raise ValueError('letter_owner must be assembly or panel')
        if len({s.id for s in self.slots}) != len(self.slots):
            raise ValueError('duplicate panel ID')
        for i, a in enumerate(self.slots):
            if a.x_mm + a.width_mm > self.width_mm or a.y_mm + a.height_mm > self.height_mm:
                raise ValueError(f'panel {a.id} outside page')
            for b in self.slots[:i]:
                if (a.x_mm < b.x_mm + b.width_mm and b.x_mm < a.x_mm + a.width_mm
                        and a.y_mm < b.y_mm + b.height_mm and b.y_mm < a.y_mm + a.height_mm):
                    raise ValueError(f'overlapping panels: {a.id}, {b.id}')
        if self.profile not in ('custom', 'nature-flagship-final-research'):
            raise ValueError('unsupported profile; Cell rules are not verified')
        if self.profile == 'nature-flagship-final-research':
            if not any(abs(self.width_mm - w) < .001 for w in (89, 183)) or self.height_mm > 170:
                raise ValueError('Nature flagship artwork requires width 89/183 mm and height <=170 mm')

    def slot(self, panel_id):
        for slot in self.slots:
            if slot.id == panel_id:
                return slot
        raise ValueError(f'unknown panel: {panel_id}')

    def to_dict(self):
        return {'schema': 'cellstyle-layout-1', **asdict(self)}

    @property
    def sha256(self):
        values = [self.id, f'{self.width_mm:.9f}', f'{self.height_mm:.9f}', self.letter_owner, self.profile]
        for s in self.slots:
            values.extend([s.id, *(f'{v:.9f}' for v in (s.x_mm, s.y_mm, s.width_mm, s.height_mm))])
            values.extend(f'{v:.9f}' for v in s.letter_reserve_mm or ())
            values.append('end-slot')
        payload = ''.join(f'{len(v.encode("utf-8"))}:{v}' for v in values)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def write(self, path):
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + '\n')

    @classmethod
    def read(cls, path):
        def unique(pairs):
            result = {}
            for k, v in pairs:
                if k in result:
                    raise ValueError(f'duplicate JSON key: {k}')
                result[k] = v
            return result
        data = json.loads(Path(path).read_text(), object_pairs_hook=unique)
        if data.pop('schema', None) != 'cellstyle-layout-1':
            raise ValueError('unsupported layout schema')
        data['slots'] = tuple(PanelSlot(**s) for s in data['slots'])
        return cls(**data)

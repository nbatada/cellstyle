"""Persistent, explicit identity colors shared by plots and languages."""
from collections.abc import Mapping
from dataclasses import dataclass, field

import re

import pandas as pd
from matplotlib.colors import is_color_like, to_hex


@dataclass
class ColorRegistry(Mapping):
    entries: dict = field(default_factory=dict)

    def register(self, entity, color, parent=None, level=None, role="identity"):
        if not isinstance(entity, str) or not entity.strip():
            raise ValueError("entity must be a nonempty string")
        if not isinstance(color, str) or not is_color_like(color):
            raise ValueError(f"Invalid color for identity {entity!r}: {color!r}")
        if re.fullmatch(r"C[0-9]+", color):
            color = to_hex(color)
        self.entries[entity] = dict(entity=entity, parent=parent, level=level,
                                    role=role, color=color)

    def __getitem__(self, entity):
        return self.color(entity)

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def color(self, entity):
        return self.entries[entity]["color"]

    def palette(self, entities):
        return [self.color(entity) for entity in entities]

    def to_tsv(self, path):
        pd.DataFrame(self.entries.values(), columns=["entity", "parent", "level", "role", "color"]).to_csv(
            path, sep="\t", index=False)

    @classmethod
    def from_tsv(cls, path):
        data = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
        if not {"entity", "color"} <= set(data.columns):
            raise ValueError("Registry requires entity and color columns")
        if data.entity.duplicated().any():
            raise ValueError("Registry contains duplicate identities")
        registry = cls()
        for row in data.to_dict("records"):
            registry.register(row["entity"], row["color"], row.get("parent") or None,
                              row.get("level") or None, row.get("role") or "identity")
        return registry

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, pandas as pd
import cellstyle as cs
def test_palette(): assert cs.editorial_vivid(5)[0]=="#1764AB"
def test_registry(tmp_path):
 r=cs.ColorRegistry(); r.register("A","#123456"); p=tmp_path/"r.tsv"; r.to_tsv(p); assert cs.ColorRegistry.from_tsv(p).color("A")=="#123456"
def test_distribution():
 df=pd.DataFrame({"g":["A"]*3+["B"]*3,"v":[1,2,3,2,3,4]}); ax=cs.replicate_distribution(df,"g","v",order=["A","B"]); assert ax is not None; plt.close(ax.figure)


def test_registry_preserves_literal_identifiers(tmp_path):
    registry = cs.ColorRegistry()
    for entity in ("NA", "001", "null"):
        registry.register(entity, "#123456")
    path = tmp_path / "identities.tsv"
    registry.to_tsv(path)
    assert cs.ColorRegistry.from_tsv(path).entries == registry.entries


def test_empty_registry_roundtrip(tmp_path):
    registry = cs.ColorRegistry()
    path = tmp_path / "empty.tsv"
    registry.to_tsv(path)
    assert cs.ColorRegistry.from_tsv(path).entries == {}

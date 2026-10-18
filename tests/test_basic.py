import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, pandas as pd
import cellstyle as cs
def test_palette(): assert cs.editorial_vivid(5)[0]=="#1764AB"
def test_registry(tmp_path):
 r=cs.ColorRegistry(); r.register("A","#123456"); p=tmp_path/"r.tsv"; r.to_tsv(p); assert cs.ColorRegistry.from_tsv(p).color("A")=="#123456"
def test_distribution():
 df=pd.DataFrame({"g":["A"]*3+["B"]*3,"v":[1,2,3,2,3,4]}); ax=cs.replicate_distribution(df,"g","v",order=["A","B"]); assert ax is not None; plt.close(ax.figure)

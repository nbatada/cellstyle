from contextlib import contextmanager
import matplotlib as mpl
MODES={"explore":{"font.size":9,"axes.grid":False},"review":{"font.size":9,"axes.grid":False,"axes.spines.top":False,"axes.spines.right":False},"manuscript":{"font.size":8,"axes.grid":False,"axes.spines.top":False,"axes.spines.right":False,"pdf.fonttype":42},"presentation":{"font.size":12,"axes.grid":False}}
BASE={"font.family":"sans-serif","figure.facecolor":"white","axes.facecolor":"white"}
def set_theme(mode="review"):
    if mode not in MODES: raise ValueError(mode)
    mpl.rcParams.update(BASE|MODES[mode])
@contextmanager
def theme_context(mode="review"):
    if mode not in MODES: raise ValueError(mode)
    with mpl.rc_context(BASE|MODES[mode]): yield

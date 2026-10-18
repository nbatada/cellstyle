from contextlib import contextmanager
from contextvars import ContextVar
import matplotlib as mpl
_active_mode = ContextVar("cellstyle_active_mode", default=None)
MODES = {'explore': {'font.size': 9, 'axes.grid': False},
 'review': {'font.size': 9,
            'axes.grid': False,
            'axes.spines.top': False,
            'axes.spines.right': False},
 'manuscript': {'font.size': 8,
                'axes.labelsize': 8,
                'xtick.labelsize': 7,
                'ytick.labelsize': 7,
                'legend.fontsize': 7.5,
                'legend.title_fontsize': 7.5,
                'axes.titlesize': 9,
                'axes.edgecolor': '#202020',
                'axes.labelcolor': '#202020',
                'text.color': '#202020',
                'xtick.color': '#202020',
                'ytick.color': '#202020',
                'axes.linewidth': 0.7,
                'xtick.major.width': 0.7,
                'ytick.major.width': 0.7,
                'axes.grid': False,
                'axes.spines.top': False,
                'axes.spines.right': False,
                'pdf.fonttype': 42},
 'presentation': {'font.size': 12, 'axes.grid': False}}
BASE={"font.family":"sans-serif","figure.facecolor":"white","axes.facecolor":"white"}
def _theme_values(mode):
    if mode not in MODES:
        raise ValueError(mode)
    # Relative native roles must not inherit fixed manuscript sizes when switching intent.
    roles = ("axes.labelsize", "axes.titlesize", "xtick.labelsize", "ytick.labelsize",
             "legend.fontsize", "legend.title_fontsize")
    defaults = {key: mpl.rcParamsDefault[key] for key in roles}
    return BASE | defaults | MODES[mode]

def set_theme(mode="review"):
    if mode not in MODES: raise ValueError(mode)
    mpl.rcParams.update(_theme_values(mode))
    _active_mode.set(mode)
@contextmanager
def theme_context(mode="review"):
    if mode not in MODES: raise ValueError(mode)
    token = _active_mode.set(mode)
    try:
        with mpl.rc_context(_theme_values(mode)): yield
    finally:
        _active_mode.reset(token)

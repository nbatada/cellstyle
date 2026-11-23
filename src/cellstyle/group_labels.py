"""Place identity labels on native Matplotlib axes at the actual render size."""
from collections import Counter

import numpy as np
import pandas as pd
from matplotlib.artist import Artist
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.transforms import IdentityTransform, Bbox


class _GroupLabels(Artist):
    def __init__(self, ax, xy, ids, alternatives, fontsize):
        super().__init__()
        self.axes = ax
        self.set_figure(ax.figure)
        self.set_zorder(5)
        self.xy = xy
        self.ids = ids
        self.alternatives = alternatives
        self.fontsize = fontsize
        self.report = []

    def draw(self, renderer):
        if not self.get_visible():
            return
        ax = self.axes
        points = ax.transData.transform(self.xy)
        visible = np.isfinite(points).all(axis=1) & (
            (points >= ax.bbox.min) & (points <= ax.bbox.max)).all(axis=1)
        points, ids = points[visible], self.ids[visible]
        counts = Counter(ids)
        pt = renderer.points_to_pixels(1)
        occupied = []
        plans = []
        # Count cell centers under candidate boxes using a 1-point occupancy grid.
        # Bound memory for very large exports. Exact counts are recorded afterward.
        bounds = ax.bbox
        nx, ny = np.clip(np.ceil(bounds.size / pt).astype(int), 1, 1024)
        grid, _, _ = np.histogram2d(points[:, 0], points[:, 1], bins=(nx, ny),
                                    range=((bounds.x0, bounds.x1), (bounds.y0, bounds.y1)))
        integral = np.pad(grid.cumsum(axis=0).cumsum(axis=1), ((1,0),(1,0)))

        def under(box):
            b = ((box.get_points() - bounds.min) / bounds.size * (nx,ny))
            lo = np.clip(np.floor(b[0]).astype(int), 0, (nx,ny))
            hi = np.clip(np.ceil(b[1]).astype(int), 0, (nx,ny))
            i,j = lo
            k,l = hi
            return integral[k,l] - integral[i,l] - integral[k,j] + integral[i,j]

        choices = {}
        for identity in sorted(counts, key=lambda key: (counts[key], key)):
            group = points[ids == identity]
            center = np.median(group, axis=0)
            distances = ((group - center)**2).sum(axis=1)
            anchor = group[np.lexsort((group[:,1], group[:,0], distances))[0]]
            choices[identity] = []
            for short, name in enumerate(self.alternatives[identity]):
                text = Text(0, 0, name, fontsize=self.fontsize, color="#202020",
                            horizontalalignment="center", verticalalignment="center",
                            transform=IdentityTransform(), parse_math=False, usetex=False)
                text.set_figure(ax.figure)
                half = text.get_window_extent(renderer).size / 2 + pt
                for dx,dy in ((0,0),(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
                    for gap in ((0,) if dx == dy == 0 else (3,10,20)):
                        target = anchor + (half + gap*pt) * (dx,dy)
                        pos = np.maximum(bounds.min+half,np.minimum(bounds.max-half,target))
                        box = Bbox.from_extents(*(pos-half), *(pos+half))
                        clipping = np.maximum(bounds.min-box.min,0).sum()+np.maximum(box.max-bounds.max,0).sum()
                        travel = np.linalg.norm(np.maximum(np.abs(pos-anchor)-half,0))/pt
                        penalty = under(box) + .25*travel + 2*short
                        choices[identity].append((box,clipping,penalty,travel,anchor,pos,text))
        # Repair early choices after the other labels have positions. Two starts
        # reduce sensitivity to whether a rare or a wide label was placed first.
        def solve(order):
            chosen = {}
            for sequence in (order, order[::-1], order):
                for identity in sequence:
                    others = [a[0] for key,a in chosen.items() if key != identity]
                    def score(option):
                        box,clip,penalty,travel = option[:4]
                        return (clip,sum(box.overlaps(other) for other in others),penalty,travel)
                    chosen[identity] = min(choices[identity], key=score)
            boxes = [a[0] for a in chosen.values()]
            pairs = sum(a.overlaps(b) for i,a in enumerate(boxes) for b in boxes[i+1:])
            return (sum(a[1] for a in chosen.values()),pairs,sum(a[2] for a in chosen.values())),chosen

        order = list(choices)
        wide_first = sorted(order,key=lambda k:-choices[k][0][0].width)
        _,chosen = min((solve(order),solve(wide_first)), key=lambda item:item[0])
        for identity,(box,clip,penalty,travel,anchor,pos,text) in chosen.items():
            text.set_position(pos)
            end = np.clip(anchor,box.min,box.max)
            if np.linalg.norm(end-anchor) > pt:
                leader = Line2D([anchor[0],end[0]], [anchor[1],end[1]], linewidth=.5,
                                color="#606060", transform=IdentityTransform())
                leader.set_figure(ax.figure)
                leader.draw(renderer)
            overlaps = sum(box.overlaps(other) for other in occupied)
            occupied.append(box)
            covered = ((points>=box.min) & (points<=box.max)).all(axis=1).sum()
            plans.append((text, dict(identity=identity, label=text.get_text(), anchor=ax.transData.inverted().transform(anchor).tolist(),
                                     box=box.extents.tolist(), cell_centers_under=int(covered),
                                     leader_length_pt=float(np.linalg.norm(end-anchor)/pt),
                                     overlaps_previous=int(overlaps), outside_panel=bool(clip>1e-6))))
        for text,_ in plans:
            text.draw(renderer)
        self.report = [row for _,row in plans]
        self.stale = False


def label_groups(ax, x, y, groups, *, short_labels=None, fontsize=7):
    """Label visible groups using observed anchors and optional approved alternatives.

    Draw after plotting the cells. The returned artist recalculates positions
    when drawn or resized. After fig.canvas.draw(), inspect artist.report for
    chosen text, collisions, covered cell centers and leader lengths.
    """
    x,y,groups = np.asarray(x,dtype=float),np.asarray(y,dtype=float),np.asarray(groups)
    if any(a.ndim != 1 for a in (x,y,groups)) or not len(x) or len(x)!=len(y) or len(x)!=len(groups):
        raise ValueError("Supply equally sized, nonempty x, y and group vectors")
    if pd.isna(groups).any() or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Coordinates and group identities must be complete")
    if ax.name != "rectilinear" or not np.isfinite(fontsize) or fontsize<=0:
        raise ValueError("Use a rectilinear embedding and a positive font size")
    raw = pd.unique(groups)
    names = [str(v) for v in raw]
    if len(set(names)) != len(names) or any(not name.strip() for name in names):
        raise ValueError("Group labels must be distinct and nonempty")
    aliases = dict(short_labels or {})
    if set(aliases) - set(raw):
        raise ValueError("Short labels must reference observed groups")
    candidates = {str(k):v for k,v in aliases.items()}
    if any(not isinstance(v,str) or not v.strip() for v in candidates.values()):
        raise ValueError("Supply nonempty short labels")
    frequency = Counter(v.casefold().strip() for v in candidates.values())
    reserved = {n.casefold().strip() for n in names}
    alternatives = {name:[name] for name in names}
    for name, alias in candidates.items():
        key = alias.casefold().strip()
        if len(alias)<len(name) and key not in reserved and frequency[key]==1:
            alternatives[name].append(alias)
    artist = _GroupLabels(ax, np.column_stack((x,y)), np.array([str(v) for v in groups]),
                          alternatives, fontsize)
    ax.add_artist(artist)
    return artist

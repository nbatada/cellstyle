import matplotlib as mpl
EDITORIAL_VIVID=["#1764AB","#00A2A5","#E6A700","#D43F3A","#8A4FA3"]
def editorial_vivid(n):
    if n>5: raise ValueError("Built-in palette supports at most five categories; supply an explicit color mapping for more.")
    return EDITORIAL_VIVID[:n]
def positive_cmap(): return mpl.colormaps["Blues"]
def marker_heatmap_cmap(): return mpl.colors.LinearSegmentedColormap.from_list("cellstyle_marker",["#2166AC","#171717","#F4D03F"])
def context_color(): return "#E8E8E8"

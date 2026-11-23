"""Save your first CellStyle plot using synthetic data; no download required.

Run: python examples/first_plot.py [OUTPUT.pdf]
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import cellstyle as cs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=Path('first-plot.pdf'))
    output = parser.parse_args().output
    dose = pd.Series([0, 1, 2, 3, 4], name='Synthetic dose (a.u.)')
    response = pd.Series([1, 1.4, 1.3, 2.1, 2.5], name='Synthetic response (a.u.)')
    ax = cs.pl.scatter(dose, response, output=output)
    plt.close(ax.figure)
    print(f'Saved {output.resolve()}')


if __name__ == '__main__':
    main()

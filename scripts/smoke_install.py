"""Verify editable, local, wheel, and sdist installs in separate clean venvs.

Run after ``python -m build``. Downloads dependencies through pip; does not
publish anything or modify the calling Python environment.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


ROOT = Path(__file__).resolve().parents[1]
SMOKE = r'''
from importlib import metadata, util
from pathlib import Path
import sys

import cellstyle as cs
import matplotlib.pyplot as plt
import pandas as pd

expected, mode, source = sys.argv[1:]
assert cs.__version__ == metadata.version("cellstyle") == expected
assert util.find_spec("scanpy") is None, "Core installation unexpectedly includes Scanpy"
package_path = Path(cs.__file__).resolve()
if mode == "editable":
    assert package_path.is_relative_to(Path(source).resolve() / "src")
else:
    assert package_path.is_relative_to(Path(sys.prefix).resolve())
    assert not package_path.is_relative_to(Path(source).resolve() / "src")
assert metadata.metadata("cellstyle")["License-Expression"] == "MIT"
assert all(hasattr(cs, name) for name in cs.__all__)

data = pd.DataFrame({"group": ["A", "A", "B", "B"], "value": [1, 2, 2, 3]})
with cs.theme_context("review"):
    ax = cs.replicate_distribution(data, "group", "value", order=["A", "B"])
    cs.add_comparisons(ax, [cs.ComparisonResult("A", "B", p_adjusted=0.03)])
    labels = [ax.text(0.5, 2.0, "A"), ax.text(0.5, 2.05, "B")]
    adjusted, _ = cs.repel_labels(labels, ax)
    assert len(adjusted) == 2
    ax.figure.savefig("smoke.png")
    plt.close(ax.figure)
assert Path("smoke.png").stat().st_size > 0
print(f"PASS {mode}: cellstyle {cs.__version__}; {package_path}; Scanpy absent")
print("Resolved dependencies: " + ", ".join(
    f"{name}=={metadata.version(name)}"
    for name in ("matplotlib", "numpy", "pandas", "seaborn", "adjustText")
))
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--modes", nargs="+", choices=("editable", "local", "wheel", "sdist"),
        default=("editable", "local", "wheel", "sdist"),
    )
    args = parser.parse_args()
    expected = (ROOT / "VERSION").read_text().strip()
    dist = args.dist_dir.resolve()
    targets = {
        "editable": ["-e", str(ROOT)],
        "local": [str(ROOT)],
        "wheel": [str(dist / f"cellstyle-{expected}-py3-none-any.whl")],
        "sdist": [str(dist / f"cellstyle-{expected}.tar.gz")],
    }
    for mode in args.modes:
        if mode in ("wheel", "sdist") and not Path(targets[mode][0]).is_file():
            parser.error(f"Missing {targets[mode][0]}; run python -m build first.")

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["MPLBACKEND"] = "Agg"
    env["PYTHONNOUSERSITE"] = "1"
    with tempfile.TemporaryDirectory(prefix="cellstyle-install-") as temporary:
        work = Path(temporary)
        env["MPLCONFIGDIR"] = str(work / "matplotlib")
        for mode in args.modes:
            print(f"Checking {mode} installation", flush=True)
            environment = work / mode
            venv.EnvBuilder(with_pip=True).create(environment)
            python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            subprocess.run(
                [str(python), "-m", "pip", "install", "--disable-pip-version-check", *targets[mode]],
                cwd=work, env=env, check=True,
            )
            subprocess.run([str(python), "-m", "pip", "check"], cwd=work, env=env, check=True)
            subprocess.run(
                [str(python), "-I", "-c", SMOKE, expected, mode, str(ROOT)],
                cwd=work, env=env, check=True,
            )


if __name__ == "__main__":
    main()

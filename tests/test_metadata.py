from importlib.metadata import distribution
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
import cellstyle


def test_installed_checkout_metadata():
    root = Path(__file__).resolve().parents[1]
    metadata = distribution('cellstyle')
    assert metadata.version == cellstyle.__version__ == (root / 'VERSION').read_text().strip()
    requirements = [Requirement(r) for r in metadata.requires]
    assert {canonicalize_name(r.name) for r in requirements if r.marker is None} == {
        'matplotlib', 'numpy', 'pandas', 'seaborn', 'adjusttext'}
    optional = next(r for r in requirements if canonicalize_name(r.name) == 'scanpy')
    assert optional.marker.evaluate({'extra': 'scanpy'})
    assert not optional.marker.evaluate({'extra': ''})
    assert metadata.metadata['License-Expression'] == 'MIT'

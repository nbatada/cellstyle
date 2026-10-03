import inspect

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import cellstyle as cs


def test_v012_public_api():
    assert hasattr(cs, "repel_labels")
    assert hasattr(cs, "categorical_embedding")
    assert hasattr(cs, "focus_embedding")


def test_replicate_distribution_has_point_size():
    sig = inspect.signature(cs.replicate_distribution)
    assert "point_size" in sig.parameters


def test_repel_labels_smoke():
    fig, ax = plt.subplots()
    texts = [
        ax.text(0.5, 0.5, "A"),
        ax.text(0.5, 0.5, "B"),
    ]
    out = cs.repel_labels(texts, ax)
    assert out is not None
    plt.close(fig)

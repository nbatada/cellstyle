import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from cellstyle.annotations import (
    ComparisonResult,
    add_comparisons,
)


def test_comparison_result_prefers_adjusted_p():

    result = ComparisonResult(
        group_a="A",
        group_b="B",
        p=0.01,
        p_adjusted=0.03,
    )

    assert result.display_p() == 0.03


def test_add_comparison_from_dataclass():

    fig, ax = plt.subplots()

    ax.scatter(
        [0, 0, 1, 1],
        [1, 2, 2, 3],
    )

    ax.set_xticks(
        [0, 1],
        ["A", "B"],
    )

    add_comparisons(
        ax,
        [
            ComparisonResult(
                group_a="A",
                group_b="B",
                p=0.016,
                test="Wilcoxon rank-sum",
                observation_unit="patient",
            )
        ],
    )

    assert len(ax.texts) == 1
    assert "0.02" in ax.texts[0].get_text()

    plt.close(fig)


def test_add_multiple_comparisons_stacks():

    fig, ax = plt.subplots()

    ax.set_xticks(
        [0, 1, 2],
        ["A", "B", "C"],
    )

    add_comparisons(
        ax,
        [
            {
                "group_a": "A",
                "group_b": "B",
                "p": 0.031,
            },
            {
                "group_a": "A",
                "group_b": "C",
                "p": 0.004,
            },
        ],
    )

    assert len(ax.texts) == 2

    plt.close(fig)

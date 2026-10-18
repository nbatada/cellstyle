import json
from copy import deepcopy
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from cellstyle.core.semantics import (read_semantic_contract, semantic_fact,
                                      validate_semantics)
from cellstyle.semantic_plot import prepare_semantic_plot


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "tests/fixtures/semantics/base.json"


def base_contract():
    return json.loads(BASE.read_text())


def codes(report):
    return {entry["code"] for entry in report["diagnostics"]}


def test_base_and_read_boundary(tmp_path):
    report = validate_semantics(base_contract(), base_dir=ROOT)
    assert (report["semantic_verdict"], report["label_verdict"]) == ("PASS", "WARN")
    assert "NO_RENDER" in codes(report)
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"a":1,"a":2}')
    with pytest.raises(ValueError, match="DUPLICATE_KEY"):
        read_semantic_contract(duplicate)
    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"value": NaN}')
    with pytest.raises(ValueError, match="NONFINITE_NUMBER"):
        read_semantic_contract(nonfinite)
    nonfinite.write_text('{"value": 1e999}')
    with pytest.raises(ValueError, match="NONFINITE_NUMBER"):
        read_semantic_contract(nonfinite)


def test_conflict_and_schema_validation():
    contract = base_contract()
    claim = deepcopy(contract["labels"][0]["text"]["candidates"][0])
    claim["value"] = "different"
    contract["labels"][0]["text"]["candidates"].append(claim)
    report = validate_semantics(contract, base_dir=ROOT)
    assert "AUTHORITY_CONFLICT" in codes(report)
    assert report["label_verdict"] == "FAIL"
    contract["labels"][0]["bogus"] = 1
    report = validate_semantics(contract, base_dir=ROOT)
    assert report["semantic_verdict"] == report["label_verdict"] == "FAIL"
    assert report["resolved"] is None
    for case in json.loads((ROOT / "tests/fixtures/semantics/cases.json").read_text()):
        kwargs = {key: case[key] for key in ("mode", "rendered", "observed",
                                            "supported_bindings", "actual") if key in case}
        report = validate_semantics(case["contract"], base_dir=ROOT, **kwargs)
        assert report["semantic_verdict"] == case["expected_semantic_verdict"], case["id"]
        assert report["label_verdict"] == case["expected_label_verdict"], case["id"]
        assert set(case["expected_codes"]) <= codes(report), case["id"]


def test_quantity_and_actual_guards():
    contract = base_contract()
    contract["quantities"][0]["requires_denominator"] = True
    report = validate_semantics(contract, base_dir=ROOT,
                                actual={"x.measure": "other"})
    assert {"MISSING_DENOMINATOR", "ACTUAL_MISMATCH"} <= codes(report)
    source = contract["labels"][0]["text"]["candidates"][0]["source"]
    assert semantic_fact(0, source=source)["candidates"][0]["value"] == 0
    unresolved = base_contract()
    unresolved["labels"][0]["original"] = "Original axis text"
    unresolved["labels"][0]["text"]["candidates"][0]["status"] = "PROPOSED"
    report = validate_semantics(unresolved, base_dir=ROOT, rendered=True,
                                observed=[{"binding": "x.title", "role": "axis_title",
                                           "text": "Original axis text"}],
                                supported_bindings=["x.title"])
    assert report["resolved"]["labels"][0]["display_text"] == "Original axis text"
    assert report["resolved"]["labels"][0]["text"]["status"] == "PROPOSED"
    assert report["label_verdict"] == "WARN"
    assert report["coverage"]["verified"] == []
    assert "LABEL_MISMATCH" not in codes(report)


def test_matplotlib_callback_and_existing_object():
    contract = base_contract()

    def draw(resolved):
        fig, ax = plt.subplots()
        ax.set_xlabel(resolved["labels"][0]["text"]["value"])
        return ax

    prepared = prepare_semantic_plot(draw, contract, base_dir=ROOT)
    assert prepared["report"]["coverage"]["verified"] == ["x.title"]
    assert prepared["report"]["label_verdict"] == "PASS"
    existing = prepare_semantic_plot(prepared["plot"], contract, base_dir=ROOT)
    assert existing["plot"] is prepared["plot"]
    assert existing["preflight_before_render"] is False
    prepared["plot"].set_title("internal_left_title", loc="left")
    assert "UNCONTRACTED_LABEL" in codes(prepare_semantic_plot(prepared["plot"], contract,
        mode="MANUSCRIPT_FINAL", base_dir=ROOT)["report"])
    prepared["plot"].set_title("", loc="left")
    prepared["plot"].set_axis_off()
    hidden = prepare_semantic_plot(prepared["plot"], contract, mode="MANUSCRIPT_FINAL", base_dir=ROOT)
    assert "MISSING_LABEL" in codes(hidden["report"]) and "x.title" not in hidden["report"]["coverage"]["verified"]
    plt.close(prepared["plot"].figure)


def test_final_unrendered_and_callback_gate():
    contract = base_contract()
    assert validate_semantics(contract, mode="MANUSCRIPT_FINAL", base_dir=ROOT)["label_verdict"] == "FAIL"
    contract["quantities"][0]["requires_denominator"] = True
    called = []
    result = prepare_semantic_plot(lambda _: called.append(True), contract,
                                   mode="MANUSCRIPT_FINAL", base_dir=ROOT)
    assert called == [] and result["report"]["semantic_verdict"] == "FAIL"
    duplicate = base_contract()
    duplicate_observed = [{"binding": "x.title", "role": "axis_title", "text": "Synthetic embedding 1"}] * 2
    report = validate_semantics(duplicate, mode="MANUSCRIPT_FINAL", base_dir=ROOT,
                                rendered=True, observed=duplicate_observed,
                                supported_bindings=["x.title"])
    assert "DUPLICATE_OBSERVED_BINDING" in codes(report)
    assert report["label_verdict"] == "FAIL"

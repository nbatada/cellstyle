"""Resolve declared figure semantics without inventing scientific facts."""

from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import re
from urllib.parse import urlparse


_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas/cellstyle-semantic-1.schema.json"
_NUMERIC_TICK = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?%?$")
_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _schema():
    packaged = Path(__file__).resolve().parents[1] / "data/cellstyle-semantic-1.schema.json"
    return json.loads((packaged if packaged.exists() else _SCHEMA_PATH).read_text())


def semantic_fact(value=None, status="KNOWN", source=None):
    if source is None:
        raise ValueError("SOURCE_REQUIRED: semantic_fact needs an explicit source")
    return {"candidates": [{"status": status, "value": value, "source": deepcopy(source)}]}


def semantic_contract(identities=None, quantities=None, labels=None, statistics=None, caption=None):
    return {
        "schema_version": "cellstyle-semantic-1",
        "identities": deepcopy([] if identities is None else identities),
        "quantities": deepcopy([] if quantities is None else quantities),
        "labels": deepcopy([] if labels is None else labels),
        "statistics": deepcopy([] if statistics is None else statistics),
        "caption": deepcopy({} if caption is None else caption),
    }


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"DUPLICATE_KEY: {key}")
        result[key] = value
    return result


def read_semantic_contract(path):
    try:
        return json.loads(Path(path).read_text(), object_pairs_hook=_unique_pairs,
                          parse_float=lambda value: _finite_json_float(value),
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"NONFINITE_NUMBER: {value}")))
    except json.JSONDecodeError as exc:
        raise ValueError(f"INVALID_JSON: {exc}") from exc


def _finite_json_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"NONFINITE_NUMBER: {value}")
    return number


def _matches_type(value, kind):
    return {
        "object": lambda: isinstance(value, dict),
        "array": lambda: isinstance(value, list),
        "string": lambda: isinstance(value, str),
        "boolean": lambda: type(value) is bool,
        "null": lambda: value is None,
        "number": lambda: type(value) in (int, float) and math.isfinite(value),
    }[kind]()


def _diagnostic(diagnostics, code, severity, path, message):
    diagnostics.append({"code": code, "severity": severity, "path": path, "message": message})


def _validate_schema(value, rule, path, schema, diagnostics):
    if "$ref" in rule:
        rule = schema["$defs"][rule["$ref"].split("/")[-1]]
    kinds = rule.get("type", [])
    kinds = [kinds] if isinstance(kinds, str) else kinds
    if kinds and not any(_matches_type(value, kind) for kind in kinds):
        code = "NONFINITE_NUMBER" if type(value) is float and not math.isfinite(value) else "INVALID_TYPE"
        _diagnostic(diagnostics, code, "FAIL", path, f"Expected {kinds}")
        return
    if "enum" in rule and value not in rule["enum"]:
        _diagnostic(diagnostics, "UNSUPPORTED_SCHEMA_VERSION" if path == "$.schema_version" else "INVALID_VALUE", "FAIL", path, "Value outside schema enum")
    if isinstance(value, str) and len(value) < rule.get("minLength", 0):
        _diagnostic(diagnostics, "INVALID_VALUE", "FAIL", path, "String too short")
    if isinstance(value, list):
        if len(value) < rule.get("minItems", 0):
            _diagnostic(diagnostics, "INVALID_VALUE", "FAIL", path, "Array too short")
        if "items" in rule:
            for index, item in enumerate(value):
                _validate_schema(item, rule["items"], f"{path}[{index}]", schema, diagnostics)
    if isinstance(value, dict):
        for key in rule.get("required", []):
            if key not in value:
                _diagnostic(diagnostics, "MISSING_FIELD", "FAIL", f"{path}.{key}", "Required field missing")
        if rule.get("additionalProperties") is False:
            for key in value.keys() - rule.get("properties", {}).keys():
                _diagnostic(diagnostics, "UNKNOWN_FIELD", "FAIL", f"{path}.{key}", "Unknown field")
        for key, child in rule.get("properties", {}).items():
            if key in value:
                _validate_schema(value[key], child, f"{path}.{key}", schema, diagnostics)


def _local_reference(reference, base_dir):
    if not reference or urlparse(reference).scheme or reference.startswith("//"):
        return False
    return (Path(base_dir) / reference).is_file()


def _verdict(diagnostics, area):
    severities = [d["severity"] for d in diagnostics if d.get("area") == area]
    return "FAIL" if "FAIL" in severities else "WARN" if "WARN" in severities else "PASS"


def validate_semantics(contract, mode="ANALYSIS_RESULT", observed=None, rendered=False,
                       supported_bindings=None, actual=None, base_dir="."):
    if mode not in ("ANALYSIS_RESULT", "MANUSCRIPT_FINAL"):
        raise ValueError("INVALID_MODE: expected ANALYSIS_RESULT or MANUSCRIPT_FINAL")
    schema = _schema()
    diagnostics = []
    _validate_schema(contract, schema, "$", schema, diagnostics)
    coverage = {"rendered": bool(rendered), "expected": [], "verified": [],
                "unsupported": [], "missing": [], "unexpected": []}

    def add(code, severity, path, message, area="semantic"):
        _diagnostic(diagnostics, code, severity, path, message)
        diagnostics[-1]["area"] = area

    def finish(resolved):
        for item in diagnostics:
            item.pop("area", None)
        semantic = _verdict(annotated, "semantic")
        label = _verdict(annotated, "label")
        return {"schema_version": schema["properties"]["schema_version"]["enum"][0],
                "semantic_verdict": semantic, "label_verdict": label,
                "diagnostics": diagnostics, "resolved": resolved, "coverage": coverage,
                "manuscript_ready": False, "submission_ready": False,
                "inspection_scope": "native text only"}

    if diagnostics:
        for item in diagnostics:
            item["area"] = "semantic"
        annotated = deepcopy(diagnostics)
        result = finish(None)
        result["label_verdict"] = "FAIL"
        return result

    priority = {kind: index for index, kind in enumerate(schema["x-cellstyle"]["authority_priority"])}
    resolved = deepcopy(contract)

    def resolve(fact, path, area, field):
        claims = fact["candidates"]
        best = min(priority[c["source"]["kind"]] for c in claims)
        top = [c for c in claims if priority[c["source"]["kind"]] == best]
        signatures = {(c["status"], json.dumps(c["value"], sort_keys=True)) for c in top}
        if len(signatures) != 1:
            add("AUTHORITY_CONFLICT", "FAIL", path, "Highest priority claims disagree", area)
            return None
        winner = min(top, key=lambda c: (c["source"]["reference"], c["source"]["revision"],
                                         json.dumps(c, sort_keys=True)))
        if any((c["status"], json.dumps(c["value"], sort_keys=True)) not in signatures for c in claims):
            add("LOWER_PRIORITY_CONFLICT", "WARN", path, "Lower priority claim differs", area)
        source = winner["source"]
        unresolved = (not source["approved"] or source["kind"] in ("unknown", "unapproved_proposal")
                      or not source["reference"].strip() or not source["revision"].strip()
                      or winner["status"] in ("UNKNOWN", "PROPOSED"))
        if unresolved:
            add("UNRESOLVED_FACT", "FAIL" if mode == "MANUSCRIPT_FINAL" else "WARN", path,
                "Fact has no approved resolved authority", area)
        if not _local_reference(source["reference"], base_dir):
            add("UNRESOLVED_SOURCE", "FAIL" if mode == "MANUSCRIPT_FINAL" else "WARN", path,
                "Source reference is not a local file", area)
        status, value = winner["status"], winner["value"]
        valid = (status == "KNOWN" and value is not None and value != "") or (
            status == "NOT_APPLICABLE" and value is None and source["approved"])
        if status == "KNOWN":
            valid = valid and (type(value) in (int, float) and value >= 0 and value == int(value) if field == "independent_n"
                               else isinstance(value, str) and bool(value.strip()))
        if not valid and status not in ("UNKNOWN", "PROPOSED"):
            add("INVALID_FACT_VALUE", "FAIL", path, "Invalid value for declared status or field", area)
        if field == "color" and status == "KNOWN" and isinstance(value, str) and not _COLOR.fullmatch(value):
            add("INVALID_FACT_VALUE", "FAIL", path, "Color must be #RRGGBB", area)
        resolved_claim = deepcopy(winner)
        if field == "color" and status == "KNOWN" and isinstance(value, str) and _COLOR.fullmatch(value):
            resolved_claim["value"] = value.upper()
        return resolved_claim

    fact_fields = {"identities": ("label", "color"),
                   "quantities": tuple(schema["x-cellstyle"]["quantity_fields"]),
                   "labels": ("text",), "statistics": ("text",)}
    unresolved_label_bindings = set()
    for section, fields in fact_fields.items():
        for index, item in enumerate(resolved[section]):
            for field in fields:
                item[field] = resolve(item[field], f"$.{section}[{index}].{field}",
                                      "label" if section == "labels" else "semantic", field)
            if section == "labels":
                claim = item["text"]
                source = claim["source"] if claim else None
                approved_known = bool(claim and claim["status"] == "KNOWN" and source["approved"]
                                      and source["kind"] not in ("unknown", "unapproved_proposal")
                                      and source["reference"].strip() and source["revision"].strip()
                                      and _local_reference(source["reference"], base_dir))
                item["display_text"] = claim["value"] if approved_known else item.get("original")
                if not approved_known:
                    unresolved_label_bindings.add(item["binding"])
    for field in schema["x-cellstyle"]["final_caption_fields"]:
        resolved["caption"][field] = resolve(resolved["caption"][field], f"$.caption.{field}",
                                              "semantic", field)

    def check_ids(section, field):
        seen = set()
        for index, item in enumerate(resolved[section]):
            key = item[field]
            if key in seen:
                add("DUPLICATE_ID", "FAIL", f"$.{section}[{index}].{field}", "Duplicate identifier",
                    "label" if section == "labels" else "semantic")
            seen.add(key)

    for section, field in (("identities", "id"), ("quantities", "id"),
                           ("statistics", "id"), ("labels", "element_id"), ("labels", "binding")):
        check_ids(section, field)
    colors = {}
    for index, item in enumerate(resolved["identities"]):
        claim = item["color"]
        if claim and claim["status"] == "KNOWN" and isinstance(claim["value"], str):
            color = claim["value"].upper()
            if color in colors and colors[color] != item["id"]:
                add("COLOR_CONFLICT", "FAIL", f"$.identities[{index}].color", "Color shared by identities")
            colors[color] = item["id"]
    quantity_ids = {item["id"] for item in resolved["quantities"]}
    stats = {item["id"]: item for item in resolved["statistics"]}
    for index, item in enumerate(resolved["quantities"]):
        for field, code in (("unit", "MISSING_UNITS"), ("transform", "MISSING_TRANSFORM")):
            if item[field] is None or item[field]["status"] in ("UNKNOWN", "PROPOSED"):
                add(code, "FAIL" if mode == "MANUSCRIPT_FINAL" else "WARN",
                    f"$.quantities[{index}].{field}", f"{field} unresolved")
        denom = item["denominator"]
        if item["requires_denominator"] and (denom is None or denom["status"] != "KNOWN"
                                              or not isinstance(denom["value"], str) or not denom["value"].strip()):
            add("MISSING_DENOMINATOR", "FAIL", f"$.quantities[{index}].denominator", "Required denominator missing")
    for index, item in enumerate(resolved["labels"]):
        if item["quantity_id"] and item["quantity_id"] not in quantity_ids:
            add("UNKNOWN_REFERENCE", "FAIL", f"$.labels[{index}].quantity_id", "Unknown quantity", "label")
        if item["statistic_id"]:
            statistic = stats.get(item["statistic_id"])
            if statistic is None:
                add("UNKNOWN_REFERENCE", "FAIL", f"$.labels[{index}].statistic_id", "Unknown statistic", "label")
            else:
                if item["context"] != statistic["context"]:
                    add("STATISTIC_CONTEXT_MISMATCH", "FAIL", f"$.labels[{index}].context", "Statistic context differs", "label")
                if item["text"] and statistic["text"] and item["text"]["value"] != statistic["text"]["value"]:
                    add("STATISTIC_TEXT_MISMATCH", "FAIL", f"$.labels[{index}].text", "Statistic text differs", "label")
    source_claim = resolved["caption"]["data_source"]
    if source_claim is None or source_claim["status"] != "KNOWN" or not isinstance(source_claim["value"], str) or not _local_reference(source_claim["value"], base_dir):
        add("DATA_SOURCE_UNRESOLVED", "FAIL" if mode == "MANUSCRIPT_FINAL" else "WARN", "$.caption.data_source", "Data source is not a local file")
    for binding, value in (actual or {}).items():
        try:
            quantity_id, field = binding.split(".", 1)
            claim = next(q[field] for q in resolved["quantities"] if q["id"] == quantity_id)
        except (ValueError, KeyError, StopIteration):
            add("UNKNOWN_REFERENCE", "FAIL", f"$.actual.{binding}", "Actual quantity field is unknown")
            continue
        if claim is None or claim["value"] != value:
            add("ACTUAL_MISMATCH", "FAIL", f"$.actual.{binding}", "Actual value differs from declaration")

    expected = {item["binding"]: item for item in resolved["labels"]}
    coverage["expected"] = sorted(expected)
    if rendered:
        observed_map = {}
        for index, seen in enumerate(observed or []):
            binding = seen["binding"]
            if binding in observed_map:
                add("DUPLICATE_OBSERVED_BINDING", "FAIL", f"$.observed[{index}].binding",
                    "Native collection repeated a binding", "label")
            else:
                observed_map[binding] = seen
        supported = set(observed_map) if supported_bindings is None else set(supported_bindings)
        for binding, item in expected.items():
            if binding not in supported:
                coverage["unsupported"].append(binding)
                add("UNSUPPORTED_SURFACE", "FAIL" if mode == "MANUSCRIPT_FINAL" and item["required"] else "WARN",
                    f"$.labels.{binding}", "Native label surface could not be inspected", "label")
            elif binding not in observed_map or not str(observed_map[binding].get("text", "")):
                coverage["missing"].append(binding)
                add("MISSING_LABEL", "FAIL" if mode == "MANUSCRIPT_FINAL" and item["required"] else "WARN",
                    f"$.labels.{binding}", "Declared label absent from rendered plot", "label")
            else:
                seen = observed_map[binding]
                good = True
                declared = item["display_text"]
                if binding not in unresolved_label_bindings and seen.get("text") != declared:
                    add("LABEL_MISMATCH", "FAIL",
                        f"$.labels.{binding}", "Rendered text differs", "label")
                    good = False
                if seen.get("role") != item["role"]:
                    add("ROLE_MISMATCH", "FAIL", f"$.labels.{binding}", "Rendered role differs", "label")
                    good = False
                if item["statistic_id"] and any(item["context"].values()) and seen.get("context") != item["context"]:
                    add("STATISTIC_CONTEXT_MISMATCH", "FAIL", f"$.labels.{binding}", "Rendered statistic context unverified", "label")
                    good = False
                if good and binding not in unresolved_label_bindings:
                    coverage["verified"].append(binding)
        for binding, seen in observed_map.items():
            if binding in expected or not str(seen.get("text", "")):
                continue
            if seen.get("role") in ("axis_tick", "colorbar_tick") and _NUMERIC_TICK.fullmatch(str(seen["text"])):
                continue
            coverage["unexpected"].append(binding)
            add("UNCONTRACTED_LABEL", "FAIL" if mode == "MANUSCRIPT_FINAL" else "WARN",
                f"$.observed.{binding}", "Visible native text has no declaration", "label")
    else:
        add("NO_RENDER", "FAIL" if mode == "MANUSCRIPT_FINAL" else "WARN", "$", "No native render inspected", "label")
    for key in ("verified", "unsupported", "missing", "unexpected"):
        coverage[key].sort()
    annotated = deepcopy(diagnostics)
    return finish(resolved)

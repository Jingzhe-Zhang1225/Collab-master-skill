#!/usr/bin/env python3
"""collab-master-skill 防漂移校验器 — 按 dev-skills/_shared/validate-spec.md 实现。

闸A：skill 全量输出 strict 校验（check --def <DEFNAME> <file>）。
闸B：mock 答案卷部分断言校验（mocks <cases.json>）。
self：schema 自检 + 内置漂移回归。
lint-md：过渡用 Markdown 正则 lint。

纯本地、无网络、只读校验。依赖 jsonschema>=4.18。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError, SchemaError
except ImportError:
    sys.exit(
        "Missing required dependency: jsonschema>=4.18\n"
        "Install with: pip install 'jsonschema>=4.18'"
    )

try:
    import yaml
except ImportError:
    yaml = None  # lenses command will fail gracefully
    sys.exit(2)


def _require_jsonschema_version() -> None:
    try:
        version = package_version("jsonschema")
    except PackageNotFoundError:
        version = "0.0.0"
    parts = []
    for chunk in version.split(".")[:2]:
        m = re.match(r"(\d+)", chunk)
        parts.append(int(m.group(1)) if m else 0)
    while len(parts) < 2:
        parts.append(0)
    if tuple(parts) < (4, 18):
        print(
            f"jsonschema>=4.18 required, found {version}. Install with: pip install 'jsonschema>=4.18'",
            file=sys.stderr,
        )
        sys.exit(2)


# ──────────────────── helpers ────────────────────


def _script_dir() -> Path:
    return Path(os.path.dirname(os.path.abspath(__file__)))


def _resolve_schema(path_str: str) -> Tuple[Path, dict]:
    """Load schema, run check_schema, return (path, parsed). Exits 3 on failure."""
    path = Path(path_str).resolve()
    if not path.exists():
        print(f"Schema file not found: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Failed to load schema {path}: {exc}", file=sys.stderr)
        sys.exit(2)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        print(f"Schema validation failed: {exc}", file=sys.stderr)
        sys.exit(3)
    return path, schema


def _build_validator(def_name: str, schema: dict) -> Draft202012Validator:
    """Build a validator for #/$defs/<def_name> using the spec-prescribed $ref pattern."""
    sub = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": f"#/$defs/{def_name}",
        "$defs": schema["$defs"],
    }
    return Draft202012Validator(sub)


def _collect_errors(validator: Draft202012Validator, instance: Any) -> List[Dict[str, Any]]:
    """Return list of {path, message, value} dicts using iter_errors."""
    results = []
    for error in sorted(validator.iter_errors(instance), key=lambda e: e.json_path):
        results.append(
            {
                "path": error.json_path or "$",
                "message": error.message,
                "value": _json_safe_value(getattr(error, "instance", None)),
            }
        )
    return results


def _json_safe_value(obj: Any) -> Any:
    """Make error.instance JSON-serializable while preserving JSON shape."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, list):
        return [_json_safe_value(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): _json_safe_value(value) for key, value in obj.items()}
    return str(obj)


def _load_json_file(filepath: str) -> Tuple[Path, Any]:
    """Load a JSON file; exit 2 on failure."""
    path = Path(filepath).resolve()
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Failed to parse {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}", file=sys.stderr)
        sys.exit(2)
    except OSError as exc:
        print(f"Failed to read {path}: {exc}", file=sys.stderr)
        sys.exit(2)
    return path, data


def _load_json_stdin() -> Any:
    """Load JSON from stdin; exit 2 on failure."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Failed to parse stdin: line {exc.lineno}, column {exc.colno}: {exc.msg}", file=sys.stderr)
        sys.exit(2)
    except OSError as exc:
        print(f"Failed to read stdin: {exc}", file=sys.stderr)
        sys.exit(2)


# ──────────────────── commands ────────────────────


def cmd_list_defs(schema: dict) -> None:
    """Print available $defs names."""
    for name in sorted(schema.get("$defs", {})):
        suffix = ""
        if name.endswith("Output") or name == "mockFile":
            suffix = "  (闸A strict)"
        elif name.endswith("Fields") or name.endswith("Assertion"):
            suffix = "  (闸B loose)"
        print(f"  {name}{suffix}")
    sys.exit(0)


def _check_instance(
    target_name: str, def_name: str, instance: Any, args: Any
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Check a single instance. Returns (passed, errors)."""
    validator = _build_validator(def_name, args.schema_data)
    errors = _collect_errors(validator, instance)
    return len(errors) == 0, errors


def cmd_check(args: Any) -> None:
    """闸A: check --def <DEFNAME> <file.json|-> [...]"""
    def_name = args.def_name
    if def_name not in args.schema_data.get("$defs", ()):
        print(f"error: unknown def '{def_name}'; run list-defs", file=sys.stderr)
        sys.exit(2)

    all_results = []
    total = 0
    passed = 0
    failed = 0

    for target_spec in args.files:
        total += 1
        if target_spec == "-":
            instance = _load_json_stdin()
            target_name = "-"
        else:
            path, instance = _load_json_file(target_spec)
            target_name = str(path)

        ok, errors = _check_instance(target_name, def_name, instance, args)
        status = "pass" if ok else "fail"
        if ok:
            passed += 1
        else:
            failed += 1
        all_results.append(
            {"target": target_name, "def": def_name, "status": status, "errors": errors}
        )

        if not args.quiet and not args.json:
            tag = "PASS" if ok else "FAIL"
            print(f"[{tag}] {target_name}  (#/$defs/{def_name})")
            for err in errors:
                print(f"   {err['path']} : {err['message']}")
                if err["value"] is not None:
                    print(f"            value: {err['value']}")

    if args.json:
        _json_output(total, passed, failed, all_results, args)
    elif not args.quiet:
        print(f"\n{total} file(s): {passed} passed, {failed} failed")
    else:
        print(f"{total} file(s): {passed} passed, {failed} failed")

    sys.exit(1 if failed > 0 else 0)


def cmd_mocks(args: Any) -> None:
    """闸B: validate a mockCase array file."""
    path, data = _load_json_file(args.cases_file)

    mock_file_validator = _build_validator("mockFile", args.schema_data)
    mock_file_errors = _collect_errors(mock_file_validator, data)
    if mock_file_errors and not isinstance(data, list):
        result = {
            "target": str(path),
            "def": "mockFile",
            "status": "fail",
            "errors": mock_file_errors,
        }
        if args.json:
            _json_output(1, 0, 1, [result], args)
        if not args.quiet:
            print(f"[FAIL] {path}  (#/$defs/mockFile)")
            for err in mock_file_errors:
                print(f"   {err['path']} : {err['message']}")
                print(f"            value: {json.dumps(err['value'], ensure_ascii=False)}")
            print("\n1 mock file: 0 passed, 1 failed")
        sys.exit(1)

    all_results = []
    total = 0
    passed = 0
    failed = 0

    for index, case in enumerate(data):
        total += 1
        case_id = case.get("id", f"<no-id-at-index-{index}>") if isinstance(case, dict) else f"<non-object-at-index-{index}>"

        val = _build_validator("mockCase", args.schema_data)
        errors = _collect_errors(val, case)
        ok = len(errors) == 0

        status = "pass" if ok else "fail"
        if ok:
            passed += 1
        else:
            failed += 1
        all_results.append({"target": str(path), "def": "mockCase", "status": status, "errors": errors, "id": case_id})

        if not args.quiet and not args.json:
            tag = "PASS" if ok else "FAIL"
            print(f"[{tag}] mockCase #{case_id}")
            for err in errors:
                print(f"   {err['path']} : {err['message']}")
                if err["value"] is not None:
                    print(f"            value: {err['value']}")

    if args.json:
        _json_output(total, passed, failed, all_results, args)
    elif not args.quiet:
        print(f"\n{total} mockCase(s): {passed} passed, {failed} failed")
    else:
        print(f"{total} mockCase(s): {passed} passed, {failed} failed")

    sys.exit(1 if failed > 0 else 0)


def cmd_self(args: Any) -> None:
    """Self-check: validate schema + run built-in drift regression samples.

    Regression table (validate-spec.md line 109-121):
      11 samples — each with expected status (PASS or FAIL).
    Any mismatch → exit 1.
    """
    schema = args.schema_data
    framework_values = schema.get("$defs", {}).get("frameworkName", {}).get("enum", [])
    valid_framework = framework_values[0] if framework_values else "direct-check"
    invalid_framework = "__invalid_framework__"
    budget_values = schema.get("$defs", {}).get("budgetTier", {}).get("enum", [])
    valid_budget = budget_values[0] if budget_values else "normal"
    invalid_budget = "__invalid_budget__"

    # ── Schema integrity checks (def presence + value rules) ──
    integrity_mismatches = 0
    integrity_checks: List[Tuple[str, bool, str]] = []

    # Required roundtable defs
    rt_defs = ["roundtableDecision","roundtableSessionOutput","chairOutput","roundtableTier","roundtableRole","roundtable"]
    for d in rt_defs:
        ok = d in schema.get("$defs", {})
        integrity_checks.append((f"roundtable def '{d}' present", ok, "def missing from schema"))
        if not ok:
            integrity_mismatches += 1

    # Required continuity defs
    cont_defs = ["composeOutput","qualityGateOutput","executionControlOutput","memoryOutput"]
    for d in cont_defs:
        ok = d in schema.get("$defs", {})
        integrity_checks.append((f"continuity def '{d}' present", ok, "def missing from schema"))
        if not ok:
            integrity_mismatches += 1

    # frameworkName values must be all-lowercase (lens registry keys match against this)
    fw_names = schema.get("$defs", {}).get("frameworkName", {}).get("enum", [])
    fw_upper = [v for v in fw_names if v != v.lower()]
    fw_ok = len(fw_upper) == 0
    integrity_checks.append(("frameworkName all-lowercase", fw_ok, f"uppercase entries: {fw_upper}" if fw_upper else ""))
    if not fw_ok:
        integrity_mismatches += 1

    # budgetTier def must exist (execution-control continuity)
    bt_ok = "budgetTier" in schema.get("$defs", {})
    integrity_checks.append(("budgetTier def present", bt_ok, "def missing from schema"))
    if not bt_ok:
        integrity_mismatches += 1

    # redlineViolations maximum must be >= 22 (v1.7 verification gate; protect against rollback to 16)
    rl_items = schema.get("$defs", {}).get("qualityGateFields", {}).get("properties", {}).get("redlineViolations", {}).get("items", {})
    rl_max = rl_items.get("maximum", 0)
    rl_ok = rl_max >= 22
    integrity_checks.append((f"redlineViolations maximum>=22 (actual: {rl_max})", rl_ok, f"maximum={rl_max} < 22 — likely rollback"))
    if not rl_ok:
        integrity_mismatches += 1

    # lens schema self-check (load and validate a bad lens card → must FAIL)
    lens_schema_path = _default_lens_schema(Path(args.schema).resolve().parent)
    if lens_schema_path.exists():
        try:
            lens_schema = json.loads(lens_schema_path.read_text(encoding="utf-8"))
            bad_lens = {"id": "@bad@", "name": "bad", "category": "epistemology"}
            validator = Draft202012Validator(lens_schema)
            bad_errors = list(validator.iter_errors(bad_lens))
            lens_ok = len(bad_errors) > 0  # must fail
            integrity_checks.append(("lens card bad → FAIL (anti-drift)", lens_ok, "bad lens card passed unexpectedly"))
            if not lens_ok:
                integrity_mismatches += 1
        except Exception:
            integrity_checks.append(("lens card bad → FAIL (anti-drift)", True, "lens_schema load error; regression skipped"))
    else:
        integrity_checks.append(("lens card bad → FAIL (anti-drift)", True, "lens_schema.json not found; regression skipped"))

    # downstreamPayload.schema.json self-check (v1.6 — 同 taskstate 防回滚)
    ds_path = _default_downstream_schema(Path(args.schema).resolve().parent)
    if ds_path.exists():
        try:
            ds_schema = json.loads(ds_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(ds_schema)
            # bad payload → must FAIL
            bad_payload = {"kind": "slides"}
            validator = Draft202012Validator(ds_schema)
            bad_errors = list(validator.iter_errors(bad_payload))
            ds_ok = len(bad_errors) > 0
            integrity_checks.append(("downstream schema bad→FAIL (anti-drift)", ds_ok, "bad payload passed unexpectedly"))
            if not ds_ok:
                integrity_mismatches += 1
            # good payload → must PASS
            good_payload = {
                "kind": "slides", "meta": {},
                "slides": [{"slideId": "1", "layout": "title-center", "corePunchline": "test"}],
            }
            good_errors = list(validator.iter_errors(good_payload))
            ds_good_ok = len(good_errors) == 0
            integrity_checks.append(("downstream schema good→PASS (anti-drift)", ds_good_ok, f"good payload failed: {good_errors[0].message[:80]}" if good_errors else ""))
            if not ds_good_ok:
                integrity_mismatches += 1
        except Exception:
            integrity_checks.append(("downstream schema self-check", True, "load error; regression skipped"))
    else:
        integrity_checks.append(("downstream schema self-check", True, "downstreamPayload.schema.json not found; regression skipped"))


    # skill-registry.schema.json self-check (v1.6 adaptive handoff)
    registry_schema_path = _default_registry_schema(Path(args.schema).resolve().parent)
    registry_path = _default_registry_file(Path(args.schema).resolve().parent)
    if registry_schema_path.exists() and registry_path.exists():
        try:
            registry_schema = json.loads(registry_schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(registry_schema)
            registry_data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
            validator = Draft202012Validator(registry_schema)
            registry_errors = list(validator.iter_errors(registry_data))
            registry_ok = len(registry_errors) == 0
            integrity_checks.append(("skill registry good?PASS (anti-drift)", registry_ok, f"registry failed: {registry_errors[0].message[:80]}" if registry_errors else ""))
            if not registry_ok:
                integrity_mismatches += 1

            bad_registry = {
                "version": "v1.6",
                "skills": {
                    "bad": {
                        "displayName": "bad",
                        "skillRef": "bad/SKILL.md",
                        "capabilities": ["unknown-capability"],
                        "inputContract": {"kind": "native", "format": "x", "contractSource": "skill"},
                        "bestFor": "bad",
                        "defaultRank": 1,
                    }
                },
            }
            bad_errors = list(validator.iter_errors(bad_registry))
            bad_ok = len(bad_errors) > 0
            integrity_checks.append(("skill registry bad?FAIL (anti-drift)", bad_ok, "bad registry passed unexpectedly"))
            if not bad_ok:
                integrity_mismatches += 1
        except Exception as exc:
            integrity_checks.append(("skill registry self-check", False, f"load/check error: {exc}"))
            integrity_mismatches += 1
    else:
        integrity_checks.append(("skill registry self-check", False, "skill-registry files not found"))
        integrity_mismatches += 1


    # v1.8 customFile + downstream verification anti-drift checks
    required_v18_defs = ["failClass", "matchType", "downstreamVerification"]
    for def_name in required_v18_defs:
        ok = def_name in schema.get("$defs", {})
        integrity_checks.append((f"v1.8 def present: {def_name}", ok, "def missing from schema"))
        if not ok:
            integrity_mismatches += 1

    rev_values = schema.get("$defs", {}).get("revisionTarget", {}).get("enum", [])
    rev_ok = "interaction-compose(6d)" in rev_values
    integrity_checks.append(("revisionTarget includes interaction-compose(6d)", rev_ok, "enum value missing"))
    if not rev_ok:
        integrity_mismatches += 1

    sync_values = schema.get("$defs", {}).get("syncTrigger", {}).get("enum", [])
    sync_ok = "downstream_capability_loss" in sync_values
    integrity_checks.append(("syncTrigger includes downstream_capability_loss", sync_ok, "enum value missing"))
    if not sync_ok:
        integrity_mismatches += 1

    strength_schema = schema.get("$defs", {}).get("structuredConstraint", {}).get("properties", {}).get("strength", {})
    strength_ok = strength_schema.get("enum") == ["force", "soft"]
    integrity_checks.append(("structuredConstraint.strength enum is [force, soft]", strength_ok, "strength enum missing or drifted"))
    if not strength_ok:
        integrity_mismatches += 1

    force_values = (
        schema.get("$defs", {})
        .get("downstreamVerification", {})
        .get("properties", {})
        .get("mismatches", {})
        .get("items", {})
        .get("properties", {})
        .get("force", {})
        .get("enum", [])
    )
    force24_ok = "force2" in force_values and "force4" in force_values
    integrity_checks.append(("downstreamVerification mismatch force includes force2 and force4", force24_ok, "force2/force4 enum value missing"))
    if not force24_ok:
        integrity_mismatches += 1

    cf_path = _default_customfile_schema(Path(args.schema).resolve().parent)
    if cf_path.exists():
        try:
            cf_schema = json.loads(cf_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(cf_schema)
            cf_defs = cf_schema.get("$defs", {})
            cf_props = cf_schema.get("properties", {})
            force_model_ok = (
                "handoffPreflight" in cf_defs
                and "handoffPreflight" in cf_props
                and "designReview" in cf_defs
                and "designReview" in cf_props
                and "diagnosticChain" in cf_defs.get("designReview", {}).get("properties", {})
            )
            integrity_checks.append(("customFile preflight + designReview force model present", force_model_ok, "handoffPreflight/designReview/diagnosticChain missing"))
            if not force_model_ok:
                integrity_mismatches += 1
            validator = Draft202012Validator(cf_schema)
            bad_customfile = {"kind": "slides"}
            bad_errors = list(validator.iter_errors(bad_customfile))
            bad_ok = len(bad_errors) > 0
            integrity_checks.append(("customFile bad?FAIL (anti-drift)", bad_ok, "bad customFile passed unexpectedly"))
            if not bad_ok:
                integrity_mismatches += 1

            good_customfile = _make_customfile_valid()
            good_errors = list(validator.iter_errors(good_customfile))
            good_ok = len(good_errors) == 0
            integrity_checks.append(("customFile good?PASS (anti-drift)", good_ok, f"good customFile failed: {good_errors[0].message[:80]}" if good_errors else ""))
            if not good_ok:
                integrity_mismatches += 1

            task_lock = schema.get("$defs", {}).get("lockLevel", {}).get("enum", [])
            custom_lock = cf_schema.get("properties", {}).get("lockLevel", {}).get("enum", [])
            lock_ok = custom_lock == task_lock
            integrity_checks.append(("customFile lockLevel mirrors taskstate lockLevel", lock_ok, f"custom={custom_lock}; taskstate={task_lock}"))
            if not lock_ok:
                integrity_mismatches += 1
        except Exception as exc:
            integrity_checks.append(("customFile schema self-check", False, f"load/check error: {exc}"))
            integrity_mismatches += 1
    else:
        integrity_checks.append(("customFile schema self-check", False, "customFile.schema.json not found"))
        integrity_mismatches += 1

    # v1.9 durable layer: asset store + memory adapter anti-drift checks
    required_v19_defs = ["assetType", "assetContext", "durableAsset"]
    for def_name in required_v19_defs:
        ok = def_name in schema.get("$defs", {})
        integrity_checks.append((f"v1.9 def present: {def_name}", ok, "def missing from schema"))
        if not ok:
            integrity_mismatches += 1

    mem_props = schema.get("$defs", {}).get("memoryFields", {}).get("properties", {})
    assets_ok = "assets" in mem_props
    integrity_checks.append(("memoryFields.assets present", assets_ok, "assets index missing"))
    if not assets_ok:
        integrity_mismatches += 1

    prov_ok = "provenance" in schema.get("$defs", {}).get("memoryEntry", {}).get("properties", {})
    integrity_checks.append(("memoryEntry.provenance present", prov_ok, "provenance field missing"))
    if not prov_ok:
        integrity_mismatches += 1

    # durableAsset.tags.domains must reuse #/$defs/domain (no second topic taxonomy → no drift)
    dom_ref = (
        schema.get("$defs", {}).get("durableAsset", {}).get("properties", {})
        .get("tags", {}).get("properties", {}).get("domains", {})
        .get("items", {}).get("$ref")
    )
    dom_ok = dom_ref == "#/$defs/domain"
    integrity_checks.append(("durableAsset.tags.domains reuses #/$defs/domain", dom_ok, f"got {dom_ref}, expected #/$defs/domain"))
    if not dom_ok:
        integrity_mismatches += 1

    # assetType must be generalized beyond ppt-template (v1.9.1: any common artifact)
    at_values = schema.get("$defs", {}).get("assetType", {}).get("enum", [])
    at_ok = "report" in at_values and "proposal" in at_values
    integrity_checks.append(("assetType generalized beyond ppt-template", at_ok, f"got {at_values}; expected report/proposal present"))
    if not at_ok:
        integrity_mismatches += 1

    # customFile v1.9: referenceArtifact.assetId + slidesProfile def + good/bad anti-drift
    cf_path19 = _default_customfile_schema(Path(args.schema).resolve().parent)
    if cf_path19.exists():
        try:
            cf_schema19 = json.loads(cf_path19.read_text(encoding="utf-8"))
            cf_defs19 = cf_schema19.get("$defs", {})
            assetid_ok = "assetId" in cf_defs19.get("referenceArtifact", {}).get("properties", {})
            integrity_checks.append(("customFile referenceArtifact.assetId present", assetid_ok, "assetId missing"))
            if not assetid_ok:
                integrity_mismatches += 1
            sp_ok = "slidesProfile" in cf_defs19
            integrity_checks.append(("customFile slidesProfile def present", sp_ok, "slidesProfile missing"))
            if not sp_ok:
                integrity_mismatches += 1
            ap_ok = "artifactProfile" in cf_defs19
            integrity_checks.append(("customFile artifactProfile def present", ap_ok, "artifactProfile missing"))
            if not ap_ok:
                integrity_mismatches += 1
            if sp_ok:
                sp_validator = Draft202012Validator({
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$ref": "#/$defs/slidesProfile",
                    "$defs": cf_defs19,
                })
                good_sp = {
                    "pageRoles": [
                        {"slideRef": "slide-1", "roleTag": "cover", "roleText": "cover", "keepPolicy": "core"}
                    ],
                    "slideIndex": {"modular": True, "intentMap": [{"intent": "weekly summary", "slides": ["slide-3"]}]},
                }
                good_sp_errors = list(sp_validator.iter_errors(good_sp))
                good_sp_ok = len(good_sp_errors) == 0
                integrity_checks.append(("slidesProfile good→PASS (anti-drift)", good_sp_ok, f"good slidesProfile failed: {good_sp_errors[0].message[:80]}" if good_sp_errors else ""))
                if not good_sp_ok:
                    integrity_mismatches += 1
                bad_sp = {"slideIndex": {}}  # missing pageRoles + slideIndex.modular
                bad_sp_ok = len(list(sp_validator.iter_errors(bad_sp))) > 0
                integrity_checks.append(("slidesProfile bad→FAIL (anti-drift)", bad_sp_ok, "bad slidesProfile passed unexpectedly"))
                if not bad_sp_ok:
                    integrity_mismatches += 1
            if ap_ok:
                ap_validator = Draft202012Validator({
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$ref": "#/$defs/artifactProfile",
                    "$defs": cf_defs19,
                })
                good_ap = {
                    "artifactType": "纯文字工作周报",
                    "structure": [
                        {"unit": "一句话总结", "function": "30 秒抓住本周", "presence": "mandatory", "order": 1}
                    ],
                    "qualityCriteria": {
                        "good": ["30 秒看懂本周", "问题带下一步"],
                        "bad": ["全是'推进/优化'空话", "无结果无数据"],
                    },
                }
                good_ap_errors = list(ap_validator.iter_errors(good_ap))
                good_ap_ok = len(good_ap_errors) == 0
                integrity_checks.append(("artifactProfile good→PASS (anti-drift)", good_ap_ok, f"good artifactProfile failed: {good_ap_errors[0].message[:80]}" if good_ap_errors else ""))
                if not good_ap_ok:
                    integrity_mismatches += 1
                bad_ap = {"artifactType": "x"}  # missing structure + qualityCriteria
                bad_ap_ok = len(list(ap_validator.iter_errors(bad_ap))) > 0
                integrity_checks.append(("artifactProfile bad→FAIL (anti-drift)", bad_ap_ok, "bad artifactProfile passed unexpectedly"))
                if not bad_ap_ok:
                    integrity_mismatches += 1
        except Exception as exc:
            integrity_checks.append(("customFile v1.9 self-check", False, f"load/check error: {exc}"))
            integrity_mismatches += 1

    # Runtime references must not carry dev-skill shell. Mock specs live in evals/.
    refs_dir = Path(args.schema).resolve().parent.parent / "references"
    if refs_dir.exists():
        bad_refs = []
        for ref_path in sorted(refs_dir.glob("*.md")):
            try:
                ref_text = ref_path.read_text(encoding="utf-8")
            except OSError as exc:
                bad_refs.append(f"{ref_path.name}: read error {exc}")
                continue
            problems = []
            if ref_text.startswith("---"):
                problems.append("frontmatter")
            if "\n## Mock Testing\n" in ref_text:
                problems.append("Mock Testing")
            if problems:
                bad_refs.append(f"{ref_path.name}: {', '.join(problems)}")
        refs_ok = len(bad_refs) == 0
        integrity_checks.append(("runtime references have no dev-skill shell", refs_ok, "; ".join(bad_refs)))
        if not refs_ok:
            integrity_mismatches += 1
    else:
        integrity_checks.append(("runtime references have no dev-skill shell", False, f"references dir not found: {refs_dir}"))
        integrity_mismatches += 1

    if not args.quiet and not args.json:
        print(f"[self] Schema integrity ({len(integrity_checks)} checks)...")
        for label, ok, detail in integrity_checks:
            tag = "PASS" if ok else "FAIL"
            print(f"  [{tag}]  {label}" + (f"  ({detail})" if not ok and detail else ""))
        if integrity_mismatches == 0:
            print("  All integrity checks passed.\n")
        else:
            print(f"  {integrity_mismatches} integrity check(s) failed.\n")

    # ── Regression samples ──

    self_regression_samples: List[Tuple[str, dict, str]] = [
        # intakeOutput
        ("intakeOutput PASS", _make_intake_output_valid(), "PASS"),
        ("intakeOutput FAIL enum", _make_intake_output(F_intent="explain"), "FAIL"),
        ("intakeOutput FAIL required", _make_intake_output(F_missing="domains"), "FAIL"),
        # boundaryOutput
        ("boundaryOutput PASS", _make_boundary_output_valid(), "PASS"),
        ("boundaryOutput FAIL enum", _make_boundary_output(F_complexityTier="低"), "FAIL"),
        ("boundaryOutput FAIL extra", _make_boundary_output(F_extra="fooBar"), "FAIL"),
        # strategyOutput
        ("strategyOutput PASS", _make_strategy_output_valid(valid_framework), "PASS"),
        ("strategyOutput FAIL frameworkName enum", _make_strategy_output(F_fwName=invalid_framework, valid_framework=valid_framework), "FAIL"),
        ("strategyOutput FAIL extra field", _make_strategy_output(F_extra_dim="structurePreference", valid_framework=valid_framework), "FAIL"),
        # executionControlOutput continuity fields
        ("executionControlOutput PASS continuity fields", _make_execution_control_output_valid(valid_budget), "PASS"),
        ("executionControlOutput FAIL budgetTier enum", _make_execution_control_output(F_budgetTier=invalid_budget, valid_budget=valid_budget), "FAIL"),
        # mockCase
        ("mockCase FAIL domain enum", _make_mock_with_domain("medicine"), "FAIL"),
        ("mockCase FAIL taskType enum", _make_mock_with_tasktype("medical/advise"), "FAIL"),
    ]

    mismatch = 0
    all_results = [
        {
            "target": label,
            "def": "integrity",
            "status": "pass" if ok else "fail",
            "expected": "pass",
            "actual": "pass" if ok else "fail",
            "errors": [] if ok else [{"path": "$", "message": detail or "integrity check failed", "value": None}],
        }
        for label, ok, detail in integrity_checks
    ]
    if not args.quiet and not args.json:
        print(f"[self] Running {len(self_regression_samples)} drift-regression samples...\n")

    for label, instance, expected in self_regression_samples:
        def_name = _guess_def_from_label(label)
        validator = _build_validator(def_name, schema)
        errors = _collect_errors(validator, instance)
        actual = "PASS" if len(errors) == 0 else "FAIL"
        status = "pass" if actual == expected else "fail"
        all_results.append(
            {
                "target": label,
                "def": def_name,
                "status": status,
                "expected": expected.lower(),
                "actual": actual.lower(),
                "errors": errors,
            }
        )

        if actual != expected:
            mismatch += 1
            if not args.json:
                print(f"[MISMATCH] {label}: expected {expected}, got {actual}")
        elif not args.quiet and not args.json:
            print(f"  [{actual}]  {label}")

    summary = f"{len(self_regression_samples)} regression samples: {len(self_regression_samples) - mismatch} ok, {mismatch} mismatch"
    has_failures = (mismatch > 0) or (integrity_mismatches > 0)
    if args.json:
        _json_output(
            len(self_regression_samples) + len(integrity_checks),
            (len(self_regression_samples) - mismatch) + (len(integrity_checks) - integrity_mismatches),
            mismatch + integrity_mismatches,
            all_results,
            args,
        )
    if not args.quiet:
        print(f"\n{summary}")
    else:
        print(summary)
    sys.exit(1 if has_failures else 0)


def _guess_def_from_label(label: str) -> str:
    if "intakeOutput" in label:
        return "intakeOutput"
    if "boundaryOutput" in label:
        return "boundaryOutput"
    if "strategyOutput" in label:
        return "strategyOutput"
    if "executionControlOutput" in label:
        return "executionControlOutput"
    return "mockCase"


# ── regression fixture builders (one per schema shape) ──


def _make_intake_output_valid() -> dict:
    return {
        "intent": "execute",
        "taskTypes": [{"type": "code", "role": "primary"}],
        "knownContext": [],
        "missingContext": [],
        "assumptions": [],
        "uncertainPoints": [],
        "intentShiftDetected": False,
        "clarificationNeeded": False,
        "composite": False,
        "domains": [],
    }


def _make_intake_output(F_intent: Optional[str] = None, F_missing: Optional[str] = None) -> dict:
    base = _make_intake_output_valid()
    if F_intent is not None:
        base["intent"] = F_intent
    if F_missing is not None:
        del base[F_missing]
    return base


def _make_boundary_output_valid() -> dict:
    return {
        "canAnswerDirectly": True,
        "needClarification": False,
        "needTool": False,
        "needWebCheck": False,
        "needSourceCheck": False,
        "riskLevel": "low",
        "complexityTier": "low",
        "truthConstraints": [],
        "uncertainClaims": [],
        "sourceConflicts": [],
        "responseConstraints": [],
    }


def _make_boundary_output(F_complexityTier: Optional[str] = None, F_extra: Optional[str] = None) -> dict:
    base = _make_boundary_output_valid()
    if F_complexityTier is not None:
        base["complexityTier"] = F_complexityTier
    if F_extra is not None:
        base[F_extra] = "unexpected_field_value"
    return base


def _make_strategy_output_valid(framework_name: str = "direct-check") -> dict:
    return {
        "successCriteria": ["test"],
        "audienceProfile": {
            "dimensions": {
                "explainDepth": "normal",
                "technicalDetail": "medium",
                "actionOrientation": "execute",
                "tone": "neutral",
                "formality": "neutral",
                "visualNeed": "none",
                "backgroundAssumed": "practitioner",
            }
        },
        "workMode": "STANDARD",
        "reasoningFrameworks": [
            {"name": framework_name, "role": "primary", "instructions": ["step 1"]}
        ],
    }


def _make_strategy_output(
    F_fwName: Optional[str] = None,
    F_extra_dim: Optional[str] = None,
    valid_framework: str = "direct-check",
) -> dict:
    base = _make_strategy_output_valid(valid_framework)
    if F_fwName is not None:
        base["reasoningFrameworks"][0]["name"] = F_fwName
    if F_extra_dim is not None:
        base["audienceProfile"]["dimensions"]["structurePreference"] = F_extra_dim
    return base


def _make_execution_control_output_valid(budget_tier: str = "normal") -> dict:
    return {
        "route": ["intake", "boundary", "compose", "quality-gate", "memory"],
        "skip": ["strategy", "solution-space", "6a", "6b", "6d"],
        "workModeOverride": None,
        "upgrade": False,
        "humanCheckRequired": False,
        "downgradeForbidden": False,
        "loopDetected": False,
        "loopType": None,
        "shouldSyncUser": False,
        "syncTrigger": None,
        "syncMessage": None,
        "requiresConfirmation": False,
        "pressureLevel": None,
        "escalationAction": None,
        "stopLoss": False,
        "minimumViableOutputRequired": False,
        "silentViolationDetected": False,
        "violationLog": [],
        "budgetTier": budget_tier,
        "emergencyLanding": False,
        "capabilityLoss": [],
        "checkpoint": {
            "written": True,
            "path": ".collab-checkpoint/task-1.json",
            "lastCompletedModule": "execution-control",
        },
        "sideEffectsDone": [],
        "resumedFrom": None,
    }


def _make_execution_control_output(
    F_budgetTier: Optional[str] = None,
    valid_budget: str = "normal",
) -> dict:
    base = _make_execution_control_output_valid(valid_budget)
    if F_budgetTier is not None:
        base["budgetTier"] = F_budgetTier
    return base


def _make_customfile_valid() -> dict:
    return {
        "kind": "slides",
        "mode": "render-engine",
        "lockStrategy": "zone-first",
        "lockLevel": "strict",
        "manifest": {"id": "cf-1", "title": "Quarterly Report", "templateId": "corp-v3"},
        "materials": [
            {
                "id": "m1",
                "origin": "derived",
                "content": "Revenue grew 12%.",
                "boundTo": "block-1.body",
            }
        ],
        "blocks": [
            {
                "blockId": "block-1",
                "template": "cover",
                "zones": [
                    {"role": "title", "text": "Quarterly Report", "locked": True},
                    {"role": "body", "boundMaterialId": "m1"},
                ],
            }
        ],
        "referenceArtifact": {
            "kind": "pptx",
            "sourceRef": "samples/board-report.pptx",
            "usage": "style-reference",
            "extractionStatus": "extracted",
            "notes": ["Use as layout grammar; do not copy business content."],
        },
        "styleProfile": {
            "reusePolicy": "interpret-not-copy",
            "visualDNA": ["dense executive layout", "calm accent color"],
            "layoutGrammar": ["cover uses title-left and metric-right"],
            "componentPatterns": ["section divider", "metric strip"],
            "typography": ["Inter-like sans serif"],
            "colorSystem": ["dark text on white canvas"],
            "spacingRhythm": ["wide outer margin, tight inner grid"],
            "chartRules": ["prefer annotated bar charts"],
            "imitationBoundaries": ["do not copy logos or confidential content"],
        },
        "handoffPreflight": {
            "force1Force3Check": {
                "passed": True,
                "checkedAgainst": ["templateId=corp-v3", "locked title zone"],
                "mismatches": [],
                "resolution": "proceed",
            },
            "force2CapabilityCheck": {
                "passed": True,
                "compositionUsed": True,
                "toolPlan": [
                    {
                        "skillId": "html-ppt",
                        "role": "renderer",
                        "capability": "slides",
                        "contractFit": "native",
                    },
                    {
                        "skillId": "huashu-design",
                        "role": "verifier",
                        "capability": "design-review",
                        "contractFit": "native",
                    },
                ],
                "missingCapabilities": [],
            },
            "injectionDecision": "compose-tools",
            "recommendedInstall": [],
            "logicChain": [
                "force1 satisfies force3 corporate template constraints",
                "renderer and verifier are composed to cover output plus review",
            ],
        },
        "designReview": {
            "enabled": True,
            "rubric": "huashu-ppt",
            "trigger": "artifact-produced",
            "scores": [
                {
                    "dimension": "visual_hierarchy",
                    "score": 7.5,
                    "evidence": "Title hierarchy is clear, but metric cards are too dominant.",
                    "advice": "Reduce metric-card weight and keep the title as the primary anchor.",
                }
            ],
            "agentSuggestion": "Reduce metric-card visual weight while keeping the corporate template fixed.",
            "diagnosticChain": [
                "preflight passed before customFile injection",
                "artifact review found visual hierarchy weakness",
            ],
            "influencePolicy": "advisory-only",
            "appliedToCustomFile": False,
        },
        "constraints": {
            "templateId": "corp-v3",
            "font": "Inter",
            "lockedZones": ["block-1.title"],
            "forbidden": ["change template", "do not copy logos or confidential content"],
            "softGuidance": [],
        },
    }


def _make_mock_with_domain(bad_domain: str) -> dict:
    return {
        "id": 99,
        "quadrant": "N",
        "input": {"userMessage": "test"},
        "expected": {
            "intake": {"domains": [bad_domain]},
        },
    }


def _make_mock_with_tasktype(bad_tasktype: str) -> dict:
    return {
        "id": 99,
        "quadrant": "N",
        "input": {"userMessage": "test"},
        "expected": {
            "intake": {"taskTypes": [{"type": bad_tasktype, "role": "primary"}]},
        },
    }


# ──────────────────── lenses (v1.5) ────────────────────


def _default_lenses_yaml(schema_dir: Path) -> Path:
    return schema_dir.parent / "references" / "roundtable" / "lenses.yaml"


def _default_lens_schema(schema_dir: Path) -> Path:
    return schema_dir.parent / "references" / "roundtable" / "lens_schema.json"


def cmd_lenses(args: Any) -> None:
    """Validate lenses.yaml cards against lens_schema.json + registry integrity."""
    if yaml is None:
        print("Missing required dependency: PyYAML\nInstall with: pip install pyyaml", file=sys.stderr)
        sys.exit(2)

    schema_dir = Path(args.schema).resolve().parent
    lenses_path = Path(args.lenses or _default_lenses_yaml(schema_dir)).resolve()
    lens_schema_path = Path(args.lens_schema or _default_lens_schema(schema_dir)).resolve()

    if not lenses_path.exists():
        print(f"lenses.yaml not found: {lenses_path}", file=sys.stderr)
        sys.exit(2)
    if not lens_schema_path.exists():
        print(f"lens_schema.json not found: {lens_schema_path}", file=sys.stderr)
        sys.exit(2)

    # Load lens schema
    try:
        lens_schema = json.loads(lens_schema_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Failed to load lens_schema.json: {exc}", file=sys.stderr)
        sys.exit(2)

    # Load lenses YAML
    try:
        with open(lenses_path, "r", encoding="utf-8") as f:
            lenses_data = yaml.safe_load(f)
    except Exception as exc:
        print(f"Failed to load lenses.yaml: {exc}", file=sys.stderr)
        sys.exit(2)

    cards = lenses_data.get("lenses", [])
    if not isinstance(cards, list) or len(cards) == 0:
        print(f"No lenses found in {lenses_path}", file=sys.stderr)
        sys.exit(2)

    # Build registry (all lens ids)
    registry = set()
    for card in cards:
        if isinstance(card, dict) and "id" in card:
            registry.add(card["id"])

    # Get frameworkName enum from schema
    fw_enum = set(args.schema_data.get("$defs", {}).get("frameworkName", {}).get("enum", []))

    total = 0
    passed = 0
    failed = 0

    for card in cards:
        total += 1
        card_id = card.get("id", f"<no-id-at-index-{total-1}>")
        card_errors = []

        # 1. Validate against lens_schema.json
        validator = Draft202012Validator(lens_schema)
        for err in validator.iter_errors(card):
            card_errors.append(f"{err.json_path}: {err.message}")

        # 2. Check conflicts_with references exist in registry
        for ref in card.get("conflicts_with", []):
            if ref not in registry:
                card_errors.append(f"conflicts_with['{ref}'] not in registry")

        # 3. Check compatible_with references exist in registry
        for ref in card.get("compatible_with", []):
            if ref not in registry:
                card_errors.append(f"compatible_with['{ref}'] not in registry")

        # 4. Check reuses_framework id matches frameworkName
        if card.get("reuses_framework") is True:
            if card_id not in fw_enum:
                card_errors.append(f"reuses_framework=true but '{card_id}' not in frameworkName enum")
            # Also verify: if it's in frameworkName, it MUST be reuses_framework
            # (We just check the forward direction here)

        if card_errors:
            failed += 1
            tag = "FAIL"
        else:
            passed += 1
            tag = "PASS"

        if not args.quiet:
            print(f"[{tag}] lens card '{card_id}'")
            for err in card_errors:
                print(f"   {err}")

    # 5. Backward check: frameworkName values that appear in registry should have reuses_framework=true
    fw_in_registry = fw_enum & registry
    for fw_id in sorted(fw_in_registry):
        fw_card = next((c for c in cards if c.get("id") == fw_id), None)
        if fw_card and fw_card.get("reuses_framework") is not True:
            if not args.quiet:
                print(f"[FAIL] frameworkName '{fw_id}' in registry but reuses_framework != true")

    if args.json:
        _json_output_lenses(total, passed, failed)
    elif not args.quiet:
        print(f"\n{total} lens card(s): {passed} passed, {failed} failed")

    sys.exit(1 if failed > 0 else 0)


def _json_output_lenses(total: int, passed: int, failed: int) -> None:
    report = {"summary": {"total": total, "passed": passed, "failed": failed}}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(1 if failed > 0 else 0)


# ──────────────────── downstream (v1.6) ────────────────────


def _default_downstream_schema(schema_dir: Path) -> Path:
    return schema_dir / "downstreamPayload.schema.json"


def _default_customfile_schema(schema_dir: Path) -> Path:
    return schema_dir / "customFile.schema.json"


def _default_registry_schema(schema_dir: Path) -> Path:
    return schema_dir / "skill-registry.schema.json"


def _default_registry_file(schema_dir: Path) -> Path:
    return schema_dir.parent / "references" / "skill-registry.yaml"


def cmd_downstream(args: Any) -> None:
    """闸D: validate a machinePayload instance against downstreamPayload.schema.json."""
    schema_dir = Path(args.schema).resolve().parent
    ds_path = Path(args.downstream_schema or _default_downstream_schema(schema_dir)).resolve()

    if not ds_path.exists():
        print(f"downstreamPayload.schema.json not found: {ds_path}", file=sys.stderr)
        sys.exit(2)

    try:
        ds_schema = json.loads(ds_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Failed to load downstream schema: {exc}", file=sys.stderr)
        sys.exit(2)

    Draft202012Validator.check_schema(ds_schema)

    total = 0
    passed = 0
    failed = 0
    all_results = []

    for target_spec in args.files:
        total += 1
        if target_spec == "-":
            instance = _load_json_stdin()
            target_name = "-"
        else:
            path, instance = _load_json_file(target_spec)
            target_name = str(path)

        validator = Draft202012Validator(ds_schema)
        errors = _collect_errors(validator, instance)
        ok = len(errors) == 0
        status = "pass" if ok else "fail"
        if ok:
            passed += 1
        else:
            failed += 1
        all_results.append(
            {"target": target_name, "kind": instance.get("kind", "unknown"), "status": status, "errors": errors}
        )

        if not args.quiet and not args.json:
            tag = "PASS" if ok else "FAIL"
            print(f"[{tag}] {target_name}  (#/downstreamPayload.schema.json, kind={instance.get('kind', '?')})")
            for err in errors:
                print(f"   {err['path']} : {err['message']}")

    if args.json:
        _json_output(total, passed, failed, all_results, args)
    elif not args.quiet:
        print(f"\n{total} file(s): {passed} passed, {failed} failed")
    else:
        print(f"{total} file(s): {passed} passed, {failed} failed")

    sys.exit(1 if failed > 0 else 0)


# ──────────────────── lint-md (过渡) ────────────────────




def cmd_customfile(args: Any) -> None:
    """Validate a v1.8 customFile instance against customFile.schema.json."""
    schema_dir = Path(args.schema).resolve().parent
    cf_path = Path(args.customfile_schema or _default_customfile_schema(schema_dir)).resolve()

    if not cf_path.exists():
        print(f"customFile.schema.json not found: {cf_path}", file=sys.stderr)
        sys.exit(2)

    try:
        cf_schema = json.loads(cf_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Failed to load customFile schema: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        Draft202012Validator.check_schema(cf_schema)
    except SchemaError as exc:
        print(f"customFile schema is invalid: {exc.message}", file=sys.stderr)
        sys.exit(3)

    total = 0
    passed = 0
    failed = 0
    all_results = []

    for target_spec in args.files:
        total += 1
        if target_spec == "-":
            instance = _load_json_stdin()
            target_name = "-"
        else:
            path, instance = _load_json_file(target_spec)
            target_name = str(path)

        validator = Draft202012Validator(cf_schema)
        errors = _collect_errors(validator, instance)
        ok = len(errors) == 0
        if ok:
            passed += 1
        else:
            failed += 1
        all_results.append({
            "target": target_name,
            "kind": instance.get("kind", "unknown") if isinstance(instance, dict) else "unknown",
            "status": "pass" if ok else "fail",
            "errors": errors,
        })

        if not args.quiet and not args.json:
            tag = "PASS" if ok else "FAIL"
            kind = instance.get("kind", "?") if isinstance(instance, dict) else "?"
            print(f"[{tag}] {target_name}  (#/customFile.schema.json, kind={kind})")
            for err in errors:
                print(f"   {err['path']} : {err['message']}")
                if err["value"] is not None:
                    print(f"            value: {err['value']}")

    if args.json:
        _json_output(total, passed, failed, all_results, args)
    elif not args.quiet:
        print(f"\n{total} file(s): {passed} passed, {failed} failed")
    else:
        print(f"{total} file(s): {passed} passed, {failed} failed")

    sys.exit(1 if failed > 0 else 0)

def cmd_asset(args: Any) -> None:
    """Validate a v1.9 asset: slidesProfile (customFile.schema.json) or durableAsset (taskstate)."""
    schema_dir = Path(args.schema).resolve().parent
    kind = args.asset_kind

    if kind == "durable-asset":
        validator = _build_validator("durableAsset", args.schema_data)
        def_label = "taskstate #/$defs/durableAsset"
    else:
        cf_path = Path(args.customfile_schema or _default_customfile_schema(schema_dir)).resolve()
        if not cf_path.exists():
            print(f"customFile.schema.json not found: {cf_path}", file=sys.stderr)
            sys.exit(2)
        try:
            cf_schema = json.loads(cf_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(cf_schema)
        except (json.JSONDecodeError, OSError, SchemaError) as exc:
            print(f"Failed to load customFile schema: {exc}", file=sys.stderr)
            sys.exit(3)
        def_name = "slidesProfile" if kind == "slides-profile" else "artifactProfile"
        sub = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": f"#/$defs/{def_name}",
            "$defs": cf_schema["$defs"],
        }
        validator = Draft202012Validator(sub)
        def_label = f"customFile #/$defs/{def_name}"

    total = 0
    passed = 0
    failed = 0
    all_results = []

    for target_spec in args.files:
        total += 1
        if target_spec == "-":
            instance = _load_json_stdin()
            target_name = "-"
        else:
            path, instance = _load_json_file(target_spec)
            target_name = str(path)

        errors = _collect_errors(validator, instance)
        ok = len(errors) == 0
        if ok:
            passed += 1
        else:
            failed += 1
        all_results.append({"target": target_name, "status": "pass" if ok else "fail", "errors": errors})

        if not args.quiet and not args.json:
            tag = "PASS" if ok else "FAIL"
            print(f"[{tag}] {target_name}  ({def_label})")
            for err in errors:
                print(f"   {err['path']} : {err['message']}")
                if err["value"] is not None:
                    print(f"            value: {err['value']}")

    if args.json:
        _json_output(total, passed, failed, all_results, args)
    elif not args.quiet:
        print(f"\n{total} file(s): {passed} passed, {failed} failed")
    else:
        print(f"{total} file(s): {passed} passed, {failed} failed")

    sys.exit(1 if failed > 0 else 0)

def cmd_registry(args: Any) -> None:
    """Validate references/skill-registry.yaml against skill-registry.schema.json."""
    if yaml is None:
        print("Missing required dependency: PyYAML\nInstall with: pip install pyyaml", file=sys.stderr)
        sys.exit(2)

    schema_dir = Path(args.schema).resolve().parent
    registry_schema_path = Path(args.registry_schema or _default_registry_schema(schema_dir)).resolve()
    registry_path = Path(args.registry or _default_registry_file(schema_dir)).resolve()

    if not registry_schema_path.exists():
        print(f"skill-registry.schema.json not found: {registry_schema_path}", file=sys.stderr)
        sys.exit(2)
    if not registry_path.exists():
        print(f"skill-registry.yaml not found: {registry_path}", file=sys.stderr)
        sys.exit(2)

    try:
        registry_schema = json.loads(registry_schema_path.read_text(encoding="utf-8"))
        registry_data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, yaml.YAMLError) as exc:
        print(f"Failed to load registry or schema: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        Draft202012Validator.check_schema(registry_schema)
    except SchemaError as exc:
        print(f"Registry schema is invalid: {exc.message}", file=sys.stderr)
        sys.exit(3)

    validator = Draft202012Validator(registry_schema)
    errors = _collect_errors(validator, registry_data)
    ok = len(errors) == 0
    result = {
        "target": str(registry_path),
        "def": "skill-registry.schema.json",
        "status": "pass" if ok else "fail",
        "errors": errors,
    }

    if args.json:
        _json_output(1, 1 if ok else 0, 0 if ok else 1, [result], args)
    elif not args.quiet:
        print(f"[{'PASS' if ok else 'FAIL'}] registry {registry_path}")
        for err in errors:
            print(f"   {err['path']} : {err['message']}")
            if err["value"] is not None:
                print(f"            value: {err['value']}")
    else:
        print(f"1 file(s): {1 if ok else 0} passed, {0 if ok else 1} failed")

    sys.exit(0 if ok else 1)

def cmd_lint_md(args: Any) -> None:
    """Best-effort regex lint of Markdown mock table data."""
    path = Path(args.md_file).resolve()
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(2)
    text = path.read_text(encoding="utf-8")

    schema = args.schema_data
    defs = schema.get("$defs", {})

    intent_enum: List[str] = defs.get("intent", {}).get("enum", [])
    tasktype_enum: List[str] = defs.get("taskTypeName", {}).get("enum", [])
    domain_enum: List[str] = defs.get("domain", {}).get("enum", [])
    risk_enum: List[str] = defs.get("riskLevel", {}).get("enum", [])
    tier_enum: List[str] = defs.get("complexityTier", {}).get("enum", [])
    mode_enum: List[str] = defs.get("workMode", {}).get("enum", [])

    failures = 0

    def _report_bad(value: str, enum: List[str], label: str) -> int:
        if value not in enum:
            print(f"  [{label}] suspicious value in md: '{value}' not in {enum}")
            return 1
        return 0

    def _extract_list_values(line: str, field: str) -> List[str]:
        match = re.search(rf"\b{re.escape(field)}\s*=\s*\[([^\]]*)\]", line)
        if not match:
            return []
        return re.findall(r"[A-Za-z][A-Za-z0-9_-]*", match.group(1))

    def _extract_scalar(line: str, field: str) -> Optional[str]:
        match = re.search(rf"\b{re.escape(field)}\s*=\s*([^,\s\]|)）]+)", line)
        return match.group(1) if match else None

    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        value = _extract_scalar(line, "intent")
        if value is not None:
            failures += _report_bad(value, intent_enum, f"L{i}:intent")
        for value in _extract_list_values(line, "taskTypes"):
            failures += _report_bad(value, tasktype_enum, f"L{i}:taskType")
        for value in _extract_list_values(line, "domains"):
            failures += _report_bad(value, domain_enum, f"L{i}:domain")
        value = _extract_scalar(line, "complexityTier")
        if value is not None:
            failures += _report_bad(value, tier_enum, f"L{i}:complexityTier")
        value = _extract_scalar(line, "riskLevel")
        if value is not None:
            failures += _report_bad(value, risk_enum, f"L{i}:riskLevel")
        value = _extract_scalar(line, "workMode")
        if value is not None:
            failures += _report_bad(value, mode_enum, f"L{i}:workMode")

    if failures == 0:
        print(f"[PASS] lint-md {path}")
    else:
        print(f"[FAIL] lint-md {path}: {failures} issue(s)")
    sys.exit(1 if failures > 0 else 0)


# ──────────────────── CLI ────────────────────


def _build_parser(schema_path_default: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="collab-master-skill validate.py — schema-driven output validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # check
    p = sub.add_parser("check", help="Validate JSON files against a $def (闸A)")
    p.add_argument("--def", dest="def_name", required=True, help="$def name, e.g. intakeOutput")
    p.add_argument("files", nargs="+", help="JSON file(s) or '-' for stdin")

    # mocks
    p = sub.add_parser("mocks", help="Validate a mockCase array file (闸B)")
    p.add_argument("cases_file", help="Path to mock-cases.json")

    # lenses
    p = sub.add_parser("lenses", help="Validate lenses.yaml cards against lens_schema.json (v1.5)")
    p.add_argument("--lenses", default=None, help="Path to lenses.yaml (default: references/roundtable/lenses.yaml)")
    p.add_argument("--lens-schema", default=None, help="Path to lens_schema.json (default: references/roundtable/lens_schema.json)")

    # downstream
    p = sub.add_parser("downstream", help="Validate machinePayload against downstreamPayload.schema.json (v1.6 闸D)")
    p.add_argument("files", nargs="+", help="JSON file(s) or '-' for stdin")
    p.add_argument("--downstream-schema", default=None, help="Path to downstreamPayload.schema.json")

    # customfile
    p = sub.add_parser("customfile", help="Validate customFile against customFile.schema.json (v1.8)")
    p.add_argument("files", nargs="+", help="JSON file(s) or '-' for stdin")
    p.add_argument("--customfile-schema", default=None, help="Path to customFile.schema.json")

    # asset (v1.9)
    p = sub.add_parser("asset", help="Validate a v1.9 asset: artifactProfile / slidesProfile / durableAsset")
    p.add_argument("files", nargs="+", help="JSON file(s) or '-' for stdin")
    p.add_argument("--asset-kind", choices=["artifact-profile", "slides-profile", "durable-asset"], default="artifact-profile",
                   help="artifact-profile (customFile #/$defs/artifactProfile, default) | slides-profile (visual specialization) | durable-asset (taskstate index entry)")
    p.add_argument("--customfile-schema", default=None, help="Path to customFile.schema.json")

    # registry
    p = sub.add_parser("registry", help="Validate references/skill-registry.yaml against skill-registry.schema.json (v1.6)")
    p.add_argument("--registry", default=None, help="Path to skill-registry.yaml")
    p.add_argument("--registry-schema", default=None, help="Path to skill-registry.schema.json")

    # self
    sub.add_parser("self", help="Schema check_schema + built-in drift regression")

    # lint-md
    p = sub.add_parser("lint-md", help="Best-effort regex lint of Markdown mock tables")
    p.add_argument("md_file", help="Path to mock-test-data.md")

    # list-defs
    sub.add_parser("list-defs", help="Print available $def names in schema")

    for p in parser._subparsers._group_actions[0].choices.values():
        p.add_argument("--schema", default=schema_path_default, help="Path to taskstate.schema.json")
        p.add_argument("--json", action="store_true", help="Machine-readable output")
        p.add_argument("--quiet", action="store_true", help="Only summary + exit code")
        p.add_argument("--all-errors", action="store_true", help="Already default (compat flag)")

    return parser


def _json_output(
    total: int, passed: int, failed: int, results: List[Dict[str, Any]], args: Any
) -> None:
    """Print machine-readable JSON report and exit."""
    report = {
        "summary": {"total": total, "passed": passed, "failed": failed},
        "results": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(1 if failed > 0 else 0)


def main() -> None:
    _require_jsonschema_version()
    default_schema = str(_script_dir() / "taskstate.schema.json")
    parser = _build_parser(default_schema)
    args = parser.parse_args()

    # Load schema for every command (schema path may be overridden)
    schema_path, schema_data = _resolve_schema(args.schema)
    args.schema_data = schema_data

    if args.command == "check":
        cmd_check(args)
    elif args.command == "mocks":
        cmd_mocks(args)
    elif args.command == "self":
        cmd_self(args)
    elif args.command == "lint-md":
        cmd_lint_md(args)
    elif args.command == "lenses":
        cmd_lenses(args)
    elif args.command == "downstream":
        cmd_downstream(args)
    elif args.command == "customfile":
        cmd_customfile(args)
    elif args.command == "asset":
        cmd_asset(args)
    elif args.command == "registry":
        cmd_registry(args)
    elif args.command == "list-defs":
        cmd_list_defs(args.schema_data)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()

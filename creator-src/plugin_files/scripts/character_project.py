#!/usr/bin/env python3
"""Deterministic project state for the character-assets Codex plugin.

Creative judgements and image review belong to the Skills. This module owns
imports, lineage, approvals, invalidation and release gates.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

SCHEMA = "CharacterProjectV1"
STAGES = ("avatar", "expression", "full_body", "execution")
HEAVY_TIERS = {"主角", "重要角色"}
SUPPORTED_INPUTS = {".json", ".md", ".markdown", ".xlsx"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
RECOGNITION_AXES = ("silhouette", "face_structure", "body_posture",
                    "hair_structure", "costume_color")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/package/2006/relationships"}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def digest(data):
    if isinstance(data, Path):
        h = hashlib.sha256()
        with data.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=".tmp-", delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temp = Path(stream.name)
    os.replace(temp, path)


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def safe_id(value):
    ensure(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", value or "")),
           f"Unsafe identifier: {value!r}")
    return value


def require_list(obj, key):
    ensure(isinstance(obj.get(key), list), f"{key} must be a list")


def require_text(obj, key):
    ensure(isinstance(obj.get(key), str) and obj[key].strip(), f"{key} must be text")


def _xlsx_rows(path):
    """Read cell values with the standard library; no Excel runtime required."""
    with zipfile.ZipFile(path) as archive:
        book = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in rels}
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in item.findall(".//m:t", NS))
                       for item in root.findall("m:si", NS)]
        result = {}
        for sheet in book.findall("m:sheets/m:sheet", NS):
            target = targets[sheet.attrib[f"{{{NS['r']}}}id"]].lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            xml = ET.fromstring(archive.read(target))
            rows = []
            for row in xml.findall(".//m:sheetData/m:row", NS):
                cells = {}
                for cell in row.findall("m:c", NS):
                    match = re.match(r"([A-Z]+)", cell.attrib.get("r", ""))
                    if not match:
                        continue
                    col = 0
                    for char in match.group(1):
                        col = col * 26 + ord(char) - 64
                    val = cell.find("m:v", NS)
                    if cell.attrib.get("t") == "inlineStr":
                        text = "".join(t.text or "" for t in cell.findall(".//m:t", NS))
                    elif val is None:
                        text = ""
                    elif cell.attrib.get("t") == "s":
                        text = strings[int(val.text or "0")]
                    else:
                        text = val.text or ""
                    cells[col] = text
                if cells:
                    rows.append([cells.get(i, "") for i in range(1, max(cells) + 1)])
            result[sheet.attrib["name"]] = rows
        return result


def load_source(path):
    path = Path(path).expanduser().resolve()
    ensure(path.is_file(), f"Input file missing: {path}")
    suffix = path.suffix.lower()
    ensure(suffix in SUPPORTED_INPUTS, f"Unsupported input: {path.name}")
    if suffix == ".json":
        return read_json(path)
    if suffix in {".md", ".markdown"}:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        return {"format": "markdown", "lines": [
            {"ref": f"{path.name}:L{i}", "text": text} for i, text in enumerate(lines, 1)]}
    sheets = _xlsx_rows(path)
    return {"format": "xlsx", "sheets": {name: [
        {"ref": f"{path.name}:{name}!R{i}", "cells": row}
        for i, row in enumerate(rows, 1)] for name, rows in sheets.items()}}


def _characters_from_markdown(data):
    lines = [row["text"] for row in data["lines"]]
    result = []
    headers = None
    for line in lines:
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if "资产ID" in cells and ("人物名" in cells or "角色名" in cells):
            headers = cells
            continue
        if headers and re.fullmatch(r"\s*:?-+:?\s*", cells[0]):
            continue
        if headers and len(cells) >= len(headers):
            row = dict(zip(headers, cells))
            ident = row.get("资产ID", "")
            if ident.startswith("CHR-"):
                result.append({"id": ident, "name": row.get("人物名") or row.get("角色名"),
                               "tier": row.get("角色层级", "未分层"),
                               "script_facts": [row.get("剧本明确特征", "")],
                               "source_refs": [row.get("来源位置", "")],
                               "states": [{"id": row.get("状态ID", "S01"),
                                           "name": row.get("状态名", "常态")} ]})
    return result


def roster_from_assets(data):
    if isinstance(data, dict) and isinstance(data.get("characters"), list):
        source = data["characters"]
    elif isinstance(data, dict) and data.get("format") == "xlsx":
        rows = data["sheets"].get("人物", [])
        ensure(rows, "Asset workbook has no 人物 sheet")
        headers = rows[0]["cells"]
        source = []
        for row in rows[1:]:
            fields = dict(zip(headers, row["cells"]))
            ident = str(fields.get("资产ID", ""))
            if ident.startswith("CHR-"):
                source.append({"id": ident, "name": fields.get("人物名", ""),
                               "tier": fields.get("角色层级", "未分层"),
                               "script_facts": [fields.get("剧本明确特征", "")],
                               "source_refs": [fields.get("来源位置", "")],
                               "states": [{"id": fields.get("状态ID", "S01"),
                                           "name": fields.get("状态名", "常态"),
                                           "script_facts": [fields.get("状态明确特征", "")] }]})
    elif isinstance(data, dict) and data.get("format") == "markdown":
        source = _characters_from_markdown(data)
    else:
        raise ValueError("Asset table has no readable character roster")
    ensure(source, "Asset table contains no characters")
    combined = {}
    for item in source:
        ident = safe_id(str(item.get("id", "")))
        ensure(str(item.get("name", "")).strip(), f"Character {ident} has no name")
        if ident not in combined:
            combined[ident] = copy.deepcopy(item)
            combined[ident]["states"] = list(item.get("states") or [])
        else:
            combined[ident]["states"].extend(item.get("states") or [])
    return [{"id": ident, "name": item["name"], "tier": item.get("tier", "未分层"),
             "priority": "deep" if item.get("tier") in HEAVY_TIERS else "light",
             "states": item.get("states", []), "aliases": item.get("aliases", []),
             "asset_digest": digest(item)} for ident, item in combined.items()]


def validate_lineage(screenplay_path, screenplay, assets, scene_log=None):
    if isinstance(screenplay, dict) and screenplay.get("format") not in {"markdown", "xlsx"}:
        ensure(isinstance(screenplay.get("episodes"), list),
               "Standardized screenplay JSON needs an episodes array")
    if isinstance(assets, dict) and isinstance(assets.get("source"), dict):
        source_hash = assets["source"].get("sha256")
        if source_hash:
            ensure(source_hash == digest(Path(screenplay_path).expanduser().resolve()),
                   "Asset table was derived from a different screenplay version")
    if isinstance(screenplay, dict) and isinstance(scene_log, dict):
        original = screenplay.get("source_manifest", {}).get("source_sha256")
        scene_original = scene_log.get("source_manifest", {}).get("source_sha256")
        if original and scene_original:
            ensure(original == scene_original,
                   "Scene log was derived from a different screenplay source")


def _copy_input(root, kind, path, revision):
    source = Path(path).expanduser().resolve()
    loaded = load_source(source)
    target = root / "inputs" / f"rev-{revision:03d}" / f"{kind}{source.suffix.lower()}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {"path": str(target.relative_to(root)), "original_name": source.name,
            "format": source.suffix.lower().lstrip("."), "sha256": digest(target)}, loaded


def _record_key(kind, character_id=None, variant_id=None, stage=None):
    if kind in {"visual-bible", "cast-plan"}:
        return kind
    safe_id(character_id)
    safe_id(variant_id or "base")
    if kind == "design-card":
        return f"design-card:{character_id}:{variant_id or 'base'}"
    ensure(kind == "prompt-package" and stage in STAGES, "Invalid record kind or stage")
    return f"prompt-package:{stage}:{character_id}:{variant_id or 'base'}"


def _require_approved(state, key):
    value = state["records"].get(key)
    ensure(value and value.get("approval") and not value.get("stale"),
           f"Required approved record missing or stale: {key}")
    return value


def _checked_record(root, state, key):
    value = _require_approved(state, key)
    ensure(digest(read_json(root / value["path"])) == value["sha256"],
           f"Approved record contents changed: {key}")
    ensure(value["approval"].get("sha256") == value["sha256"],
           f"Approval refers to another record version: {key}")
    return value


def _checked_image(root, state, stage, character_id, variant_id):
    image = _approved_image(state, stage, character_id, variant_id)
    ensure(digest(root / image["path"]) == image["sha256"],
           f"Approved image contents changed: {image['id']}")
    review = state["reviews"].get(image["id"])
    ensure(review and digest(read_json(root / review["path"])) == review["sha256"],
           f"Review missing or changed: {image['id']}")
    ensure(image["approval"].get("review_sha256") == review["sha256"],
           f"Image approval refers to another review: {image['id']}")
    ensure(image["approval"].get("image_sha256") == image["sha256"],
           f"Image approval refers to another image version: {image['id']}")
    ensure(read_json(root / review["path"]).get("verdict") == "pass",
           f"Approved image review does not pass: {image['id']}")
    prompt = _checked_record(root, state, _record_key(
        "prompt-package", character_id, variant_id, stage))
    ensure(image["prompt_sha256"] == prompt["sha256"],
           f"Image was generated from another prompt version: {image['id']}")
    return image


def _approved_image(state, stage, character_id, variant_id):
    matching = [image for image in state["images"] if image["stage"] == stage
                and image["character_id"] == character_id
                and image["variant_id"] == variant_id and image.get("approval")
                and not image.get("stale")]
    ensure(len(matching) == 1, f"One approved {stage} image required for {character_id}/{variant_id}")
    return matching[0]


def _invalidate(state, character_id=None, variant_id=None, start="visual-bible"):
    downstream = {
        "visual-bible": {"visual-bible", "cast-plan", "design-card", *STAGES},
        "cast-plan": {"cast-plan", "design-card", *STAGES},
        "design-card": {"design-card", *STAGES},
        "avatar": set(STAGES),
        "expression": {"expression", "execution"},
        "full_body": {"full_body", "execution"},
        "execution": {"execution"},
    }
    affected = downstream[start]
    for key, value in state["records"].items():
        parts = key.split(":")
        if character_id and (len(parts) < 2 or character_id not in parts):
            continue
        if variant_id and len(parts) > 2 and parts[-1] != variant_id:
            continue
        level = parts[1] if parts[0] == "prompt-package" else parts[0]
        if level in affected:
            value["stale"] = True
            value["approval"] = None
    for image in state["images"]:
        if character_id and image["character_id"] != character_id:
            continue
        if variant_id and image["variant_id"] != variant_id:
            continue
        if image["stage"] in affected:
            image["stale"] = True
            image["approval"] = None


def _validate_record(kind, data, state, character_id=None, variant_id=None, stage=None):
    ensure(isinstance(data, dict), "Record must be a JSON object")
    expected = {"visual-bible": "ProjectVisualBibleV1", "cast-plan": "CastPlanV1",
                "design-card": "CharacterDesignCardV1",
                "prompt-package": "CharacterPromptPackageV1"}[kind]
    accepted = {"cast-plan": {"CastPlanV1", "CastPlanV2"},
                "design-card": {"CharacterDesignCardV1", "CharacterDesignCardV2"}}
    ensure(data.get("schema_version") in accepted.get(kind, {expected}),
           f"Expected one of {sorted(accepted.get(kind, {expected}))}")
    require_list(data, "unresolved") if kind != "prompt-package" else None
    if kind == "visual-bible":
        require_text(data, "project_id")
        ensure(data["project_id"] == state["project_id"], "Wrong project_id")
        require_list(data, "world_rules")
        ensure(isinstance(data.get("style"), dict), "style must be an object")
        require_list(data, "evidence")
        for fact in data["evidence"]:
            require_text(fact, "claim")
            require_list(fact, "source_refs")
            ensure(fact["source_refs"], "World evidence needs source_refs")
    elif kind == "cast-plan":
        require_list(data, "characters")
        expected_ids = {row["id"] for row in state["roster"]}
        actual = {row.get("id") for row in data["characters"]}
        ensure(actual == expected_ids, "Cast plan must cover the asset-table roster exactly")
        for item in data["characters"]:
            require_text(item, "design_distinction")
            if data["schema_version"] == "CastPlanV2":
                axes = item.get("recognition_axes")
                ensure(isinstance(axes, dict), "CastPlanV2 rows need recognition_axes")
                for axis in RECOGNITION_AXES:
                    require_text(axes, axis)
    elif kind == "design-card":
        ensure(data.get("character_id") == character_id, "Wrong character_id")
        ensure(data.get("variant_id") == variant_id, "Wrong variant_id")
        ensure(data.get("morphology") in {"human", "humanoid", "nonhuman"},
               "morphology must be human, humanoid or nonhuman")
        for field in ("facts", "inferences", "approved_choices", "identity_invariants"):
            require_list(data, field)
        ensure(isinstance(data.get("appearance"), dict), "appearance must be an object")
        ensure(isinstance(data.get("costume"), dict), "costume must be an object")
        for fact in data["facts"]:
            require_text(fact, "text")
            require_list(fact, "source_refs")
            ensure(fact["source_refs"], "A script fact needs source_refs")
        for idea in data["inferences"]:
            require_text(idea, "text")
            require_list(idea, "basis_refs")
        for choice in data["approved_choices"]:
            require_text(choice, "field")
            require_text(choice, "value")
            require_text(choice, "rationale")
        if data["schema_version"] == "CharacterDesignCardV2":
            axes = data.get("recognition_axes")
            ensure(isinstance(axes, dict), "CharacterDesignCardV2 needs recognition_axes")
            for axis in RECOGNITION_AXES:
                require_text(axes, axis)
            review = data.get("differentiation_review")
            ensure(isinstance(review, dict), "CharacterDesignCardV2 needs differentiation_review")
            require_list(review, "closest_character_ids")
            require_list(review, "shared_features")
            require_list(review, "distinct_features")
            require_text(review, "realism_check")
            if review["closest_character_ids"]:
                ensure(review["distinct_features"],
                       "Describe visible differences from the closest cast members")
    else:
        ensure(data.get("character_id") == character_id and data.get("variant_id") == variant_id,
               "Prompt target does not match character/variant")
        ensure(data.get("stage") == stage, "Prompt stage mismatch")
        ensure(str(data.get("target_model", "")).startswith("gpt-image-2.5"),
               "Prompts must target GPT Image 2.5")
        require_list(data, "reference_images")
        require_list(data, "prompts")
        require_list(data, "acceptance_checks")
        require_text(data, "design_card_sha256")
        ensure(isinstance(data.get("anchor_images"), dict),
               "anchor_images must be a stage-to-SHA object")
        ensure(data["prompts"], "Prompt package is empty")
        ensure(data["acceptance_checks"], "Prompt package needs acceptance checks")
        prompt_ids = []
        for prompt in data["prompts"]:
            require_text(prompt, "id")
            require_text(prompt, "text")
            prompt_ids.append(prompt["id"])
        ensure(len(set(prompt_ids)) == len(prompt_ids), "Prompt IDs must be unique")
        if stage == "avatar":
            ensure(2 <= len(data["prompts"]) <= 3, "Avatar requires 2–3 same-design candidates")
        if stage == "expression":
            require_list(data, "labels")
            ensure(len(data["labels"]) in {9, 16}, "Expression sheet needs 9 or 16 Chinese labels")
            ensure(all(isinstance(x, str) and x.strip() for x in data["labels"]),
                   "Expression labels cannot be empty")
            ensure(all(re.search(r"[\u3400-\u9fff]", x) for x in data["labels"]),
                   "Each expression label must contain Chinese text")
        if stage == "full_body":
            ensure(data.get("head_visible") is True, "Standalone full-body image includes head")
            ensure(data.get("feet_visible") is True, "Standalone full-body image includes feet")
        if stage == "execution" and data.get("morphology") == "human":
            layout = data.get("layout") or {}
            ensure(layout.get("top_left") == "front_face" and
                   layout.get("top_right") == "three_quarter_face_45" and
                   layout.get("bottom_left") == "headless_enlarged_front_costume" and
                   layout.get("bottom_right") == "complete_back_head_to_shoes",
                   "Human execution sheet must use the approved four-panel layout")


@contextlib.contextmanager
def locked_project(root):
    import fcntl
    root = Path(root).expanduser().resolve()
    ensure((root / "project.json").is_file(), f"Not a character project: {root}")
    with (root / ".lock").open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = read_json(root / "project.json")
        ensure(state.get("schema_version") == SCHEMA, "Unsupported project state")
        yield root, state
        state["revision"] += 1
        write_json(root / "project.json", state)


def cmd_init(args):
    root = Path(args.project_root).expanduser().resolve()
    ensure(not root.exists(), f"Project directory already exists: {root}")
    snapshot = None
    if args.snapshot:
        snapshot_path = Path(args.snapshot).expanduser().resolve()
        snapshot = read_json(snapshot_path)
        ensure(snapshot.get("schema_version") == "AssetProjectSnapshotV1",
               "Expected AssetProjectSnapshotV1")
        ensure(isinstance(snapshot.get("sources"), dict), "Snapshot sources missing")
        if args.project_id:
            ensure(args.project_id == snapshot.get("project_id"), "Snapshot project_id mismatch")
        args.project_id = snapshot.get("project_id")
        for kind in ("screenplay", "asset_table", "scene_log"):
            item = snapshot["sources"].get(kind)
            if item:
                source = (snapshot_path.parent / item["path"]).resolve()
                ensure(source.is_file() and digest(source) == item.get("sha256"),
                       f"Snapshot source hash mismatch: {kind}")
                setattr(args, kind, str(source))
        bible = snapshot.get("visual_bible")
        if bible:
            bible_path = (snapshot_path.parent / bible["path"]).resolve()
            ensure(bible_path.is_file() and digest(bible_path) == bible.get("sha256"),
                   "Snapshot visual_bible hash mismatch")
            ensure(isinstance(bible.get("approval"), dict) and
                   bible["approval"].get("operator"), "Snapshot visual_bible is not approved")
    ensure(args.project_id and args.screenplay and args.asset_table,
           "project_id, screenplay and asset_table are required unless supplied by snapshot")
    safe_id(args.project_id)
    # Check the required inputs before creating the project directory.
    checked_screenplay = load_source(args.screenplay)
    checked_assets = load_source(args.asset_table)
    roster_from_assets(checked_assets)
    checked_scene_log = load_source(args.scene_log) if args.scene_log else None
    validate_lineage(args.screenplay, checked_screenplay, checked_assets, checked_scene_log)
    root.mkdir(parents=True)
    inputs, data = {}, {}
    for kind, path in (("screenplay", args.screenplay), ("asset_table", args.asset_table),
                       ("scene_log", args.scene_log)):
        if path:
            inputs[kind], data[kind] = _copy_input(root, kind, path, 1)
    roster = roster_from_assets(data["asset_table"])
    for kind, value in data.items():
        if not (isinstance(value, dict) and kind == "asset_table" and "characters" in value):
            write_json(root / "inputs" / f"rev-001/{kind}.normalized.json", value)
    state = {"schema_version": SCHEMA, "project_id": args.project_id, "created_at": now(),
             "revision": 1, "inputs": inputs, "roster": roster, "records": {},
             "images": [], "reviews": {}, "references": [], "pending_impact": None,
             "decisions": []}
    if snapshot and snapshot.get("visual_bible"):
        bible = snapshot["visual_bible"]
        bible_path = (Path(args.snapshot).expanduser().resolve().parent / bible["path"]).resolve()
        content = read_json(bible_path)
        _validate_record("visual-bible", content, state)
        ensure(not content["unresolved"], "Approved snapshot bible has unresolved items")
        ensure(bible["approval"].get("sha256") == digest(content),
               "Snapshot approval refers to another visual_bible version")
        target = root / "records" / "visual-bible" / f"{digest(content)[:12]}.json"
        write_json(target, content)
        state["records"]["visual-bible"] = {
            "path": str(target.relative_to(root)), "sha256": digest(content),
            "submitted_at": now(), "approval": bible["approval"], "stale": False}
    write_json(root / "project.json", state)
    return {"project_root": str(root), "characters": len(roster),
            "deep_design": [row["id"] for row in roster if row["priority"] == "deep"],
            "scene_log_present": bool(args.scene_log)}


def cmd_status(args):
    root = Path(args.project_root).expanduser().resolve()
    state = read_json(root / "project.json")
    return {"project_id": state["project_id"], "revision": state["revision"],
            "inputs": state["inputs"], "roster": state["roster"],
            "records": {key: {"approved": bool(v.get("approval")), "stale": v.get("stale", False)}
                        for key, v in state["records"].items()},
            "images": [{key: image.get(key) for key in
                        ("id", "stage", "character_id", "variant_id", "approval", "stale")}
                       for image in state["images"]],
            "pending_impact": state["pending_impact"]}


def cmd_submit(args):
    with locked_project(args.project_root) as (root, state):
        ensure(not state["pending_impact"], "Resolve upstream impact before new design decisions")
        character_id = args.character_id
        variant_id = args.variant_id or "base"
        key = _record_key(args.kind, character_id, variant_id, args.stage)
        if character_id:
            ensure(character_id in {row["id"] for row in state["roster"]},
                   "Unknown character ID")
        dependencies = {"cast-plan": ["visual-bible"],
                        "design-card": ["visual-bible", "cast-plan"]}
        for dep in dependencies.get(args.kind, []):
            _checked_record(root, state, dep)
        if args.kind == "prompt-package":
            card_key = _record_key("design-card", character_id, variant_id)
            card_record = _checked_record(root, state, card_key)
            anchors = {}
            if args.stage in {"expression", "full_body", "execution"}:
                anchors["avatar"] = _checked_image(root, state, "avatar", character_id, variant_id)["sha256"]
            if args.stage == "execution":
                for anchor_stage in ("expression", "full_body"):
                    anchors[anchor_stage] = _checked_image(
                        root, state, anchor_stage, character_id, variant_id)["sha256"]
        content = read_json(args.file)
        _validate_record(args.kind, content, state, character_id, variant_id, args.stage)
        if args.kind == "prompt-package":
            ensure(content["design_card_sha256"] == card_record["sha256"],
                   "Prompt package refers to a different design card version")
            ensure(content["anchor_images"] == anchors,
                   "Prompt package anchor image versions do not match the current approvals")
            card = read_json(root / state["records"][
                _record_key("design-card", character_id, variant_id)]["path"])
            if args.stage == "execution":
                ensure(content.get("morphology") == card["morphology"],
                       "Execution prompt morphology must match the approved design card")
                if card["morphology"] != "human":
                    ensure(isinstance(card.get("execution_layout"), dict) and
                           card["execution_layout"],
                           "Nonhuman design card needs an approved execution_layout")
                    ensure(content.get("layout") == card["execution_layout"],
                           "Execution layout must match the approved design card")
        incoming = digest(content)
        prior = state["records"].get(key)
        if prior and prior["sha256"] == incoming and not prior.get("stale"):
            return {"key": key, "status": "unchanged", "sha256": incoming}
        if prior:
            level = args.stage if args.kind == "prompt-package" else args.kind
            _invalidate(state, character_id, variant_id if character_id else None, level)
        path = root / "records" / key.replace(":", "/") / f"{incoming[:12]}.json"
        write_json(path, content)
        state["records"][key] = {"path": str(path.relative_to(root)), "sha256": incoming,
                                 "submitted_at": now(), "approval": None, "stale": False}
        if args.kind == "prompt-package":
            state["records"][key]["approval"] = {"operator": "system:contract-check",
                                                    "at": now(), "sha256": incoming}
        return {"key": key, "sha256": incoming,
                "status": "ready" if args.kind == "prompt-package" else "awaiting-approval"}


def cmd_approve_record(args):
    with locked_project(args.project_root) as (root, state):
        ensure(not state["pending_impact"], "Unresolved upstream impact")
        ensure(args.kind != "prompt-package", "Prompt packages become ready after contract check")
        key = _record_key(args.kind, args.character_id, args.variant_id or "base")
        value = state["records"].get(key)
        ensure(value and not value.get("stale"), f"Record is missing or stale: {key}")
        ensure(digest(read_json(root / value["path"])) == value["sha256"],
               "Record contents changed after submission")
        ensure(not read_json(root / value["path"])["unresolved"],
               "Resolve pending design decisions before approval")
        if args.kind == "cast-plan":
            _require_approved(state, "visual-bible")
        elif args.kind == "design-card":
            _require_approved(state, "cast-plan")
        require_text({"operator": args.operator}, "operator")
        value["approval"] = {"operator": args.operator, "at": now(), "sha256": value["sha256"]}
        state["decisions"].append({"kind": "approve-record", "key": key,
                                   "operator": args.operator, "at": now(),
                                   "sha256": value["sha256"]})
        return {"key": key, "approved": True}


def cmd_import_reference(args):
    source = Path(args.path).expanduser().resolve()
    ensure(source.is_file() and source.suffix.lower() in IMAGE_SUFFIXES,
           "Reference must be PNG, JPG or WebP")
    with locked_project(args.project_root) as (root, state):
        if args.character_id:
            ensure(args.character_id in {x["id"] for x in state["roster"]}, "Unknown character")
        ident = digest(source)[:16]
        target = root / "references" / f"{ident}{source.suffix.lower()}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
        row = {"id": ident, "path": str(target.relative_to(root)), "sha256": digest(source),
               "role": args.role, "desired_strength": args.desired_strength,
               "character_id": args.character_id, "imported_at": now()}
        if not any(x["id"] == ident and x["role"] == args.role for x in state["references"]):
            state["references"].append(row)
        return row


def cmd_import_image(args):
    ensure(args.stage in STAGES, "Invalid image stage")
    source = Path(args.path).expanduser().resolve()
    ensure(source.is_file() and source.suffix.lower() in IMAGE_SUFFIXES,
           "Image must be PNG, JPG or WebP")
    with locked_project(args.project_root) as (root, state):
        ensure(not state["pending_impact"], "Resolve upstream impact first")
        variant_id = args.variant_id or "base"
        key = _record_key("prompt-package", args.character_id, variant_id, args.stage)
        _require_approved(state, key)
        sha = digest(source)
        ident = f"{args.stage}-{sha[:16]}"
        target = root / "images" / args.character_id / variant_id / args.stage / f"{sha}{source.suffix.lower()}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
        existing = next((x for x in state["images"] if x["id"] == ident and
                         x["character_id"] == args.character_id and
                         x["variant_id"] == variant_id), None)
        if existing:
            return existing
        row = {"id": ident, "stage": args.stage, "character_id": args.character_id,
               "variant_id": variant_id, "path": str(target.relative_to(root)),
               "sha256": sha, "prompt_sha256": state["records"][key]["sha256"],
               "imported_at": now(), "approval": None, "stale": False}
        state["images"].append(row)
        return row


def _image(state, ident):
    item = next((x for x in state["images"] if x["id"] == ident), None)
    ensure(item, f"Unknown image: {ident}")
    ensure(not item.get("stale"), f"Image is stale: {ident}")
    return item


def cmd_submit_review(args):
    with locked_project(args.project_root) as (root, state):
        image = _image(state, args.image_id)
        ensure(digest(root / image["path"]) == image["sha256"],
               "Imported image contents changed")
        report = read_json(args.file)
        ensure(report.get("schema_version") == "CharacterImageReviewV1", "Wrong review schema")
        ensure(report.get("image_sha256") == image["sha256"] and
               report.get("stage") == image["stage"], "Review target mismatch")
        ensure(report.get("verdict") in {"pass", "revise", "uncertain"}, "Invalid verdict")
        for key in ("factual_conflicts", "identity_issues", "layout_issues",
                    "label_issues", "blocking_issues", "adoption_proposals"):
            require_list(report, key)
        if report["verdict"] == "pass":
            ensure(not report["blocking_issues"] and not report["factual_conflicts"] and
                   not report["identity_issues"] and not report["layout_issues"] and
                   not report["label_issues"], "A passing review cannot contain unresolved defects")
        review_sha = digest(report)
        path = root / "reviews" / f"{image['id']}-{review_sha[:12]}.json"
        write_json(path, report)
        state["reviews"][image["id"]] = {"path": str(path.relative_to(root)),
                                          "sha256": review_sha, "submitted_at": now()}
        image["approval"] = None
        return {"image_id": image["id"], "verdict": report["verdict"],
                "review_sha256": review_sha}


def cmd_approve_image(args):
    with locked_project(args.project_root) as (root, state):
        ensure(not state["pending_impact"], "Unresolved upstream impact")
        image = _image(state, args.image_id)
        entry = state["reviews"].get(image["id"])
        ensure(entry, "Image must be reviewed first")
        ensure(digest(root / image["path"]) == image["sha256"],
               "Imported image contents changed")
        report = read_json(root / entry["path"])
        ensure(digest(report) == entry["sha256"], "Review contents changed")
        ensure(report["verdict"] == "pass" and not report["blocking_issues"],
               "Image review has not passed")
        require_text({"operator": args.operator}, "operator")
        previous = [x for x in state["images"] if x is not image and x["stage"] == image["stage"]
                    and x["character_id"] == image["character_id"] and
                    x["variant_id"] == image["variant_id"] and x.get("approval")]
        if previous:
            if image["stage"] == "avatar":
                _invalidate(state, image["character_id"], image["variant_id"], "expression")
                _invalidate(state, image["character_id"], image["variant_id"], "full_body")
            else:
                _invalidate(state, image["character_id"], image["variant_id"], "execution")
            for old in previous:
                old["approval"] = None
        image["approval"] = {"operator": args.operator, "at": now(),
                             "image_sha256": image["sha256"],
                             "review_sha256": entry["sha256"]}
        state["decisions"].append({"kind": "approve-image", "image_id": image["id"],
                                   "operator": args.operator, "at": now(),
                                   "image_sha256": image["sha256"],
                                   "review_sha256": entry["sha256"]})
        return {"image_id": image["id"], "approved": True}


def cmd_refresh(args):
    with locked_project(args.project_root) as (root, state):
        ensure(not state["pending_impact"], "Resolve current impact before another refresh")
        revision = state["revision"] + 1
        old_roster = {x["id"]: x for x in state["roster"]}
        inputs = copy.deepcopy(state["inputs"])
        changed = []
        new_data = {}
        for kind, path in (("screenplay", args.screenplay), ("asset_table", args.asset_table),
                           ("scene_log", args.scene_log)):
            if path:
                candidate = Path(path).expanduser().resolve()
                if inputs.get(kind, {}).get("sha256") != digest(candidate):
                    inputs[kind], new_data[kind] = _copy_input(root, kind, path, revision)
                    changed.append(kind)
        ensure(changed, "No changed input files")
        if "asset_table" in changed:
            roster = roster_from_assets(new_data["asset_table"])
            new_ids = {x["id"] for x in roster}
            direct = [x["id"] for x in roster if old_roster.get(x["id"], {}).get("asset_digest")
                      != x["asset_digest"]]
            removed = sorted(set(old_roster) - new_ids)
            state["roster"] = roster
        else:
            direct, removed = [], []
        for ident in set(direct + removed):
            _invalidate(state, ident, None, "design-card")
        state["inputs"] = inputs
        state["pending_impact"] = {"changed_inputs": changed,
                                   "directly_changed_characters": direct,
                                   "removed_characters": removed,
                                   "needs_context_review": "screenplay" in changed or "scene_log" in changed,
                                   "created_at": now()}
        return state["pending_impact"]


def cmd_resolve_impact(args):
    with locked_project(args.project_root) as (_root, state):
        ensure(state["pending_impact"], "No pending upstream impact")
        known = {x["id"] for x in state["roster"]}
        affected = set(args.affected or [])
        ensure(affected <= known, f"Unknown affected IDs: {sorted(affected - known)}")
        if args.global_style:
            _invalidate(state, start="visual-bible")
        else:
            for ident in affected:
                _invalidate(state, ident, None, "design-card")
        state["decisions"].append({"kind": "resolve-impact", "operator": args.operator,
                                   "at": now(), "affected": sorted(affected),
                                   "global_style": bool(args.global_style),
                                   "reviewed_inputs": state["pending_impact"]["changed_inputs"]})
        state["pending_impact"] = None
        return {"affected": sorted(affected), "global_style": bool(args.global_style)}


def cmd_package(args):
    root = Path(args.project_root).expanduser().resolve()
    state = read_json(root / "project.json")
    ensure(not state["pending_impact"], "Unresolved upstream impact")
    ident = args.character_id
    variant = args.variant_id or "base"
    for kind, source in state["inputs"].items():
        ensure(digest(root / source["path"]) == source["sha256"],
               f"Imported {kind} file changed after intake")
    _checked_record(root, state, "visual-bible")
    _checked_record(root, state, "cast-plan")
    _checked_record(root, state, _record_key("design-card", ident, variant))
    records = [state["records"][_record_key("design-card", ident, variant)]]
    images = []
    for stage in STAGES:
        records.append(_checked_record(root, state, _record_key("prompt-package", ident, variant, stage)))
        images.append(_checked_image(root, state, stage, ident, variant))
    out = Path(args.output).expanduser().resolve()
    ensure(not out.exists(), f"Output already exists: {out}")
    out.mkdir(parents=True)
    copied = []
    for item in [state["records"]["visual-bible"], state["records"]["cast-plan"], *records]:
        source = root / item["path"]
        target = out / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append({"path": str(target.relative_to(out)), "sha256": digest(target)})
    for image in images:
        review = state["reviews"][image["id"]]
        for item in (image, review):
            source = root / item["path"]
            target = out / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append({"path": str(target.relative_to(out)), "sha256": digest(target)})
    relevant_refs = [x for x in state["references"] if x.get("character_id") in
                     {None, ident}]
    for item in relevant_refs:
        source = root / item["path"]
        ensure(digest(source) == item["sha256"],
               f"Reference image contents changed: {item['id']}")
        target = out / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append({"path": str(target.relative_to(out)), "sha256": digest(target)})
    plugin_root = Path(__file__).resolve().parents[1]
    for relative in ("knowledge/source-register.json", "sources.lock.json"):
        source = plugin_root / relative
        ensure(source.is_file(), f"Plugin provenance file missing: {relative}")
        target = out / "plugin-provenance" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append({"path": str(target.relative_to(out)), "sha256": digest(target)})
    image_ids = {x["id"] for x in images}
    record_keys = {"visual-bible", "cast-plan", _record_key("design-card", ident, variant)}
    record_keys.update(_record_key("prompt-package", ident, variant, stage) for stage in STAGES)
    manifest = {"schema_version": "CharacterAssetPackV1", "plugin_version": "0.1.3",
                "project_id": state["project_id"],
                "character_id": ident, "variant_id": variant, "created_at": now(),
                "input_sources": state["inputs"],
                "approved_images": {x["stage"]: {"path": x["path"], "sha256": x["sha256"],
                                                  "approval": x["approval"],
                                                  "purpose": {"avatar": "身份锚点",
                                                              "expression": "剧情表情参考",
                                                              "full_body": "完整全身造型",
                                                              "execution": "制作执行参考板"}[x["stage"]]}
                                    for x in images},
                "record_approvals": {key: state["records"][key]["approval"]
                                     for key in sorted(record_keys)},
                "files": copied, "decisions": [x for x in state["decisions"]
                                                if x.get("key") in record_keys or
                                                x.get("image_id") in image_ids],
                "reference_images": relevant_refs}
    write_json(out / "manifest.json", manifest)
    return {"asset_pack": str(out), "files": len(copied) + 1}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Import project sources")
    init.add_argument("--project-root", required=True)
    init.add_argument("--project-id")
    init.add_argument("--screenplay")
    init.add_argument("--asset-table")
    init.add_argument("--scene-log")
    init.add_argument("--snapshot", help="Approved AssetProjectSnapshotV1 from the parent plugin")
    status = sub.add_parser("status")
    status.add_argument("--project-root", required=True)
    submit = sub.add_parser("submit", help="Register a structured design/prompt draft")
    submit.add_argument("--project-root", required=True)
    submit.add_argument("--kind", choices=("visual-bible", "cast-plan", "design-card", "prompt-package"), required=True)
    submit.add_argument("--file", required=True)
    submit.add_argument("--character-id")
    submit.add_argument("--variant-id", default="base")
    submit.add_argument("--stage", choices=STAGES)
    approve = sub.add_parser("approve-record")
    approve.add_argument("--project-root", required=True)
    approve.add_argument("--kind", choices=("visual-bible", "cast-plan", "design-card"), required=True)
    approve.add_argument("--character-id")
    approve.add_argument("--variant-id", default="base")
    approve.add_argument("--operator", required=True)
    reference = sub.add_parser("import-reference")
    reference.add_argument("--project-root", required=True)
    reference.add_argument("--path", required=True)
    reference.add_argument("--role", choices=("identity", "costume", "style", "inspiration"), required=True)
    reference.add_argument("--desired-strength", required=True)
    reference.add_argument("--character-id")
    image = sub.add_parser("import-image")
    image.add_argument("--project-root", required=True)
    image.add_argument("--path", required=True)
    image.add_argument("--stage", choices=STAGES, required=True)
    image.add_argument("--character-id", required=True)
    image.add_argument("--variant-id", default="base")
    review = sub.add_parser("submit-review")
    review.add_argument("--project-root", required=True)
    review.add_argument("--image-id", required=True)
    review.add_argument("--file", required=True)
    approve_image = sub.add_parser("approve-image")
    approve_image.add_argument("--project-root", required=True)
    approve_image.add_argument("--image-id", required=True)
    approve_image.add_argument("--operator", required=True)
    refresh = sub.add_parser("refresh")
    refresh.add_argument("--project-root", required=True)
    refresh.add_argument("--screenplay")
    refresh.add_argument("--asset-table")
    refresh.add_argument("--scene-log")
    impact = sub.add_parser("resolve-impact")
    impact.add_argument("--project-root", required=True)
    impact.add_argument("--affected", nargs="*")
    impact.add_argument("--global-style", action="store_true")
    impact.add_argument("--operator", required=True)
    release = sub.add_parser("package")
    release.add_argument("--project-root", required=True)
    release.add_argument("--character-id", required=True)
    release.add_argument("--variant-id", default="base")
    release.add_argument("--output", required=True)
    return parser


def main():
    args = build_parser().parse_args()
    actions = {"init": cmd_init, "status": cmd_status, "submit": cmd_submit,
               "approve-record": cmd_approve_record, "import-reference": cmd_import_reference,
               "import-image": cmd_import_image, "submit-review": cmd_submit_review,
               "approve-image": cmd_approve_image, "refresh": cmd_refresh,
               "resolve-impact": cmd_resolve_impact, "package": cmd_package}
    try:
        print(json.dumps(actions[args.command](args), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

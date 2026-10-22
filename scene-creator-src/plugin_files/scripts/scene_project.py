#!/usr/bin/env python3
"""Local, deterministic state and approval gates for scene assets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

KINDS = {"visual-bible": "ProjectVisualBibleV1", "design": "SceneDesignCardV1",
         "prompt": "ScenePromptPackageV1", "review": "SceneImageReviewV1"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def fail(message: str) -> None:
    raise SystemExit(message)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def input_fingerprint(state: dict) -> str:
    versions = {name: item["sha256"] for name, item in state["inputs"].items()}
    return hashlib.sha256(json.dumps(versions, sort_keys=True).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail(f"Cannot read JSON {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"Expected JSON object: {path}")
    return value


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def safe_id(value: str) -> str:
    if not value or not all(c.isascii() and (c.isalnum() or c in "-_") for c in value):
        fail(f"ID must use ASCII letters, numbers, - or _: {value!r}")
    return value


def state_path(root: Path) -> Path:
    return root / "project.json"


def read_state(root: Path) -> dict:
    path = state_path(root)
    if not path.is_file():
        fail(f"Project not initialized: {root}")
    state = load_json(path)
    if state.get("schema_version") != "SceneProjectStateV1":
        fail("Unsupported project state")
    for source in state["inputs"].values():
        stored = root / source["stored_path"]
        if not stored.is_file() or digest(stored) != source["sha256"]:
            fail(f"Stored input changed: {source['stored_path']}")
    for rows in state["records"].values():
        for record in rows:
            path = root / record["path"]
            if not path.is_file() or digest(path) != record["sha256"]:
                fail(f"Recorded document changed: {record['path']}")
    for image in state["images"]:
        path = root / image["path"]
        if not path.is_file() or digest(path) != image["sha256"]:
            fail(f"Imported image changed: {image['path']}")
    if state.get("stale"):
        fail("Inputs were refreshed; resubmit and approve the visual bible before continuing")
    return state


def key(kind: str, scene_id: str | None = None, variant_id: str | None = None,
        image_id: str | None = None) -> str:
    if kind == "visual-bible":
        return kind
    if not scene_id or not variant_id:
        fail(f"{kind} requires --scene-id and --variant-id")
    parts = [kind, safe_id(scene_id), safe_id(variant_id)]
    if kind == "review":
        if not image_id:
            fail("review requires --image-id")
        parts.append(safe_id(image_id))
    return "/".join(parts)


def latest(state: dict, record_key: str) -> dict | None:
    rows = state["records"].get(record_key, [])
    return rows[-1] if rows else None


def approved(state: dict, record_key: str) -> dict:
    item = latest(state, record_key)
    if item is None or not item.get("approval"):
        fail(f"Approved record required: {record_key}")
    return item


def require_fields(data: dict, names: tuple[str, ...]) -> None:
    for name in names:
        if name not in data:
            fail(f"Missing required field: {name}")


def check_document(kind: str, data: dict, state: dict, args) -> None:
    if data.get("schema_version") != KINDS[kind]:
        fail(f"Expected schema_version {KINDS[kind]}")
    if kind == "visual-bible":
        require_fields(data, ("project_id", "world_rules", "style", "evidence", "unresolved"))
        if data["project_id"] != state["project_id"] or not isinstance(data["style"], dict):
            fail("Visual bible project_id/style mismatch")
        if not isinstance(data["style"].get("fantasy_scale_enabled"), bool):
            fail("style.fantasy_scale_enabled must be a boolean")
        if any(not isinstance(data[name], list) for name in ("world_rules", "evidence", "unresolved")):
            fail("Visual bible rules, evidence and unresolved must be lists")
        if not data["evidence"]:
            fail("Visual bible needs at least one source-backed observation")
    elif kind == "design":
        require_fields(data, ("scene_id", "variant_id", "visual_bible_sha256", "facts", "approved_choices",
                              "primary_space", "scale_cues", "composition",
                              "continuity_invariants", "source_refs", "unresolved",
                              "fantasy_scale_enabled"))
        visual = approved(state, "visual-bible")
        bible = load_json(args.project_root / visual["path"])
        if data["scene_id"] != args.scene_id or data["variant_id"] != args.variant_id:
            fail("Design scene_id/variant_id mismatch")
        if data["visual_bible_sha256"] != visual["sha256"]:
            fail("Design must use current approved visual bible SHA")
        if not isinstance(data["fantasy_scale_enabled"], bool):
            fail("fantasy_scale_enabled must be a boolean")
        if data["fantasy_scale_enabled"] and not bible["style"]["fantasy_scale_enabled"]:
            fail("Fantasy scale must be approved in the visual bible")
        if not isinstance(data["facts"], list) or not data["facts"] or any(
            not isinstance(item, dict) or not item.get("source_refs") for item in data["facts"]):
            fail("Each scene fact needs source_refs")
        if any(not isinstance(data[name], list) for name in
               ("approved_choices", "scale_cues", "continuity_invariants", "source_refs", "unresolved")):
            fail("Design lists have an invalid type")
        if not data["source_refs"]:
            fail("Design needs scene source_refs")
        if not isinstance(data["primary_space"], dict) or not isinstance(data["composition"], dict):
            fail("primary_space and composition must be objects")
    elif kind == "prompt":
        require_fields(data, ("scene_id", "variant_id", "design_card_sha256", "target_model",
                              "reference_images", "prompts", "acceptance_checks"))
        design = approved(state, key("design", args.scene_id, args.variant_id))
        if data["scene_id"] != args.scene_id or data["variant_id"] != args.variant_id:
            fail("Prompt scene_id/variant_id mismatch")
        if data["design_card_sha256"] != design["sha256"]:
            fail("Prompt must use current approved design SHA")
        if (not isinstance(data["target_model"], str) or not data["target_model"].strip()
            or not isinstance(data["prompts"], list) or not data["prompts"]
            or not isinstance(data["acceptance_checks"], list) or not data["acceptance_checks"]
            or not isinstance(data["reference_images"], list)):
            fail("Prompt text and acceptance checks cannot be empty")
        if any(not isinstance(item, dict) or not item.get("id") or not item.get("text")
               for item in data["prompts"]):
            fail("Each prompt requires id and text")
    else:
        require_fields(data, ("image_sha256", "verdict", "factual_conflicts", "continuity_issues",
                              "space_scale_issues", "layout_issues", "blocking_issues",
                              "adoption_proposals"))
        image = next((row for row in state["images"] if row["id"] == args.image_id), None)
        if image is None or (image["scene_id"], image["variant_id"]) != (args.scene_id, args.variant_id):
            fail("Review image ID does not match scene/variant")
        if data["image_sha256"] != image["sha256"]:
            fail("Review image SHA does not match imported image")
        if data["verdict"] not in {"pass", "revise", "uncertain"}:
            fail("Invalid review verdict")
        if any(not isinstance(data[field], list) for field in
               ("factual_conflicts", "continuity_issues", "space_scale_issues",
                "layout_issues", "blocking_issues", "adoption_proposals")):
            fail("Review issue fields must be lists")
        if data["verdict"] == "pass" and any(data[field] for field in
            ("factual_conflicts", "continuity_issues", "space_scale_issues", "layout_issues", "blocking_issues")):
            fail("Pass review cannot contain defects")


def command_init(args) -> dict:
    root = args.project_root.resolve()
    if state_path(root).exists():
        fail(f"Project already initialized: {root}")
    safe_id(args.project_id)
    inputs = {}
    for label in ("screenplay", "asset_table", "scene_log"):
        source = getattr(args, label)
        if source is None:
            continue
        source = source.resolve()
        if not source.is_file():
            fail(f"Missing input: {source}")
        target = root / "inputs" / (label + source.suffix.lower())
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        inputs[label] = {"name": source.name, "stored_path": str(target.relative_to(root)),
                         "sha256": digest(target)}
    state = {"schema_version": "SceneProjectStateV1", "project_id": args.project_id,
             "created_at": now(), "inputs": inputs, "stale": False,
             "records": {}, "images": [], "events": []}
    save_json(state_path(root), state)
    return {"project_root": str(root), "inputs": inputs}


def command_submit(args) -> dict:
    root = args.project_root.resolve()
    state = read_state(root)
    data = load_json(args.file)
    check_document(args.kind, data, state, args)
    record_key = key(args.kind, args.scene_id, args.variant_id, args.image_id)
    version = len(state["records"].get(record_key, [])) + 1
    target = root / "records" / record_key / f"v{version:03d}.json"
    if target.exists():
        fail(f"Record path already exists: {target}")
    save_json(target, data)
    record = {"version": version, "path": str(target.relative_to(root)),
              "sha256": digest(target), "input_fingerprint": input_fingerprint(state),
              "created_at": now(), "approval": None}
    state["records"].setdefault(record_key, []).append(record)
    if args.kind == "visual-bible":
        for rows in state["records"].values():
            for row in rows:
                if row is not record:
                    row["approval"] = None
        for image in state["images"]:
            image["approval"] = None
    elif args.kind in {"design", "prompt"}:
        prefix = "/".join((safe_id(args.scene_id), safe_id(args.variant_id)))
        for rk, rows in state["records"].items():
            if rk in {f"prompt/{prefix}"} or rk.startswith(f"review/{prefix}/"):
                for row in rows:
                    row["approval"] = None
        for image in state["images"]:
            if (image["scene_id"], image["variant_id"]) == (args.scene_id, args.variant_id):
                image["approval"] = None
    state["events"].append({"at": now(), "type": "submit", "key": record_key,
                            "version": version, "sha256": record["sha256"]})
    save_json(state_path(root), state)
    return {"key": record_key, **record}


def command_approve_record(args) -> dict:
    root = args.project_root.resolve()
    state = read_state(root)
    record_key = key(args.kind, args.scene_id, args.variant_id)
    record = latest(state, record_key)
    if record is None:
        fail(f"No record to approve: {record_key}")
    if record.get("input_fingerprint") != input_fingerprint(state):
        fail("Record was submitted against an older input version")
    data = load_json(root / record["path"])
    if data.get("unresolved"):
        fail("Resolve open questions before approval")
    if args.kind == "design":
        visual = approved(state, "visual-bible")
        if data["visual_bible_sha256"] != visual["sha256"]:
            fail("Design belongs to an older visual bible")
    approval = {"operator": args.operator, "at": now(), "sha256": record["sha256"]}
    record["approval"] = approval
    state["events"].append({"at": now(), "type": "approve-record", "key": record_key,
                            "version": record["version"], "operator": args.operator})
    save_json(state_path(root), state)
    return {"key": record_key, "approval": approval}


def command_add_image(args) -> dict:
    root = args.project_root.resolve()
    state = read_state(root)
    safe_id(args.scene_id); safe_id(args.variant_id)
    approved(state, key("design", args.scene_id, args.variant_id))
    prompt = latest(state, key("prompt", args.scene_id, args.variant_id))
    if prompt is None:
        fail("Create a prompt package before importing an image")
    if prompt.get("input_fingerprint") != input_fingerprint(state):
        fail("Prompt belongs to older inputs")
    design = approved(state, key("design", args.scene_id, args.variant_id))
    if load_json(root / prompt["path"])["design_card_sha256"] != design["sha256"]:
        fail("Prompt belongs to an older design card")
    source = args.file.resolve()
    if not source.is_file() or source.suffix.lower() not in IMAGE_SUFFIXES or source.stat().st_size == 0:
        fail("Image must be a nonempty PNG, JPEG or WebP file")
    image_id = f"img-{len(state['images']) + 1:04d}"
    target = root / "images" / args.scene_id / args.variant_id / (image_id + source.suffix.lower())
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    row = {"id": image_id, "scene_id": args.scene_id, "variant_id": args.variant_id,
           "path": str(target.relative_to(root)), "sha256": digest(target),
           "prompt_sha256": prompt["sha256"], "imported_at": now(), "approval": None}
    state["images"].append(row)
    state["events"].append({"at": now(), "type": "add-image", "image_id": image_id,
                            "sha256": row["sha256"]})
    save_json(state_path(root), state)
    return row


def command_approve_image(args) -> dict:
    root = args.project_root.resolve()
    state = read_state(root)
    image = next((row for row in state["images"] if row["id"] == args.image_id), None)
    if image is None or (image["scene_id"], image["variant_id"]) != (args.scene_id, args.variant_id):
        fail("Unknown image for scene/variant")
    review = latest(state, key("review", args.scene_id, args.variant_id, args.image_id))
    if review is None:
        fail("Image review required")
    if review.get("input_fingerprint") != input_fingerprint(state):
        fail("Review belongs to older inputs")
    report = load_json(root / review["path"])
    if report["verdict"] != "pass" or report["image_sha256"] != image["sha256"]:
        fail("Only a current pass review can be approved")
    design = approved(state, key("design", args.scene_id, args.variant_id))
    prompt = latest(state, key("prompt", args.scene_id, args.variant_id))
    if image["prompt_sha256"] != prompt["sha256"]:
        fail("Image belongs to an older prompt package")
    if prompt.get("input_fingerprint") != input_fingerprint(state):
        fail("Prompt belongs to older inputs")
    if load_json(root / prompt["path"])["design_card_sha256"] != design["sha256"]:
        fail("Prompt belongs to an older design card")
    image["approval"] = {"operator": args.operator, "at": now(),
                         "sha256": image["sha256"], "review_sha256": review["sha256"]}
    state["events"].append({"at": now(), "type": "approve-image", "image_id": args.image_id,
                            "operator": args.operator})
    save_json(state_path(root), state)
    return {"image_id": args.image_id, "approval": image["approval"]}


def command_refresh(args) -> dict:
    root = args.project_root.resolve()
    state = read_state(root)
    changed = []
    for label in ("screenplay", "asset_table", "scene_log"):
        source = getattr(args, label)
        if source is None:
            continue
        source = source.resolve()
        if not source.is_file():
            fail(f"Missing input: {source}")
        current = state["inputs"].get(label)
        new_hash = digest(source)
        if current and current["sha256"] == new_hash:
            continue
        target = root / "inputs" / (label + source.suffix.lower())
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        state["inputs"][label] = {"name": source.name, "stored_path": str(target.relative_to(root)),
                                  "sha256": new_hash}
        changed.append(label)
    if changed:
        for rows in state["records"].values():
            for row in rows:
                row["approval"] = None
        for image in state["images"]:
            image["approval"] = None
        state["events"].append({"at": now(), "type": "refresh", "changed_inputs": changed,
                                "policy": "conservative approval invalidation"})
    save_json(state_path(root), state)
    return {"changed_inputs": changed, "approvals_invalidated": bool(changed)}


def command_package(args) -> dict:
    root = args.project_root.resolve()
    state = read_state(root)
    visual = approved(state, "visual-bible")
    design = approved(state, key("design", args.scene_id, args.variant_id))
    if load_json(root / design["path"])["visual_bible_sha256"] != visual["sha256"]:
        fail("Design belongs to an older visual bible")
    prompt = latest(state, key("prompt", args.scene_id, args.variant_id))
    if (prompt is None or prompt.get("input_fingerprint") != input_fingerprint(state)
        or load_json(root / prompt["path"])["design_card_sha256"] != design["sha256"]):
        fail("Current prompt package required")
    images = [row for row in state["images"] if row["scene_id"] == args.scene_id
              and row["variant_id"] == args.variant_id and row.get("approval")
              and row["prompt_sha256"] == prompt["sha256"]]
    if not images:
        fail("Approved current image required")
    for image in images:
        review = latest(state, key("review", args.scene_id, args.variant_id, image["id"]))
        if review is None or review["sha256"] != image["approval"]["review_sha256"]:
            fail("Image review changed after approval")
    output = args.output.resolve()
    if output.exists():
        fail(f"Output already exists: {output}")
    output.mkdir(parents=True)
    copied = {}
    for label, record in (("visual-bible", visual), ("design", design), ("prompt", prompt)):
        source = root / record["path"]
        target = output / (label + ".json")
        shutil.copy2(source, target)
        copied[label] = {"path": target.name, "sha256": digest(target),
                         "approval": record.get("approval")}
    image_rows = []
    for image in images:
        review = latest(state, key("review", args.scene_id, args.variant_id, image["id"]))
        for label, source in ((image["id"], root / image["path"]),
                              (image["id"] + "-review", root / review["path"])):
            target = output / (label + source.suffix)
            shutil.copy2(source, target)
        image_rows.append({"id": image["id"], "path": image["id"] + (root / image["path"]).suffix,
                           "sha256": image["sha256"], "approval": image["approval"],
                           "review_path": image["id"] + "-review.json", "review_sha256": review["sha256"]})
    manifest = {"schema_version": "SceneAssetPackV1", "plugin_version": "0.1.0",
                "project_id": state["project_id"], "scene_id": args.scene_id,
                "variant_id": args.variant_id, "created_at": now(),
                "inputs": {name: {"name": item["name"], "sha256": item["sha256"]}
                           for name, item in state["inputs"].items()},
                "records": copied, "images": image_rows}
    receipts = Path(__file__).resolve().parents[1] / "sources.lock.json"
    if receipts.is_file():
        target = output / "sources.lock.json"
        shutil.copy2(receipts, target)
        manifest["source_receipts"] = {"path": target.name, "sha256": digest(target)}
    save_json(output / "manifest.json", manifest)
    return {"output": str(output), "image_count": len(image_rows)}


def command_status(args) -> dict:
    root = args.project_root.resolve()
    state = read_state(root)
    return {"project_id": state["project_id"], "inputs": state["inputs"],
            "records": {name: {"versions": len(rows), "latest_approved": bool(rows[-1].get("approval"))}
                        for name, rows in state["records"].items()},
            "images": [{"id": row["id"], "scene_id": row["scene_id"],
                        "variant_id": row["variant_id"], "approved": bool(row.get("approval"))}
                       for row in state["images"]]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--project-root", type=Path, required=True)
    init.add_argument("--project-id", required=True)
    init.add_argument("--screenplay", type=Path, required=True)
    init.add_argument("--asset-table", type=Path, required=True)
    init.add_argument("--scene-log", type=Path)
    refresh = commands.add_parser("refresh")
    refresh.add_argument("--project-root", type=Path, required=True)
    for label in ("screenplay", "asset-table", "scene-log"):
        refresh.add_argument("--" + label, type=Path)
    submit = commands.add_parser("submit")
    submit.add_argument("--project-root", type=Path, required=True)
    submit.add_argument("--kind", choices=list(KINDS), required=True)
    submit.add_argument("--file", type=Path, required=True)
    submit.add_argument("--scene-id")
    submit.add_argument("--variant-id", default="base")
    submit.add_argument("--image-id")
    approve_record = commands.add_parser("approve-record")
    approve_record.add_argument("--project-root", type=Path, required=True)
    approve_record.add_argument("--kind", choices=["visual-bible", "design"], required=True)
    approve_record.add_argument("--scene-id")
    approve_record.add_argument("--variant-id", default="base")
    approve_record.add_argument("--operator", required=True)
    add_image = commands.add_parser("add-image")
    add_image.add_argument("--project-root", type=Path, required=True)
    add_image.add_argument("--scene-id", required=True)
    add_image.add_argument("--variant-id", default="base")
    add_image.add_argument("--file", type=Path, required=True)
    approve_image = commands.add_parser("approve-image")
    approve_image.add_argument("--project-root", type=Path, required=True)
    approve_image.add_argument("--scene-id", required=True)
    approve_image.add_argument("--variant-id", default="base")
    approve_image.add_argument("--image-id", required=True)
    approve_image.add_argument("--operator", required=True)
    package = commands.add_parser("package")
    package.add_argument("--project-root", type=Path, required=True)
    package.add_argument("--scene-id", required=True)
    package.add_argument("--variant-id", default="base")
    package.add_argument("--output", type=Path, required=True)
    status = commands.add_parser("status")
    status.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    if hasattr(args, "operator") and not args.operator.strip():
        fail("Operator cannot be empty")
    result = {"init": command_init, "refresh": command_refresh, "submit": command_submit,
              "approve-record": command_approve_record, "add-image": command_add_image,
              "approve-image": command_approve_image, "package": command_package,
              "status": command_status}[args.command](args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

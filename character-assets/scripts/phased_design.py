"""Scoped design approvals for the optional v0.2.5 workflow.

The model supplies creative work. This module checks provenance, scope ownership,
explicit approvals and dependency hashes; it never infers character traits.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re

KINDS = {"script-context", "design-brief", "costume-bible", "stage-design"}
SCOPES = {"identity", "body", "costume"}
UNDERSTANDING_FIELDS = ("role_in_story", "core_motivation", "central_tension",
                        "world_and_life", "relationships", "arc")
OWNERS = {"identity": {"face", "hair", "skin"}, "body": {"body"},
          "costume": {"costume"}}
SCOPE_SPECIALISTS = {
    "identity": {"character-world-appearance-design", "character-feature-focus", "character-hair-design",
                 "character-face-design", "character-face-signature-design", "character-skin-design",
                 "character-face-decoration-design"},
    "body": {"character-body-design"},
    "costume": {"character-costume-style-design", "character-costume-cut-design", "character-costume-color-design",
                "character-costume-material-design", "character-costume-accessory-design"},
}
STATE_STYLING_SPECIALISTS = {
    "makeup": ("character-face-decoration-design", "costume_direction.state_makeup"),
    "hair": ("character-hair-design", "costume_direction.state_hair"),
    "head_ear_neck": ("character-face-signature-design", "costume_direction.head_ear_neck"),
    "wearable_accessories": ("character-costume-accessory-design", "costume_direction.wearable_accessories"),
}
SCENE_NEED_NAMES = (*STATE_STYLING_SPECIALISTS, "garment")
COMMON_PAYLOAD = {"facts", "inferences", "approved_choices", "recognition_axes", "world_influences", "morphology", "morphology_details"}
SCOPE_PAYLOAD = {
    "identity": {"appearance", "feature_focus", "facial_surface", "differentiation_review", "execution_layout", "identity_invariants", "prompt_detail_contract"},
    "body": {"body_form"}, "costume": {"costume", "costume_direction", "prompt_detail_contract", "execution_layout"},
}
AXIS_SCOPES = {"face_structure": "identity", "hair_structure": "identity", "silhouette": "body",
               "body_posture": "body", "costume_color": "costume"}

# Every selected, visible design cue survives the design-to-prompt handoff.
# These are information dimensions, not prescribed character features or word counts.
PROMPT_DETAIL_FIELDS = {
    "face": {"type", "forehead_cheekbone", "jaw_chin", "turning"},
    "hair": {"type_length", "hairline_part", "left_right", "back_flow", "surface_control"},
    "brow": {"shape_placement"},
    "eye": {"shape_placement", "lid_iris"},
    "ear": {"shape_visibility"},
    "nose": {"bridge_tip_wings"},
    "lip": {"width_shape_corners"},
    "skin": {"tone_distribution", "finish_artifact_control"},
    "makeup": {"base", "brow", "eye", "cheek", "lip"},
    "adornment": {"name_shape_scale", "body_side_position", "attachment_visibility", "material_state"},
    "identity": {"face_body_anchor", "reference_roles", "cross_panel"},
    "garment": {"name_silhouette", "placement_scale", "panels", "overlap_fastening",
                "material_color", "front_side_back", "mobility"},
    "focus_component": {"outline_scale", "pieces", "anchor_overlap_fastening",
                        "surface", "front_side_back", "motion"},
    "surface_pattern": {"carrier", "motif_scale", "placement_density", "technique_visibility"},
    "footwear": {"toe_opening", "upper_fastening", "heel_sole", "material_color", "front_back"},
    "framing": {"canvas_crop", "attire_or_panels", "background_light"},
}
PROMPT_DETAIL_REQUIRED = {
    "avatar": {"face", "hair", "brow", "eye", "ear", "nose", "lip", "skin", "framing"},
    "execution": {"identity", "hair", "skin", "garment", "footwear", "framing"},
}
PROMPT_DETAIL_ALLOWED = {
    "avatar": PROMPT_DETAIL_REQUIRED["avatar"] | {"makeup", "adornment"},
    "execution": PROMPT_DETAIL_REQUIRED["execution"] |
                 {"makeup", "adornment", "focus_component", "surface_pattern"},
}


DETAIL_SPECIALISTS = {
    **{kind: {"character-face-design"} for kind in ("face", "brow", "eye", "ear", "nose", "lip")},
    "hair": {"character-hair-design"}, "skin": {"character-skin-design"},
    "makeup": {"character-face-decoration-design"},
    "adornment": {"character-face-signature-design", "character-costume-accessory-design"},
    **{kind: SCOPE_SPECIALISTS["costume"] for kind in
       ("garment", "footwear", "focus_component", "surface_pattern")},
}


def _as_text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _detail_source(cp, root, state, data, kind, ref):
    """Resolve adopted work, never a self-declared source label, into cue material."""
    match = re.fullmatch(r"specialist_execution\.([a-z0-9-]+)\.(results|applied_elements)\.(0|[1-9][0-9]*)", ref)
    if match:
        specialist, collection, index = match.group(1), match.group(2), int(match.group(3))
        cp.ensure(specialist in DETAIL_SPECIALISTS.get(kind, set()),
                  f"Detail {kind} source belongs to another specialist")
        work = data.get("specialist_execution", {}).get(specialist, {})
        expected_mode = "inline" if collection == "results" else "independent"
        cp.ensure(work.get("mode") == expected_mode, "Detail source execution mode mismatch")
        rows = work.get(collection, [])
        cp.ensure(isinstance(rows, list) and index < len(rows), "Detail source result index is invalid")
        row = rows[index]
        if collection == "results":
            cp.require_text(row, "visible_result")
            value = _get(data["payload"], row["field"])
            cp.ensure(row["visible_result"] in _as_text(value), "Detail source result is not adopted")
            return row["visible_result"]
        cp.ensure(root is not None, "Independent detail source needs its real artifact root")
        proposal = cp.checked_handoff_file(root, work.get("proposal_ref"), work.get("proposal_sha256"), specialist)
        option = next((x for x in proposal["options"] if x["id"] == work.get("selected_option_id")), None)
        cp.ensure(option is not None, "Detail source has no selected proposal option")
        elements = option["design_elements"]
        element_index = row.get("element_index")
        cp.ensure(isinstance(element_index, int) and not isinstance(element_index, bool) and
                  0 <= element_index < len(elements), "Detail source proposal element is invalid")
        adopted = _as_text(_get(data["payload"], row["field"]))
        cp.ensure(all(elements[element_index][field] in adopted for field in
                      ("visible_feature", "placement_or_structure")),
                  "Independent detail source is not visibly adopted")
        return adopted
    if ref == "payload.execution_layout" or ref.startswith("payload.execution_layout."):
        identity_layout = (kind == "identity" and data["scope"] == "costume" and
                           (ref == "payload.execution_layout.identity" or
                            ref.startswith("payload.execution_layout.identity.")))
        cp.ensure(kind == "framing" or identity_layout, "Layout may only source framing or identity placement cues")
        return _as_text(_get(data, ref))
    if ref.startswith("approved_parent:"):
        cp.ensure(data["scope"] == "costume" and kind in {"identity", "hair", "skin"},
                  "Approved parent sources only preserve execution identity, hair or skin")
        cp.ensure(root is not None and state is not None, "Approved parent source needs the real project")
        record_key, separator, path = ref[len("approved_parent:"):].partition("#")
        cp.ensure(separator and path.startswith("payload."), "Approved parent source needs a payload field")
        expected_scope = "body" if kind == "identity" and path.startswith("payload.body_form") else "identity"
        cp.ensure(record_key == key("stage-design", data["character_id"], scope=expected_scope),
                  "Approved parent source must be the same character's identity/body stage")
        allowed = {"identity": ("payload.appearance", "payload.identity_invariants", "payload.body_form"),
                   "hair": ("payload.visual_details.hair",), "skin": ("payload.visual_details.skin",)}[kind]
        cp.ensure(any(path == prefix or path.startswith(prefix + ".") for prefix in allowed),
                  "Approved parent source does not belong to its detail kind")
        record = cp._checked_record(root, state, record_key)
        cp.ensure(data.get("parent_refs", {}).get(record_key) == record["sha256"],
                  "Approved detail parent must match the current stage parent SHA")
        return _as_text(_get(cp.read_json(root / record["path"]), path))
    raise ValueError(f"Unresolved detail source: {ref}")


def validate_prompt_detail_contract(cp, data, root=None, state=None, strict=True):
    """Validate the approved visual inventory before any new avatar/execution prompt."""
    scope = data["scope"]
    expected_stage = "avatar" if scope == "identity" else "execution"
    contract = data["payload"].get("prompt_detail_contract")
    cp.ensure(isinstance(contract, dict) and contract.get("schema_version") == "PromptDetailContractV1",
              "V1.2 identity/costume needs PromptDetailContractV1")
    cp.ensure(contract.get("stage") == expected_stage, "Prompt detail stage mismatch")
    cp.ensure(contract.get("complexity") in {"ordinary", "featured"},
              "Prompt detail complexity must be ordinary or featured")
    items = contract.get("items")
    cp.ensure(isinstance(items, list) and items, "Prompt detail contract needs visible items")
    ids, kinds = set(), set()
    for item in items:
        cp.ensure(isinstance(item, dict), "Prompt detail item must be an object")
        cp.require_text(item, "id")
        cp.ensure(item["id"] not in ids, "Prompt detail item IDs must be unique")
        ids.add(item["id"])
        kind = item.get("kind")
        cp.ensure(kind in PROMPT_DETAIL_ALLOWED[expected_stage], f"Invalid {expected_stage} detail kind: {kind}")
        kinds.add(kind)
        refs = item.get("source_refs")
        cp.ensure(isinstance(refs, list) and refs and all(isinstance(x, str) and x.strip() for x in refs),
                  f"Prompt detail item {item['id']} needs source_refs")
        cues = item.get("cues")
        required = PROMPT_DETAIL_FIELDS[kind]
        cp.ensure(isinstance(cues, dict) and set(cues) == required,
                  f"Prompt detail item {item['id']} needs exactly {sorted(required)}")
        cp.ensure(all(isinstance(value, str) and len(value.strip()) >= 6 for value in cues.values()),
                  f"Prompt detail item {item['id']} has empty or generic cues")
        cp.ensure(len(set(cues.values())) == len(cues),
                  f"Prompt detail item {item['id']} repeats a summary across dimensions")
        if strict:
            material = [_detail_source(cp, root, state, data, kind, ref) for ref in refs]
            cp.ensure(all(any(cue in source for source in material) for cue in cues.values()),
                      f"Prompt detail item {item['id']} has cues absent from its adopted specialist results")
            if kind == "identity":
                parent_material = [source for source, ref in zip(material, refs) if ref.startswith("approved_parent:")]
                cp.ensure(any(cues["face_body_anchor"] in source for source in parent_material),
                          "Execution identity anchor must preserve an approved identity/body result")
    cp.ensure(PROMPT_DETAIL_REQUIRED[expected_stage] <= kinds,
              f"Missing required {expected_stage} detail kinds: {sorted(PROMPT_DETAIL_REQUIRED[expected_stage] - kinds)}")
    if expected_stage == "execution":
        cp.ensure(contract["complexity"] != "featured" or "focus_component" in kinds,
                  "Featured costume needs a drawable focus_component")
        requirements = data["payload"]["costume_direction"]["scene_needs"]["requirements"]
        for need, kind in (("makeup", "makeup"), ("head_ear_neck", "adornment"),
                           ("wearable_accessories", "adornment")):
            if requirements[need]["decision"] == "design":
                cp.ensure(kind in kinds, f"Designed {need} missing from prompt detail contract")


def validate_prompt_detail_coverage(cp, root, state, package, character, variant, stage):
    """Reject prompt summaries that drop any cue frozen in the approved stage."""
    scope = "identity" if stage == "avatar" else "costume"
    record_key = key("stage-design", character, variant, scope)
    record = (draft(cp, root, state, record_key) if package.get("purpose") == "preview"
              else cp._checked_record(root, state, record_key))
    design = cp.read_json(root / record["path"])
    cp.ensure(design.get("schema_version") == "CharacterStageDesignV1.2",
              f"New {stage} prompts require a V1.2 {scope} design; deepen legacy summaries first")
    if 'fidelity_review' in package:
        from prompt_fidelity import design_inventory, validate_fidelity
        validate_fidelity(package, design_inventory(design, stage), record['sha256'])
        return
    contract = design["payload"]["prompt_detail_contract"]
    checks = "\n".join(package["acceptance_checks"])
    for prompt in package["prompts"]:
        body = prompt["text"]
        cp.ensure(not re.search(r"(?:^|[。；\n])\s*(?:脸型|发型|皮肤|妆容|款式|剪裁|材质|饰品)\s*[:：]", body),
                  f"Prompt {prompt['id']} contains section headings")
        for item in contract["items"]:
            for field, cue in item["cues"].items():
                cp.ensure(cue in body,
                          f"Prompt {prompt['id']} dropped {item['id']}.{field}: {cue}")
    for item in contract["items"]:
        cp.ensure(any(cue in checks for cue in item["cues"].values()),
                  f"Acceptance checks do not inspect detail item {item['id']}")


def enabled(state):
    return state.get("design_progression", "complete") == "phased"


def key(kind, character=None, variant="base", scope=None):
    if kind == "script-context":
        return kind
    if kind == "design-brief":
        return f"design-brief:{character}:base"
    if kind == "costume-bible":
        return f"costume-bible:{character}:base"
    return f"stage-design:{scope}:{character}:{variant if scope == 'costume' else 'base'}"


def units(cp, path):
    """Enumerate the whole source in bounded contiguous blocks, not search hits."""
    source = Path(path).expanduser().resolve()
    loaded = cp.load_source(source)  # Validate supported input before reading.
    text = (json.dumps(loaded, ensure_ascii=False, indent=2) if source.suffix.lower() == ".xlsx"
            else source.read_text(encoding="utf-8-sig"))
    leaves = []
    offset = 0
    while offset < len(text):
        end = min(offset + 2400, len(text))
        if end < len(text):
            boundary = text.rfind("\n", offset + 1200, end)
            if boundary != -1:
                end = boundary + 1
        leaves.append((f"chars:{offset}-{end}", offset, text[offset:end]))
        offset = end
    return {"source_sha256": cp.digest(source), "source_name": source.name,
            "units": [{"unit_id": f"u{index:06d}", "source_ref": pointer,
                       "offset": offset, "text": text, "sha256": cp.digest(text)}
                      for index, (pointer, offset, text) in enumerate(leaves, 1)]}


def context_units(cp, args):
    if getattr(args, "source", None):
        result = units(cp, args.source)
    else:
        cp.ensure(args.project_root, "context-units needs --source or --project-root")
        root = Path(args.project_root).expanduser().resolve()
        state = cp.read_json(root / "project.json")
        result = units(cp, root / state["inputs"]["screenplay"]["path"])
    if getattr(args, "output", None):
        cp.write_json(Path(args.output).expanduser().resolve(), result)
        return {"output": str(Path(args.output).expanduser().resolve()),
                "source_sha256": result["source_sha256"], "units": len(result["units"])}
    return result


def draft(cp, root, state, record_key):
    record = state["records"].get(record_key)
    cp.ensure(record and not record.get("stale"), f"Record missing or stale: {record_key}")
    cp.ensure(cp.digest(cp.read_json(root / record["path"])) == record["sha256"],
              f"Record contents changed: {record_key}")
    return record


def parents(cp, root, state, data, approved=True):
    refs = data.get("parent_refs", {})
    if data.get("schema_version") == "DesignDirectionBriefV1":
        refs = {"script-context": data["context_sha256"], **refs}
    for record_key, sha in refs.items():
        record = (cp._checked_record(root, state, record_key) if approved
                  else draft(cp, root, state, record_key))
        cp.ensure(record["sha256"] == sha, f"Parent version changed: {record_key}")


def checked_dependencies(cp, root, state, record_key, data):
    if record_key == "script-context":
        source = state["inputs"]["screenplay"]
        cp.ensure(data["source_sha256"] == source["sha256"] == cp.digest(root / source["path"]),
                  "Script context is for another source version")
    elif record_key.startswith(("design-brief:", "stage-design:", "costume-bible:")):
        parents(cp, root, state, data, approved=True)
        if record_key.startswith("stage-design:"):
            # Existing approved contracts remain readable. New submissions carry
            # the marker and keep their stronger provenance checks on every read.
            validate_execution(cp, root, data, state,
                               strict=data.get("execution_contract_version") == 2)
        if record_key.startswith("costume-bible:"):
            validate_bible(cp, root, state, data, data["character_id"])
    elif data.get("schema_version") == "CharacterDesignCardV2.5":
        for parent_key, sha in data["stage_receipts"].items():
            cp.ensure(cp._checked_record(root, state, parent_key)["sha256"] == sha,
                      f"Compiled card basis changed: {parent_key}")


def _text_fields(cp, data, names):
    for name in names:
        cp.require_text(data, name)


def _task(cp, data):
    cp.ensure(isinstance(data, dict), "Active specialist needs an actionable task")
    _text_fields(cp, data, ("objective", "character_context", "expected_result"))
    cp.require_list(data, "constraints")
    cp.ensure(all(isinstance(x, str) and x.strip() for x in data["constraints"]), "Task constraints must be concrete text")


def _evidence_units(cp, refs, known):
    cp.ensure(isinstance(refs, list) and refs and set(refs) <= known,
              "Narrative interpretation needs existing context evidence_unit_ids")


def validate_context(cp, root, state, data):
    cp.ensure(data.get("schema_version") == "ScriptContextV1", "Expected ScriptContextV1")
    source = root / state["inputs"]["screenplay"]["path"]
    listing = units(cp, source)
    cp.ensure(data.get("source_sha256") == listing["source_sha256"], "Context source SHA mismatch")
    cp.ensure(data.get("source_kind") in {"screenplay", "biography"}, "Unknown context source_kind")
    supplied = data.get("read_units")
    cp.ensure(isinstance(supplied, list), "read_units must enumerate the full source")
    expected = {item["unit_id"]: item["sha256"] for item in listing["units"]}
    actual = {item.get("unit_id"): item.get("sha256") for item in supplied if isinstance(item, dict)}
    cp.ensure(len(supplied) == len(expected) and actual == expected,
              "Context reading coverage must include every source unit with its exact SHA")
    _text_fields(cp, data, ("synopsis", "world_summary", "narrative_structure"))
    cp.ensure(isinstance(data.get("character_index"), list) and data["character_index"],
              "Context needs narrative character_index")
    known = set(expected)
    seen = set()
    for character in data["character_index"]:
        _text_fields(cp, character, ("character_id", "name", "role_in_story", "arc_summary", "relationships"))
        _evidence_units(cp, character.get("evidence_unit_ids"), known)
        cp.ensure(character["character_id"] not in seen, "Context character_index contains duplicate IDs")
        seen.add(character["character_id"])
    roster_ids = {x["id"] for x in state.get("roster", [])}
    if roster_ids:
        cp.ensure(seen == roster_ids, "Project context character_index must cover the complete asset roster exactly")


def validate_brief(cp, root, state, data, character):
    cp.ensure(data.get("schema_version") == "DesignDirectionBriefV1", "Expected DesignDirectionBriefV1")
    cp.ensure(data.get("asset_domain") == "character", "This version only supports asset_domain character")
    cp.ensure(data.get("character_id") == character and data.get("variant_id", "base") == "base",
              "Direction brief target mismatch")
    context = cp._checked_record(root, state, "script-context")
    cp.ensure(data.get("context_sha256") == context["sha256"], "Brief context SHA mismatch")
    source_context = cp.read_json(root / context["path"])
    indexed = next((x for x in source_context["character_index"] if x["character_id"] == character), None)
    cp.ensure(indexed is not None, "Target character must be interpreted in the full context index")
    understanding = data.get("understanding")
    cp.ensure(isinstance(understanding, dict) and understanding.get("schema_version") == "CharacterUnderstandingV1",
              "Brief needs CharacterUnderstandingV1")
    _text_fields(cp, understanding, UNDERSTANDING_FIELDS)
    _evidence_units(cp, understanding.get("evidence_unit_ids"),
                    {x["unit_id"] for x in source_context["read_units"]})
    _text_fields(cp, data, ("design_thesis", "recommended_direction"))
    cp.ensure(data.get("visual_strategy") in {"direct", "contrast", "concealed", "mixed"},
              "visual_strategy must be direct, contrast, concealed or mixed")
    for name in ("alternatives", "delegated_dimensions"):
        cp.require_list(data, name)
    plan = data.get("specialist_plan")
    cp.ensure(isinstance(plan, dict) and set(plan) == set(cp.SPECIALIST_DOMAINS_V24),
              "Direction brief must plan all 13 specialists")
    for item in plan.values():
        cp.ensure(isinstance(item, dict) and item.get("status") in {"inline", "independent", "defer", "not_needed"},
                  "Specialist plan status must be inline, independent, defer or not_needed")
        cp.require_text(item, "reason")
        if item["status"] in {"inline", "independent"}:
            _task(cp, item.get("task"))
    parents(cp, root, state, data)


def _get(data, path):
    value = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"Applied design field missing: {path}")
        value = value[part]
    return value


def _field_scope(path):
    """Use the same ownership for actual values and metadata that selects them."""
    parts = path.split(".")
    if parts[0] == "visual_details" and len(parts) >= 3:
        if parts[1] in {"face", "hair", "skin"}:
            return "identity"
        if parts[1] in {"body", "costume"}:
            return parts[1]
        if parts[1] == "adornments":
            return {"head_neck": "identity", "body_hands": "costume"}.get(parts[2])
    if parts[0] == "recognition_axes" and len(parts) == 2:
        return AXIS_SCOPES.get(parts[1])
    if parts[0] == "morphology_details" and len(parts) >= 2:
        return parts[1] if parts[1] in SCOPES else None
    for scope, names in SCOPE_PAYLOAD.items():
        if parts[0] in names:
            return scope
    if parts[0] in {"morphology", "world_influences"}:
        return "identity"
    return None


def _knowledge(cp, root, refs, specialist=None, strict=True, archive=False):
    cp.ensure(isinstance(refs, list) and refs, "Inline execution needs real knowledge_refs")
    plugin = Path(cp.__file__).resolve().parents[1]
    locked = cp.read_json(plugin / "knowledge-lock.json")["snapshots"] if strict else []
    for item in refs:
        cp.ensure(isinstance(item, dict), "Knowledge reference must be an object")
        sha = item.get("sha256", "")
        cp.ensure(isinstance(sha, str) and len(sha) == 64 and all(x in "0123456789abcdef" for x in sha),
                  "Knowledge reference SHA must be hexadecimal SHA-256")
        if strict:
            cp.ensure(any(row.get("path") == item.get("path") and row.get("rules_sha256") == sha and
                          specialist in row.get("capability_ids", []) for row in locked),
                      f"Knowledge reference is not locked for specialist {specialist}")
        snapshot = root / "knowledge-snapshots" / sha
        if snapshot.is_file():
            cp.ensure(cp.digest(snapshot) == sha, "Project knowledge snapshot changed")
            continue
        path = (plugin / item.get("path", "")).resolve()
        cp.ensure(path.is_relative_to(plugin) and path.is_file(), "Knowledge file must be inside this plugin")
        cp.ensure(cp.digest(path) == item.get("sha256"), "Knowledge reference SHA mismatch")
        if archive:
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            cp.shutil.copy2(path, snapshot)


def _archive_execution_knowledge(cp, root, data):
    """Archive once on successful new-stage submission, never during reads."""
    for specialist, work in data["specialist_execution"].items():
        if work["mode"] == "inline":
            refs = work["knowledge_refs"]
        elif work["mode"] == "independent":
            proposal = cp.checked_handoff_file(root, work["proposal_ref"], work["proposal_sha256"], specialist)
            refs = proposal.get("knowledge_refs", [])
        else:
            continue
        _knowledge(cp, root, refs, specialist, strict=True, archive=True)


def _stage_morphology(cp, root, data, state):
    morphology = data.get("payload", {}).get("morphology")
    if morphology is None and data["scope"] != "identity" and state is not None:
        identity_key = key("stage-design", data["character_id"], scope="identity")
        identity_record = cp._checked_record(root, state, identity_key)
        morphology = cp.read_json(root / identity_record["path"])["payload"]["morphology"]
    return morphology


def _specialist_field(cp, data, specialist, path):
    """Evidence/labels cannot stand in for a specialist's adopted design field."""
    cp.ensure(isinstance(path, str) and path.strip(), "Specialist result needs a payload field")
    parts = path.split(".")
    if parts[0] == "visual_details":
        cp.ensure(len(parts) > 2 and parts[1] in cp.SPECIALIST_FIELD_DOMAINS[specialist],
                  "Specialist result is outside its design domain")
        return
    prefixes = {
        "character-world-appearance-design": ("world_influences",),
        "character-feature-focus": ("feature_focus", "recognition_axes", "identity_invariants"),
        "character-face-design": ("appearance",),
        "character-hair-design": ("costume_direction.state_hair",),
        "character-body-design": ("body_form",),
        "character-skin-design": (),
        "character-face-signature-design": ("facial_surface", "costume_direction.head_ear_neck"),
        "character-face-decoration-design": ("facial_surface", "costume_direction.state_makeup"),
        "character-costume-style-design": ("costume", "costume_direction.front_structure", "costume_direction.back_structure",
                                            "costume_direction.recognition_focus"),
        "character-costume-cut-design": ("costume_direction.cut_and_fastening", "costume_direction.layering",
                                          "costume_direction.mobility_and_camera"),
        "character-costume-color-design": ("costume_direction.color_placement", "recognition_axes.costume_color"),
        "character-costume-material-design": ("costume_direction.material_behavior",),
        "character-costume-accessory-design": ("costume_direction.wearable_accessories", "costume_direction.head_ear_neck"),
    }.get(specialist, ())
    shape_prefix = f"morphology_details.{data['scope']}"
    nonhuman = (path == shape_prefix or path.startswith(shape_prefix + ".")) and specialist in SCOPE_SPECIALISTS[data['scope']]
    cp.ensure(nonhuman or any(path == prefix or path.startswith(prefix + ".") for prefix in prefixes),
              "Specialist result must map an owned design field, not evidence or prompt metadata")


def validate_execution(cp, root, data, state=None, strict=True):
    execution = data.get("specialist_execution")
    cp.ensure(isinstance(execution, dict) and execution, "Stage design needs actual specialist_execution")
    cp.ensure(SCOPE_SPECIALISTS[data["scope"]] <= set(execution),
              "Stage design must cover its responsible specialists, including reasoned not_needed decisions")
    brief = None
    if state is not None:
        brief_record = draft(cp, root, state, key("design-brief", data["character_id"]))
        brief = cp.read_json(root / brief_record["path"])
    # Historical reads used no new morphology-parent lookups. Only fresh work
    # needs the human/core applicability gate introduced with this contract.
    morphology = _stage_morphology(cp, root, data, state) if strict else None
    core = ({"character-face-design", "character-hair-design", "character-skin-design"}
            if data["scope"] == "identity" else {"character-body-design"} if data["scope"] == "body" else set())
    for specialist, work in execution.items():
        cp.ensure(specialist in cp.SPECIALIST_DOMAINS_V24, f"Unknown specialist: {specialist}")
        cp.require_text(work, "decision")
        mode = work.get("mode")
        cp.ensure(mode in {"inline", "independent", "not_needed"}, "Unknown specialist execution mode")
        if strict and mode == "not_needed":
            cp.ensure(morphology == "nonhuman" or specialist not in core,
                      f"Current human design needs actual {specialist} work; baldness is a hair design result")
            if brief is not None and brief["specialist_plan"][specialist]["status"] in {"inline", "independent"}:
                cp.require_text(work, "execution_change_reason")
                cp.require_text(work, "not_applicable_reason")
        if brief is not None and mode != "not_needed":
            planned = brief["specialist_plan"][specialist]
            state_activation = (data["scope"] == "costume" and
                                specialist in {pair[0] for pair in STATE_STYLING_SPECIALISTS.values()} and
                                data.get("schema_version") in {"CharacterStageDesignV1.1", "CharacterStageDesignV1.2"})
            if planned["status"] == "not_needed" and state_activation:
                _task(cp, work.get("task"))
                cp.require_text(work, "state_activation_reason")
            else:
                cp.ensure(planned["status"] != "not_needed", "An excluded specialist needs an updated direction brief before activation")
            if planned["status"] == "defer":
                _task(cp, work.get("task"))
                cp.require_text(work, "activation_reason")
            elif planned["status"] != mode and planned["status"] != "not_needed":
                cp.require_text(work, "execution_change_reason")
        if mode == "not_needed":
            continue
        if mode == "inline":
            cp.ensure(isinstance(work.get("rules_applied"), list) and work["rules_applied"] and
                      all(isinstance(x, str) and x.strip() for x in work["rules_applied"]),
                      "Inline work must name the specialist rules actually applied")
            _knowledge(cp, root, work.get("knowledge_refs"), specialist, strict)
            cp.ensure(isinstance(work.get("results"), list) and work["results"], "Inline work needs visible results")
            for result in work["results"]:
                _text_fields(cp, result, ("field", "visible_result", "basis"))
                cp.ensure(result.get("evidence_status") in {"script_fact", "inference", "creative_choice"},
                          "Inline result needs evidence_status")
                value = _get(data["payload"], result["field"])
                if strict:
                    _specialist_field(cp, data, specialist, result["field"])
                cp.ensure(result["visible_result"] in (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)),
                          "Inline result must actually occur in its mapped payload field")
                domain = result["field"].split(".")
                if domain[0] == "visual_details":
                    cp.ensure(len(domain) > 2 and domain[1] in cp.SPECIALIST_FIELD_DOMAINS[specialist],
                              "Inline result is outside the specialist's domain")
        else:
            proposal = cp.checked_handoff_file(root, work.get("proposal_ref"), work.get("proposal_sha256"), specialist)
            from validate_specialist_proposal import validate
            validate(proposal)
            cp.ensure(proposal.get("schema_version") in {"CharacterSpecialistProposalV1.1", "CharacterSpecialistProposalV1.2"},
                      "Independent handoff needs V1.1 or V1.2")
            if proposal["schema_version"] == "CharacterSpecialistProposalV1.2":
                _knowledge(cp, root, proposal["knowledge_refs"], specialist, strict)
            elif strict:
                cp.ensure(False, "New independent work needs V1.2 with specialist-applicable knowledge")
            cp.ensure(proposal.get("specialist") == specialist and proposal.get("character_id") == data["character_id"] and
                      proposal.get("variant_id") == data["variant_id"], "Independent proposal target mismatch")
            if strict:
                cp.ensure(proposal.get("scope") == data["scope"] and proposal.get("execution_mode") == "independent",
                          "Independent proposal must match the current stage scope and actual execution mode")
            option = next((x for x in proposal["options"] if x["id"] == work.get("selected_option_id")), None)
            cp.ensure(option, "Independent work must select a real proposal option")
            mappings = work.get("applied_elements")
            cp.ensure(isinstance(mappings, list) and mappings, "Independent work needs applied_elements")
            for mapping in mappings:
                index = mapping.get("element_index")
                cp.ensure(isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(option["design_elements"]),
                          "Independent element index is invalid")
                adopted = _get(data["payload"], mapping["field"])
                if strict:
                    _specialist_field(cp, data, specialist, mapping["field"])
                    element = option["design_elements"][index]
                    cp.ensure(all(element[field] in _as_text(adopted) for field in
                                  ("visible_feature", "placement_or_structure")),
                              "Independent selected feature and structure must actually occur in its mapped payload")
                domain = mapping["field"].split(".")
                if domain[0] == "visual_details":
                    cp.ensure(len(domain) > 2 and domain[1] in cp.SPECIALIST_FIELD_DOMAINS[specialist],
                              "Independent result is outside the specialist's domain")


def validate_bible(cp, root, state, data, character):
    cp.ensure(state.get("pipeline_version", 1) >= 3, "CostumeStyleBibleV1 belongs to pipeline 3")
    cp.ensure(data.get("schema_version") == "CostumeStyleBibleV1" and
              data.get("character_id") == character and data.get("variant_id", "base") == "base",
              "Costume bible target or schema mismatch")
    refs = data.get("parent_refs")
    expected = {key("design-brief", character), key("stage-design", character, scope="identity"),
                key("stage-design", character, scope="body")}
    cp.ensure(isinstance(refs, dict) and set(refs) == expected,
              "Costume bible must bind the approved direction and identity")
    parents(cp, root, state, data)
    cp.ensure(data.get("tier") in {"full", "compact", "group"}, "Unknown wardrobe bible tier")
    roster_item = next(x for x in state["roster"] if x["id"] == character)
    if roster_item.get("priority") == "deep":
        cp.ensure(data["tier"] == "full", "Lead and important characters need a full wardrobe bible")
    else:
        cp.ensure(data["tier"] in {"compact", "group"}, "Ordinary characters use compact or group wardrobe rules")
    for field in ("wearing_thesis", "world_translation", "signature_silhouette",
                  "cut_grammar", "palette_grammar", "material_grammar", "recognition_anchor",
                  "wearing_habits", "state_logic", "physical_and_camera_rules"):
        cp.require_text(data, field)
        cp.ensure(len(data[field].strip()) >= 16, f"Wardrobe rule too vague: {field}")
    if data["tier"] == "full":
        matrix = data.get("state_matrix")
        cp.ensure(isinstance(matrix, list) and matrix, "Lead wardrobe bible needs a state_matrix")
        expected_states = {x.get("id") for x in roster_item.get("states", [])} or {"base"}
        cp.ensure({x.get("variant_id") for x in matrix} == expected_states,
                  "Wardrobe state_matrix must cover every registered state")
        for item in matrix:
            for field in ("variant_id", "narrative_function", "silhouette_shift", "anchor_continuity"):
                cp.require_text(item, field)
    cp.ensure(data.get("new_lore_policy") in {"none", "pending_approval"},
              "New family, religion or faction lore must be separately reviewed")
    cp.require_list(data, "unresolved")
    if data["new_lore_policy"] == "pending_approval":
        cp.ensure(data["unresolved"], "Pending new lore must remain unresolved until separately approved")


def validate_costume_direction(cp, root, state, data):
    character, variant = data["character_id"], data["variant_id"]
    bible_key = key("costume-bible", character)
    cp.ensure(data["parent_refs"].get(bible_key) == cp._checked_record(root, state, bible_key)["sha256"],
              "State costume must bind the current approved wardrobe bible")
    direction = data["payload"].get("costume_direction")
    cp.ensure(isinstance(direction, dict), "Pipeline 3 costume needs costume_direction")
    for field in ("script_requirement", "narrative_function", "front_structure", "back_structure",
                  "cut_and_fastening", "layering", "color_placement", "material_behavior",
                  "recognition_focus", "mobility_and_camera", "state_continuity", "makeup_and_hair"):
        cp.require_text(direction, field)
        cp.ensure(len(direction[field].strip()) >= 16, f"Costume design too vague: {field}")
    cp.ensure(direction.get("evidence_status") in {"script_fact", "inference", "creative_choice", "mixed"},
              "Costume choices need an evidence boundary")
    cp.require_list(direction, "script_refs")
    cp.ensure(direction["script_refs"], "Costume requires script or direction evidence")
    expected_fields = {
        "character-costume-style-design": ("costume_direction.front_structure", "costume_direction.back_structure"),
        "character-costume-cut-design": ("costume_direction.cut_and_fastening", "costume_direction.layering"),
        "character-costume-color-design": ("costume_direction.color_placement",),
        "character-costume-material-design": ("costume_direction.material_behavior", "visual_details.costume.material_drape_wear"),
    }
    for specialist, fields in expected_fields.items():
        work = data["specialist_execution"].get(specialist, {})
        cp.ensure(work.get("mode") in {"inline", "independent"},
                  f"Mandatory costume specialist not applied: {specialist}")
        if work["mode"] == "inline":
            cp.ensure(any(result.get("field", "") in fields
                          for result in work.get("results", [])),
                      f"Costume specialist needs a mapped garment result: {specialist}")
        else:
            cp.ensure(any(mapping.get("field") in fields for mapping in work.get("applied_elements", [])),
                      f"Independent costume proposal needs an applied garment field: {specialist}")
    if data["schema_version"] in {"CharacterStageDesignV1.1", "CharacterStageDesignV1.2"}:
        validate_scene_needs(cp, data)


def validate_scene_needs(cp, data):
    """A state-specific needs pass is mandatory for new costume submissions.

    Base identity exclusions do not decide temporary makeup, hair or jewelry.
    Historical V1 records remain readable without retroactive requirements.
    """
    direction = data["payload"]["costume_direction"]
    needs = direction.get("scene_needs")
    cp.ensure(isinstance(needs, dict), "V1.1 costume needs scene_needs")
    for name in ("occasion", "shot_and_action", "constraint_scope"):
        cp.require_text(needs, name)
    requirements = needs.get("requirements")
    cp.ensure(isinstance(requirements, dict) and set(requirements) == set(SCENE_NEED_NAMES),
              "Scene needs must decide makeup, hair, head/ear/neck, garment and wearable accessories")
    execution = data["specialist_execution"]
    for name, item in requirements.items():
        cp.ensure(isinstance(item, dict), f"Scene need {name} must be an object")
        cp.ensure(item.get("decision") in {"design", "inherit", "explicit_none"},
                  f"Scene need {name} needs design, inherit or explicit_none")
        cp.require_text(item, "reason")
        cp.ensure(len(item["reason"].strip()) >= 16, f"Scene need {name} has a vague reason")
        cp.require_list(item, "source_refs")
        cp.ensure(item["source_refs"] and all(isinstance(ref, str) and ref.strip() for ref in item["source_refs"]),
                  f"Scene need {name} needs traceable scene or approved-direction refs")
        if item["decision"] != "design":
            continue
        cues = item.get("prompt_cues")
        cp.ensure(isinstance(cues, list) and cues and all(isinstance(cue, str) and len(cue.strip()) >= 4 for cue in cues),
                  f"Designed scene need {name} needs visible prompt_cues")
        source_text = (" ".join(str(direction.get(field, "")) for field in
                        ("front_structure", "back_structure", "cut_and_fastening", "layering", "recognition_focus"))
                       if name == "garment" else str(direction.get(STATE_STYLING_SPECIALISTS[name][1].rsplit(".", 1)[-1], "")))
        cp.ensure(all(cue in source_text for cue in cues),
                  f"Scene need {name} prompt_cues must come from mapped visible design")
        if name == "garment":
            for specialist in ("character-costume-style-design", "character-costume-cut-design",
                               "character-costume-color-design", "character-costume-material-design"):
                cp.ensure(execution[specialist]["mode"] in {"inline", "independent"},
                          f"Garment scene need requires {specialist}")
            continue
        specialist, field = STATE_STYLING_SPECIALISTS[name]
        work = execution.get(specialist, {})
        cp.ensure(work.get("mode") in {"inline", "independent"},
                  f"Designed scene need {name} requires active {specialist}")
        cp.require_text(direction, field.rsplit(".", 1)[-1])
        if work["mode"] == "inline":
            cp.ensure(any(result.get("field") == field for result in work.get("results", [])),
                      f"Scene need {name} has no mapped specialist result")
        else:
            cp.ensure(any(mapping.get("field") == field for mapping in work.get("applied_elements", [])),
                      f"Scene need {name} has no mapped independent result")


def validate_scene_prompt_coverage(cp, root, state, package, character, variant):
    """Guard the design-to-prompt handoff for V1.1 state work."""
    record = cp._checked_record(root, state, key("stage-design", character, variant, "costume"))
    stage = cp.read_json(root / record["path"])
    if stage.get("schema_version") not in {"CharacterStageDesignV1.1", "CharacterStageDesignV1.2"}:
        return
    if 'fidelity_review' in package:
        # The unified inventory includes scene cues as well as adopted objects.
        from prompt_fidelity import design_inventory, validate_fidelity
        validate_fidelity(package, design_inventory(stage, 'execution'), record['sha256'])
        return
    requirements = stage["payload"]["costume_direction"]["scene_needs"]["requirements"]
    checks = "\n".join(package["acceptance_checks"])
    for name, item in requirements.items():
        if item["decision"] != "design":
            continue
        for prompt in package["prompts"]:
            for cue in item["prompt_cues"]:
                cp.ensure(cue in prompt["text"],
                          f"Execution prompt {prompt['id']} dropped {name} cue: {cue}")
        cp.ensure(any(cue in checks for cue in item["prompt_cues"]),
                  f"Execution checks do not inspect designed {name}")


def required_parents(state, character, scope, variant):
    result = [key("design-brief", character)]
    if scope in {"body", "costume"}:
        result.append(key("stage-design", character, scope="identity"))
    if scope == "costume":
        result.append(key("stage-design", character, scope="body"))
        if state.get("pipeline_version", 1) >= 3:
            result.append(key("costume-bible", character))
    return result


def validate_stage(cp, root, state, data, character, variant, scope, strict=True):
    cp.ensure(scope in SCOPES and data.get("schema_version") in {"CharacterStageDesignV1", "CharacterStageDesignV1.1", "CharacterStageDesignV1.2"},
              "Expected CharacterStageDesignV1/V1.1/V1.2 and a design scope")
    cp.ensure(data.get("character_id") == character and data.get("scope") == scope and data.get("variant_id") == variant,
              "Stage design target mismatch")
    if strict:
        cp.ensure(data.get("execution_contract_version") == 2,
                  "New or modified stage design needs execution_contract_version: 2")
    cp.ensure(variant == "base" or scope == "costume", "Identity and body scopes belong to base")
    refs = data.get("parent_refs")
    cp.ensure(isinstance(refs, dict) and set(refs) == set(required_parents(state, character, scope, variant)),
              "Stage design parent_refs must cover exactly the preceding design scopes")
    parents(cp, root, state, data, approved=scope != "identity")
    payload = data.get("payload")
    cp.ensure(isinstance(payload, dict), "Stage payload must be an object")
    cp.ensure(set(payload) <= COMMON_PAYLOAD | SCOPE_PAYLOAD[scope] | {"visual_details"},
              "Stage payload contains fields owned by another design scope")
    for name, ref_field in (("facts", "source_refs"), ("inferences", "basis_refs")):
        if name in payload:
            cp.require_list(payload, name)
            for claim in payload[name]:
                cp.require_text(claim, "text")
                refs = claim.get(ref_field)
                cp.ensure(isinstance(refs, list) and refs and all(isinstance(x, str) and x.strip() for x in refs),
                          f"Stage {name} need nonempty {ref_field}")
    if "approved_choices" in payload:
        cp.require_list(payload, "approved_choices")
        for choice in payload["approved_choices"]:
            _text_fields(cp, choice, ("field", "value", "rationale"))
            cp.ensure(_field_scope(choice["field"]) == scope,
                      "Stage approved_choices cannot select another scope's design fields")
            _get(payload, choice["field"])
    if "recognition_axes" in payload:
        axes = payload["recognition_axes"]
        cp.ensure(isinstance(axes, dict) and all(AXIS_SCOPES.get(name) == scope for name in axes),
                  "Stage recognition_axes contain another scope's axis")
        for name in axes:
            cp.require_text(axes, name)
    if "morphology_details" in payload:
        cp.ensure(isinstance(payload["morphology_details"], dict) and set(payload["morphology_details"]) == {scope},
                  "morphology_details must belong to the current design scope")
    if scope != "identity" and "world_influences" in payload:
        world = payload["world_influences"]
        cp.ensure(isinstance(world, dict) and set(world) == {"appearance_effects"},
                  "Later scopes cannot change world environment, technology or resource rules")
        cp.ensure(isinstance(world["appearance_effects"], list), "World appearance effects must be a list")
        for effect in world["appearance_effects"]:
            _text_fields(cp, effect, ("feature", "mechanism", "basis", "evidence_status", "field"))
            cp.ensure(effect["evidence_status"] in {"script_fact", "approved_choice", "inference", "creative_choice"},
                      "World effect needs a recognized evidence_status")
            cp.ensure(_field_scope(effect["field"]) == scope,
                      "Stage world effects cannot change another scope's appearance")
            _get(payload, effect["field"])
    details = payload.get("visual_details")
    cp.ensure(isinstance(details, dict), "Stage payload needs visual_details")
    morphology = payload.get("morphology")
    if scope != "identity":
        identity_key = key("stage-design", character, scope="identity")
        identity = cp.read_json(root / cp._checked_record(root, state, identity_key)["path"])["payload"]
        cp.ensure(morphology in {None, identity["morphology"]}, "A later scope cannot change identity morphology")
        morphology = identity["morphology"]
    human = morphology in {"human", "humanoid"}
    if not human:
        form = payload.get("morphology_details")
        cp.ensure(isinstance(form, dict) and set(form) == {scope} and form[scope],
                  "Nonhuman design needs morphology_details for the current scope")
    allowed = OWNERS[scope] | ({"adornments"} if scope != "body" else set())
    cp.ensure(set(details) <= allowed, "Stage payload changes another scope's visual fields")
    for domain in OWNERS[scope] if human else ():
        cp.ensure(isinstance(details.get(domain), dict), f"Stage needs visual_details.{domain}")
        for field in cp.DETAIL_FIELDS[domain]:
            cp.require_text(details[domain], field)
            cp.ensure(len(details[domain][field].strip()) >= 8, f"Concrete design missing: {domain}.{field}")
    if human and scope in {"identity", "costume"}:
        owned = "head_neck" if scope == "identity" else "body_hands"
        cp.ensure(set(details.get("adornments", {})) == {owned}, "Adornment ownership must match its design scope")
        cp.require_text(details["adornments"], owned)
    if scope == "identity":
        cp.ensure(payload.get("morphology") in {"human", "humanoid", "nonhuman"}, "Identity needs morphology")
        for field in ("appearance", "feature_focus", "world_influences", "facial_surface", "differentiation_review"):
            cp.ensure(isinstance(payload.get(field), dict), f"Identity needs {field}")
        cp.ensure(isinstance(payload.get("identity_invariants"), list) and payload["identity_invariants"],
                  "Identity needs stable identity_invariants")
        cp.validate_world_and_face(payload, allow_proposals=True)
        cp.validate_feature_focus(payload)
    if scope == "body" and human:
        cp.validate_body_form(payload)
        cp.validate_body_proportion_anchors(payload)
    if scope == "costume":
        cp.ensure(isinstance(payload.get("costume"), dict) and payload["costume"], "Costume scope needs costume summary")
    cp.require_list(data, "deferred_dimensions")
    validate_execution(cp, root, data, state, strict=strict)
    if scope == "costume" and state.get("pipeline_version", 1) >= 3:
        validate_costume_direction(cp, root, state, data)
    if human and data["schema_version"] == "CharacterStageDesignV1.2" and scope in {"identity", "costume"}:
        validate_prompt_detail_contract(cp, data, root=root, state=state, strict=strict)


def _store(cp, root, state, record_key, data, approval=None):
    sha = cp.digest(data)
    path = root / "records" / record_key.replace(":", "/") / f"{sha[:12]}.json"
    cp.write_json(path, data)
    state["records"][record_key] = {"path": str(path.relative_to(root)), "sha256": sha,
                                    "submitted_at": cp.now(), "approval": approval, "stale": False}
    return state["records"][record_key]


def invalidate(cp, state, character=None, scope="direction", variant="base"):
    """Invalidate only descendants of a design domain; keep immutable history files."""
    scopes = {"direction": SCOPES, "identity": SCOPES, "body": {"body", "costume"}, "costume": {"costume"}}[scope]
    image_start = {"direction": "avatar", "identity": "avatar", "body": "full_body",
                   "costume": "execution" if state.get("pipeline_version", 1) >= 3 else "costume_design"}[scope]
    cp._invalidate(state, character, variant if scope == "costume" else None, image_start)
    for record_key, record in state["records"].items():
        parts = record_key.split(":")
        matches_character = not character or character in parts
        if not matches_character:
            continue
        selected = ((record_key.startswith("design-brief:") and scope == "direction") or
                    (record_key.startswith("costume-bible:") and scope in {"direction", "identity", "body"}) or
                    (record_key.startswith("stage-design:") and parts[1] in scopes and
                     (scope != "costume" or parts[-1] == variant)) or
                    (record_key.startswith("design-card:") and (scope != "costume" or parts[-1] == variant)))
        if selected:
            record.update(stale=True, approval=None)


def invalidate_bible(cp, state, character):
    """A changed wardrobe constitution requires review of every costume state."""
    cp._invalidate(state, character, None, "execution")
    for record_key, record in state["records"].items():
        parts = record_key.split(":")
        if character in parts and (record_key.startswith("stage-design:costume:") or
                                   record_key.startswith("design-card:")):
            record.update(stale=True, approval=None)


def submit(cp, args, root, state):
    cp.ensure(enabled(state), "Scoped design records require a phased project")
    data = cp.read_json(args.file)
    cp.require_list(data, "unresolved")
    character, variant, scope = args.character_id, args.variant_id or "base", getattr(args, "scope", None)
    if args.kind == "script-context":
        validate_context(cp, root, state, data)
    else:
        cp.require_known_variant(state, character, variant)
        cp.ensure(cp.ensemble.mode(cp, root, state, character) == "individual",
                  "Extras use a one-sheet design, not individual multi-stage design scopes")
        cp._checked_record(root, state, "visual-bible")
        cp._checked_record(root, state, "cast-plan")
        if args.kind == "design-brief":
            cp.ensure(variant == "base", "Direction brief belongs to base")
            validate_brief(cp, root, state, data, character)
        elif args.kind == "costume-bible":
            cp.ensure(variant == "base", "Costume bible belongs to base")
            validate_bible(cp, root, state, data, character)
        else:
            # A byte-identical, already approved historical stage is a read,
            # not newly authored work. Never make an old approval stale merely
            # because the installed validator gained a stronger contract.
            previous_key = key("stage-design", character, variant, scope)
            previous_stage = state["records"].get(previous_key)
            if (previous_stage and previous_stage.get("approval") and not previous_stage.get("stale") and
                    previous_stage["sha256"] == cp.digest(data)):
                cp._checked_record(root, state, previous_key)
                return {"key": previous_key, "status": "unchanged", "sha256": previous_stage["sha256"]}
            if scope in {"identity", "costume"} and state.get("pipeline_version", 1) >= 3:
                if scope == "identity":
                    human = data.get("payload", {}).get("morphology") in {"human", "humanoid"}
                else:
                    identity_key = key("stage-design", character, scope="identity")
                    identity = cp.read_json(root / cp._checked_record(root, state, identity_key)["path"])
                    human = identity.get("payload", {}).get("morphology") in {"human", "humanoid"}
                if human:
                    cp.ensure(data.get("schema_version") == "CharacterStageDesignV1.2",
                              "New human identity/costume submissions require CharacterStageDesignV1.2 prompt details")
            validate_stage(cp, root, state, data, character, variant, scope)
    record_key = key(args.kind, character, variant, scope)
    incoming = cp.digest(data)
    previous = state["records"].get(record_key)
    if previous and previous["sha256"] == incoming and not previous.get("stale"):
        return {"key": record_key, "status": "unchanged", "sha256": incoming}
    if args.kind == "stage-design":
        _archive_execution_knowledge(cp, root, data)
    if previous:
        if args.kind == "costume-bible":
            invalidate_bible(cp, state, character)
        else:
            invalidate(cp, state, character, scope if args.kind == "stage-design" else "direction", variant)
    value = _store(cp, root, state, record_key, data)
    if args.kind == "script-context" and not data["unresolved"]:
        value["approval"] = {"operator": "system:context-contract-check", "at": cp.now(),
                             "sha256": value["sha256"], "scope": "source-coverage-and-structure"}
        state["decisions"].append({"kind": "context-contract-check", "key": record_key, **value["approval"]})
        return {"key": record_key, "status": "ready", "sha256": value["sha256"],
                "checked": "source-coverage-and-structure", "interpretation_confirmed": False}
    return {"key": record_key, "status": "awaiting-approval", "sha256": value["sha256"]}


def approve(cp, args, root, state):
    record_key = key(args.kind, args.character_id, args.variant_id or "base", getattr(args, "scope", None))
    value = draft(cp, root, state, record_key)
    data = cp.read_json(root / value["path"])
    cp.ensure(not data["unresolved"], "Resolve current scope decisions before approval")
    if args.kind == "script-context":
        validate_context(cp, root, state, data)
    elif args.kind == "design-brief":
        validate_brief(cp, root, state, data, args.character_id)
    elif args.kind == "costume-bible":
        validate_bible(cp, root, state, data, args.character_id)
    else:
        validate_stage(cp, root, state, data, args.character_id, args.variant_id or "base", args.scope,
                       strict=data.get("execution_contract_version") == 2 or not value.get("approval"))
        parents(cp, root, state, data, approved=True)
    cp.require_text({"operator": args.operator}, "operator")
    value["approval"] = {"operator": args.operator, "at": cp.now(), "sha256": value["sha256"]}
    state["decisions"].append({"kind": "approve-record", "key": record_key, **value["approval"]})
    return {"key": record_key, "approved": True, "sha256": value["sha256"]}


def basis_keys(character, variant, stage, state=None):
    result = [key("design-brief", character), key("stage-design", character, scope="identity")]
    if stage in {"full_body", "costume_design", "execution"}:
        result.append(key("stage-design", character, scope="body"))
    if stage in {"costume_design", "execution"}:
        if state and state.get("pipeline_version", 1) >= 3:
            result.append(key("costume-bible", character))
        result.append(key("stage-design", character, variant, "costume"))
    if stage == "execution":
        result.append(f"design-card:{character}:{variant}")
    return result


def resolve_basis(cp, root, state, package, character, variant, stage, force_approved=False):
    preview = package.get("purpose", "production") == "preview" and not force_approved
    cp.ensure(package.get("purpose", "production") in {"preview", "production"}, "Unknown prompt purpose")
    cp.ensure(not preview or stage == "avatar", "Only an avatar can be a fast preview")
    mode = package.get("preview_mode", "direction_first")
    cp.ensure(mode in {"direction_first", "image_first"}, "Unknown preview_mode")
    expected_keys = basis_keys(character, variant, stage, state)
    supplied = package.get("design_basis", {}).get("records")
    cp.ensure(isinstance(supplied, dict) and set(supplied) == set(expected_keys), "Prompt design_basis records do not match the stage")
    cp._checked_record(root, state, "script-context")
    cp._checked_record(root, state, "visual-bible")
    cp._checked_record(root, state, "cast-plan")
    payloads = []
    for record_key in expected_keys:
        may_be_draft = preview and (record_key.startswith("stage-design:identity:") or
                                  mode == "image_first" and record_key.startswith("design-brief:"))
        record = draft(cp, root, state, record_key) if may_be_draft else cp._checked_record(root, state, record_key)
        cp.ensure(record["sha256"] == supplied[record_key], f"Prompt design basis version changed: {record_key}")
        data = cp.read_json(root / record["path"])
        if record_key.startswith("stage-design:"):
            parents(cp, root, state, data, approved=not preview)
            strict = data.get("execution_contract_version") == 2 or not record.get("approval")
            validate_execution(cp, root, data, state, strict=strict)
            if (strict and data["scope"] in {"identity", "costume"} and
                    data.get("schema_version") == "CharacterStageDesignV1.2" and
                    _stage_morphology(cp, root, data, state) in {"human", "humanoid"}):
                validate_prompt_detail_contract(cp, data, root=root, state=state, strict=True)
            payloads.append(data["payload"])
    merged = merge_payloads(cp, payloads)
    return merged


def merge_payloads(cp, payloads):
    result = {}
    def merge(target, source, prefix=""):
        for name, value in source.items():
            path = f"{prefix}.{name}" if prefix else name
            if name not in target:
                target[name] = copy.deepcopy(value)
            elif isinstance(value, dict) and isinstance(target[name], dict):
                merge(target[name], value, path)
            elif isinstance(value, list) and isinstance(target[name], list):
                for item in value:
                    if item not in target[name]:
                        target[name].append(copy.deepcopy(item))
            else:
                cp.ensure(target[name] == value, f"Conflicting design scopes at {path}")
    for payload in payloads:
        source = copy.deepcopy(payload)
        contract = source.pop("prompt_detail_contract", None)
        if contract is not None:
            stage = contract["stage"]
            contracts = result.setdefault("prompt_detail_contracts", {})
            cp.ensure(stage not in contracts or contracts[stage] == contract,
                      f"Conflicting prompt detail contracts for {stage}")
            contracts[stage] = contract
        if "execution_layout" in source:
            layout = source.pop("execution_layout")
            scope = ("costume" if source.get("costume_direction") is not None or source.get("costume") is not None or
                     contract is not None and contract["stage"] == "execution" else "identity")
            layouts = result.setdefault("stage_execution_layouts", {})
            cp.ensure(scope not in layouts or layouts[scope] == layout, f"Conflicting {scope} execution layouts")
            layouts[scope] = layout
            # Existing nonhuman readers use execution_layout. Preserve that
            # interface, choosing the current state layout over identity framing.
            result["execution_layout"] = copy.deepcopy(layouts.get("costume", layouts.get("identity")))
        merge(result, source)
    return result


def compile_card(cp, args):
    with cp.locked_project(args.project_root) as (root, state):
        cp.ensure(enabled(state) and not state["pending_impact"], "Compile requires an unblocked phased project")
        character, variant = args.character_id, args.variant_id or "base"
        cp.require_known_variant(state, character, variant)
        scopes = [key("design-brief", character), key("stage-design", character, scope="identity"),
                  key("stage-design", character, scope="body")]
        if state.get("pipeline_version", 1) >= 3:
            scopes.append(key("costume-bible", character))
        scopes.append(key("stage-design", character, variant, "costume"))
        values = {record_key: cp._checked_record(root, state, record_key) for record_key in scopes}
        stages = [cp.read_json(root / values[x]["path"]) for x in scopes[1:] if x.startswith("stage-design:")]
        card = merge_payloads(cp, [x["payload"] for x in stages])
        card.update(schema_version="CharacterDesignCardV2.5", character_id=character, variant_id=variant,
                    unresolved=[], stage_receipts={x: values[x]["sha256"] for x in scopes})
        for name in ("facts", "inferences", "approved_choices", "identity_invariants"):
            card.setdefault(name, [])
        executions = {}
        for stage in stages:
            for specialist, work in stage["specialist_execution"].items():
                executions.setdefault(specialist, []).append({"scope": stage["scope"], "variant_id": stage["variant_id"], **work})
        brief = cp.read_json(root / values[scopes[0]]["path"])
        card["specialist_coverage"] = {specialist: {"executions": executions.get(specialist, []),
                 "plan": brief["specialist_plan"][specialist]} for specialist in cp.SPECIALIST_DOMAINS_V24}
        cp._validate_record("design-card", card, state, character, variant)
        validate_compiled_coverage(cp, card)
        cp.validate_body_proportion_anchors(card) if card["morphology"] in {"human", "humanoid"} else None
        record_key = f"design-card:{character}:{variant}"
        approval = {"operator": "system:approved-scope-composition", "at": cp.now(), "sha256": cp.digest(card),
                    "inherited_from": card["stage_receipts"]}
        _store(cp, root, state, record_key, card, approval)
        state["decisions"].append({"kind": "compile-design-card", "key": record_key, **approval})
        return {"key": record_key, "sha256": cp.digest(card), "approved": True, "inherited_from": card["stage_receipts"]}


def validate_compiled_coverage(cp, card):
    coverage = card.get("specialist_coverage")
    cp.ensure(isinstance(coverage, dict) and set(coverage) == set(cp.SPECIALIST_DOMAINS_V24), "V2.5 needs all 13 specialist receipts")
    cp.ensure(isinstance(card.get("stage_receipts"), dict) and card["stage_receipts"], "V2.5 needs stage_receipts")
    for specialist, item in coverage.items():
        cp.ensure(isinstance(item, dict) and isinstance(item.get("executions"), list) and isinstance(item.get("plan"), dict),
                  f"Invalid specialist receipt: {specialist}")
        cp.ensure(item["executions"] or item["plan"].get("status") == "not_needed",
                  f"Specialist remains deferred or unexecuted in the completed card: {specialist}")


def promote(cp, args):
    with cp.locked_project(args.project_root) as (root, state):
        cp.ensure(enabled(state), "Candidate promotion requires a phased project")
        cp.require_text({"operator": args.operator}, "operator")
        cp.ensure(not state["pending_impact"], "Resolve upstream impact first")
        image = cp._image(state, args.image_id)
        cp.ensure(image.get("purpose") == "preview" and image["stage"] == "avatar", "Only a current avatar preview can be promoted")
        prompt_key = cp._record_key("prompt-package", image["character_id"], image["variant_id"], "avatar")
        prompt_record = cp._checked_record(root, state, prompt_key)
        cp.ensure(prompt_record["sha256"] == image["prompt_sha256"], "Candidate prompt changed")
        package = cp.read_json(root / prompt_record["path"])
        resolve_basis(cp, root, state, package, image["character_id"], image["variant_id"], "avatar")
        review = state["reviews"].get(image["id"])
        cp.ensure(review and cp.digest(cp.read_json(root / review["path"])) == review["sha256"], "Candidate review is missing or changed")
        report = cp.read_json(root / review["path"])
        cp.ensure(report.get("verdict") == "pass" and not report.get("adoption_proposals"),
                  "Candidate must pass review; resolve any new-detail adoption before promotion")
        cp.ensure(cp.digest(root / image["path"]) == image["sha256"], "Candidate image changed")
        if getattr(args, "approve_design_basis", False):
            from types import SimpleNamespace
            for record_key in basis_keys(image["character_id"], image["variant_id"], "avatar"):
                sha = package["design_basis"]["records"][record_key]
                record = draft(cp, root, state, record_key)
                cp.ensure(record["sha256"] == sha, "Cannot approve a different candidate design version")
                if not record.get("approval"):
                    kind = "design-brief" if record_key.startswith("design-brief:") else "stage-design"
                    approve(cp, SimpleNamespace(kind=kind, character_id=image["character_id"], variant_id="base",
                                                scope="identity" if kind == "stage-design" else None,
                                                operator=args.operator), root, state)
        resolve_basis(cp, root, state, package, image["character_id"], image["variant_id"], "avatar", force_approved=True)
        image["purpose"] = "production"
        image["promotion"] = {"operator": args.operator, "at": cp.now(), "prompt_sha256": image["prompt_sha256"],
                              "design_basis": package["design_basis"], "review_sha256": review["sha256"]}
        # Reuse the same approval semantics without reopening the locked project.
        for old in state["images"]:
            if old is not image and old["stage"] == "avatar" and old["character_id"] == image["character_id"] and old.get("approval"):
                cp._invalidate(state, image["character_id"], None, "expression")
                old["approval"] = None
        image["approval"] = {"operator": args.operator, "at": cp.now(), "image_sha256": image["sha256"], "review_sha256": review["sha256"]}
        state["decisions"].append({"kind": "promote-candidate", "image_id": image["id"], **image["promotion"]})
        return {"image_id": image["id"], "approved": True, "same_image_sha256": image["sha256"], "promoted": True}

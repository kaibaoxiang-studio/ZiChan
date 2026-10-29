"""One-image production paths for extras in a V3 character project.

The asset-table row remains the stable ID. A group design describes the people
visible in one image; it never turns representative extras into new story facts.
"""
from __future__ import annotations

from pathlib import Path
import re
import shutil


def key(character, variant):
    return f"ensemble-design:{character}:{variant}"


def extra_key(character, variant):
    return f"extra-design:{character}:{variant}"


def design_key(asset_mode, character, variant):
    return extra_key(character, variant) if asset_mode == "speaking_extra" else key(character, variant)


def _style_anchors(style):
    if isinstance(style, str) and style.strip():
        return [style.strip()]
    if isinstance(style, dict):
        values = []
        for value in style.values():
            values.extend(_style_anchors(value))
        return values
    if isinstance(style, list):
        values = []
        for value in style:
            values.extend(_style_anchors(value))
        return values
    return []


def _script_count(row, screenplay=None, variant=None):
    """Recognize only an unambiguous local numeral near the group name."""
    numerals = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
                "六": 6, "七": 7, "八": 8, "九": 9}

    def number(token):
        if token.isdigit():
            return int(token)
        if "万" in token:
            if token.count("万") != 1:
                raise ValueError(f"Unsupported explicit group count: {token}")
            high, low = token.split("万")
            if not high:
                raise ValueError(f"Unsupported explicit group count: {token}")
            if low and low[0] not in {"零", "〇"} and not any(unit in low for unit in "十百千"):
                raise ValueError(f"Ambiguous group count, use an exact quantity: {token}")
            return number(high) * 10000 + (number(low) if low else 0)
        total, pending, last_unit = 0, None, 10000
        for char in token:
            if char in numerals:
                if pending not in {None, 0}:
                    raise ValueError(f"Ambiguous group count, use an exact quantity: {token}")
                pending = numerals[char]
                continue
            unit_value = {"十": 10, "百": 100, "千": 1000}.get(char)
            if unit_value is None or unit_value >= last_unit:
                raise ValueError(f"Unsupported explicit group count: {token}")
            total += (pending if pending is not None else 1) * unit_value
            pending, last_unit = None, unit_value
        if pending is not None:
            if last_unit >= 100 and total and len(token) > 1 and token[-2] not in {"零", "〇"}:
                raise ValueError(f"Ambiguous group count, use an exact quantity: {token}")
            total += pending
        return total

    def explicit(source, start, end):
        # Approximation/bounds are not a script-exact count. Keep them available
        # to the designer as evidence, but never turn “约三名” into exactly 3.
        before, after = source[:start], source[end:]
        return not (re.search(r"(?:大约|大概|差不多|将近|接近|至少|至多|最多|最少|超过|不足|不到|好几|约|近|数|几|上)\s*(?:有|为)?\s*$", before) or
                    re.match(r"\s*(?:左右|上下|以上|以下|余|来|许)", after))

    counts = set()
    # Greedy complete tokens and the left boundary prevent taking 二十 from
    # 一百二十. Unsupported larger notation is rejected, never suffix-counted.
    number_chars = r"0-9零〇一二两三四五六七八九十百千万亿点"
    amount = r"(?<![" + number_chars + r"])(\d+|[零〇一二两三四五六七八九十百千万亿点]+)"
    unit = r"[名个位人]"
    # Asset-table display names often carry a count or a catalogue suffix,
    # e.g. “三个小纸人” or “武士群像”. Match the real named group in evidence,
    # rather than accidentally asking for “三个三个小纸人”. Aliases may carry
    # the scripted noun; unrelated numbers in the same block are never used.
    names = set()
    counted_names = []
    for display in [row["name"], *row.get("aliases", [])]:
        if not isinstance(display, str) or not display.strip():
            continue
        display = display.strip()
        prefix = re.fullmatch(amount + r"\s*" + unit + r"\s*(.+)", display)
        if prefix:
            counted_names.append((display, prefix.group(1)))
            display = prefix.group(2).strip()
        display = re.sub(r"(?:群像|群演)$", "", display).strip()
        if display and display not in {"人", "名", "位", "个", "群像", "群演"}:
            names.add(re.escape(display))
    states = [x for x in row.get("states", []) if variant is None or x.get("id") == variant]
    evidence = [item for part in states for item in part.get("evidence", [])]
    texts = [item.get("text", "") for item in evidence]
    refs = {ref for item in evidence for ref in item.get("source_refs", [])}
    if isinstance(screenplay, dict) and refs:
        for episode in screenplay.get("episodes", []):
            for scene in episode.get("scenes", []):
                for block in scene.get("blocks", []):
                    if refs.intersection(block.get("source_refs", [])):
                        texts.append(block.get("text", ""))
    for source in texts:
        for display, token in counted_names:
            for match in re.finditer(re.escape(display), source):
                if explicit(source, match.start(), match.end()):
                    counts.add(number(token))
        for name in names:
            for pattern in (amount + r"\s*" + unit + r"\s*" + name,
                            name + r"\s*(?:共计|总计|共有|一共|共|有)?\s*" + amount + r"\s*" + unit):
                for match in re.finditer(pattern, source):
                    if explicit(source, match.start(1), match.end()):
                        counts.add(number(match.group(1)))
    if len(counts) > 1:
        raise ValueError(f"Conflicting explicit group counts for {row['name']}: {sorted(counts)}")
    return next(iter(counts)) if counts else None


def _speaker_names(cp, root, state):
    source = root / state["inputs"]["screenplay"]["path"]
    screenplay = cp.load_source(source)
    cp.ensure(isinstance(screenplay, dict) and isinstance(screenplay.get("episodes"), list),
              "Classifying extras by dialogue needs a structured screenplay JSON with episodes/scenes/blocks")
    speakers = set()
    for episode in screenplay["episodes"]:
        for scene in episode.get("scenes", []):
            for block in scene.get("blocks", []):
                if block.get("type") == "dialogue" and isinstance(block.get("speaker"), str):
                    speakers.add(re.sub(r"\s+", "", block["speaker"]))
    return speakers


def mode(cp, root, state, character):
    """Return individual, speaking_extra or ensemble; preserve old approved work."""
    if state.get("pipeline_version", 1) < 3 or not state.get("design_progression") == "phased":
        return "individual"
    row = next((x for x in state["roster"] if x["id"] == character), None)
    cp.ensure(row is not None, f"Unknown character ID: {character}")
    if row.get("tier") not in {"群演", "群像"}:
        return "individual"
    if any(x.get("character_id") == character and x.get("approval") and
           x.get("stage") in cp.IDENTITY_STAGES for x in state["images"]):
        return "individual"
    if any(k.startswith((f"stage-design:identity:{character}:", f"design-card:{character}:")) and
           v.get("approval") for k, v in state["records"].items()):
        return "individual"
    names = {re.sub(r"\s+", "", x) for x in [row["name"], *row.get("aliases", [])] if x}
    speakers = _speaker_names(cp, root, state)
    if names & speakers:
        return "speaking_extra"
    ambiguous = sorted(s for s in speakers for n in names
                       if s.startswith(n) and s != n and
                       re.fullmatch(r"[甲乙丙丁一二三四五六七八九十\dA-Za-z]+", s[len(n):]))
    cp.ensure(not ambiguous,
              f"Group asset {character} contains individually speaking members {ambiguous}; split them into asset IDs")
    return "ensemble"


def validate(cp, root, state, data, character, variant):
    cp.ensure(mode(cp, root, state, character) == "ensemble", "Only non-speaking group extras use ensemble-design")
    cp.ensure(data.get("schema_version") == "GroupEnsembleDesignV1" and
              data.get("character_id") == character and data.get("variant_id") == variant,
              "Group design target/schema mismatch")
    cp.require_known_variant(state, character, variant)
    expected = {x: cp._checked_record(root, state, x)["sha256"] for x in
                ("script-context", "visual-bible", "cast-plan")}
    cp.ensure(data.get("parent_refs") == expected, "Group design must bind current script, cast and visual style")
    cp.require_text(data, "narrative_function")
    cp.require_text(data, "world_style_translation")
    cp.require_text(data, "shared_visual_grammar")
    cp.require_text(data, "variation_logic")
    cp.require_text(data, "quantity_basis")
    cp.require_text(data, "arrangement")
    cp.require_list(data, "source_refs")
    cp.ensure(data["source_refs"], "Group design needs script source_refs")
    row = next(x for x in state["roster"] if x["id"] == character)
    bible = cp.read_json(root / state["records"]["visual-bible"]["path"])
    style_anchors = _style_anchors(bible["style"])
    cp.ensure(all(anchor in data["world_style_translation"] for anchor in style_anchors),
              "Group design must carry the approved project visual style")
    known_refs = {ref for item in row.get("states", []) for e in item.get("evidence", [])
                  for ref in e.get("source_refs", [])}
    if known_refs:
        cp.ensure(set(data["source_refs"]) & known_refs,
                  "Group source_refs must include an asset-table script reference")
    cp.ensure(data.get("quantity_status") in {"script_explicit", "representative_choice"},
              "Group quantity must distinguish script count from representative choice")
    count = data.get("member_count")
    cp.ensure(type(count) is int and count >= 1, "Group member_count must be a positive integer")
    explicit = data.get("script_count")
    cp.ensure(explicit is None or type(explicit) is int and explicit >= 1,
              "script_count must be a positive number or null")
    if explicit is not None:
        cp.ensure(data["quantity_status"] == "script_explicit" and count == explicit,
                  "A script-explicit group must show exactly the scripted number")
    else:
        cp.ensure(data["quantity_status"] == "representative_choice",
                  "Unknown group size requires a labeled representative choice")
    screenplay = cp.load_source(root / state["inputs"]["screenplay"]["path"])
    existing = state.get("records", {}).get(key(character, variant), {})
    frozen_approval = (existing.get("approval") and not existing.get("stale") and
                       existing.get("sha256") == cp.digest(data))
    # Correct new count extraction on new/revised designs. Reading an unchanged
    # approved historical design must not silently introduce a new gate.
    found_count = None if frozen_approval else _script_count(row, screenplay, variant)
    if found_count is not None:
        cp.ensure(explicit == found_count and count == found_count,
                  "Group figure count must match the explicit asset-table script evidence")
    members = data.get("members")
    cp.ensure(isinstance(members, list) and len(members) == count,
              "Group design needs one concrete member per depicted person")
    slots = []
    for member in members:
        for field in ("slot", "body_and_posture", "face_and_hair", "costume_structure",
                      "color_and_material", "action_or_prop"):
            cp.require_text(member, field)
        cp.ensure(member.get("evidence_status") in {"script_fact", "inference", "creative_choice", "mixed"},
                  "Each member needs an evidence boundary")
        slots.append(member["slot"])
    cp.ensure(len(slots) == len(set(slots)), "Group member slots must be unique")
    cp.ensure(len({m["body_and_posture"] + m["face_and_hair"] for m in members}) == count,
              "Group members cannot all reuse the same face and build")
    cp.require_list(data, "unresolved")
    cp.ensure(data.get("new_lore_policy") in {"none", "pending_approval"},
              "New group lore must be explicitly identified")
    if data["new_lore_policy"] == "pending_approval":
        cp.ensure(data["unresolved"], "Unapproved new lore cannot be silently finalized")


def validate_extra(cp, root, state, data, character, variant):
    cp.ensure(mode(cp, root, state, character) == "speaking_extra",
              "Only speaking extras use extra-design")
    cp.ensure(data.get("schema_version") == "SpeakingExtraDesignV1" and
              data.get("character_id") == character and data.get("variant_id") == variant,
              "Speaking extra design target/schema mismatch")
    cp.require_known_variant(state, character, variant)
    expected = {x: cp._checked_record(root, state, x)["sha256"] for x in
                ("script-context", "visual-bible", "cast-plan")}
    cp.ensure(data.get("parent_refs") == expected,
              "Speaking extra design must bind current script, cast and visual style")
    morphology = data.get("morphology", "human")
    cp.ensure(morphology in {"human", "humanoid", "nonhuman"}, "Unknown speaking extra morphology")
    for field in ("narrative_function", "spoken_line", "world_style_translation",
                  "body_and_posture", "color_and_material", "prop_and_action"):
        cp.require_text(data, field)
    if morphology in {"human", "humanoid"}:
        for field in ("face_and_hair", "costume_front", "costume_back"):
            cp.require_text(data, field)
    else:
        details = data.get("morphology_details")
        cp.ensure(isinstance(details, dict) and details, "Nonhuman speaking extra needs concrete morphology_details")
        for field in details:
            cp.require_text(details, field)
        cp.ensure(isinstance(data.get("execution_layout"), dict) and data["execution_layout"],
                  "Nonhuman speaking extra needs an approved one-sheet execution_layout")
        cp.require_text(data["execution_layout"], "description")
    screenplay = cp.load_source(root / state["inputs"]["screenplay"]["path"])
    row = next(x for x in state["roster"] if x["id"] == character)
    names = {re.sub(r"\s+", "", x) for x in [row["name"], *row.get("aliases", [])] if x}
    spoken = [(block.get("text", ""), block.get("source_refs", []))
              for episode in screenplay["episodes"] for scene in episode.get("scenes", [])
              for block in scene.get("blocks", []) if block.get("type") == "dialogue" and
              re.sub(r"\s+", "", block.get("speaker", "")) in names]
    cp.ensure(any(data["spoken_line"] in text for text, _ in spoken),
              "Speaking extra design must quote a scripted line")
    cp.require_list(data, "source_refs")
    cp.ensure(data["source_refs"] and any(set(data["source_refs"]) & set(refs) for _, refs in spoken),
              "Speaking extra source_refs must include its dialogue source")
    bible = cp.read_json(root / state["records"]["visual-bible"]["path"])
    cp.ensure(all(anchor in data["world_style_translation"] for anchor in _style_anchors(bible["style"])),
              "Speaking extra must carry approved project visual style")
    cp.ensure(data.get("evidence_status") in {"script_fact", "inference", "creative_choice", "mixed"},
              "Speaking extra design needs an evidence boundary")
    cp.require_list(data, "unresolved")
    cp.ensure(data.get("new_lore_policy") in {"none", "pending_approval"},
              "New lore must be explicitly identified")
    if data["new_lore_policy"] == "pending_approval":
        cp.ensure(data["unresolved"], "Unapproved new lore cannot be silently finalized")


def submit(cp, args, root, state):
    data = cp.read_json(args.file)
    character, variant = args.character_id, args.variant_id or "base"
    speaking = args.kind == "extra-design"
    (validate_extra if speaking else validate)(cp, root, state, data, character, variant)
    record_key = extra_key(character, variant) if speaking else key(character, variant)
    sha = cp.digest(data)
    prior = state["records"].get(record_key)
    if prior and prior["sha256"] == sha and not prior.get("stale"):
        return {"key": record_key, "status": "unchanged", "sha256": sha}
    if prior:
        cp._invalidate(state, character, variant, args.kind)
    path = root / "records" / record_key.replace(":", "/") / f"{sha[:12]}.json"
    cp.write_json(path, data)
    state["records"][record_key] = {"path": str(path.relative_to(root)), "sha256": sha,
                                    "submitted_at": cp.now(), "approval": None, "stale": False}
    return {"key": record_key, "sha256": sha, "status": "awaiting-approval"}


def approve(cp, args, root, state):
    character, variant = args.character_id, args.variant_id or "base"
    speaking = args.kind == "extra-design"
    record_key = extra_key(character, variant) if speaking else key(character, variant)
    record = state["records"].get(record_key)
    cp.ensure(record and not record.get("stale"), f"Missing group design: {record_key}")
    data = cp.read_json(root / record["path"])
    cp.ensure(cp.digest(data) == record["sha256"], "Group design changed after submission")
    (validate_extra if speaking else validate)(cp, root, state, data, character, variant)
    cp.ensure(not data["unresolved"], "Resolve group design decisions before approval")
    cp.require_text({"operator": args.operator}, "operator")
    record["approval"] = {"operator": args.operator, "at": cp.now(), "sha256": record["sha256"]}
    state["decisions"].append({"kind": "approve-record", "key": record_key, **record["approval"]})
    return {"key": record_key, "approved": True, "sha256": record["sha256"]}


def resolve(cp, root, state, package, character, variant):
    asset_mode = mode(cp, root, state, character)
    cp.ensure(asset_mode in {"ensemble", "speaking_extra"}, "This asset uses the multi-stage route")
    record_key = design_key(asset_mode, character, variant)
    record = cp._checked_record(root, state, record_key)
    supplied = package.get("design_basis", {}).get("records")
    cp.ensure(supplied == {record_key: record["sha256"]},
              "Group prompt must bind the current approved group design")
    data = cp.read_json(root / record["path"])
    (validate_extra if asset_mode == "speaking_extra" else validate)(cp, root, state, data, character, variant)
    return data


def validate_prompt(cp, package, design):
    cp.ensure(package.get("morphology") == "group", "Group prompt morphology must be group")
    cp.ensure(package.get("anchor_images") == {}, "Group sheet has no individual identity image anchors")
    count = design["member_count"]
    layout = package.get("layout") or {}
    slots = [x["slot"] for x in design["members"]]
    cp.ensure(layout.get("type") == "ensemble_lineup" and layout.get("single_canvas") is True and
              layout.get("full_body") is True and layout.get("member_count") == count and
              layout.get("ordered_slots") == slots,
              "Group layout must show every member full body on one canvas in approved order")
    cp.ensure(not any(k in layout for k in ("top_left", "top_right", "bottom_left", "bottom_right")),
              "Group image cannot use a four-panel individual layout")
    ratio = package.get("aspect_ratio")
    cp.ensure(isinstance(ratio, str) and re.fullmatch(r"[1-9]\d*:[1-9]\d*", ratio),
              "Group prompt needs a numeric aspect_ratio")
    wide, tall = map(int, ratio.split(":"))
    if count > 1:
        cp.ensure(wide > tall, "Multiple extras need a horizontal canvas")
    else:
        cp.ensure(ratio == "9:16", "A single non-speaking extra uses a 9:16 full-body canvas")
    cp.require_text(package, "aspect_ratio_basis")
    for prompt in package["prompts"]:
        text = prompt["text"]
        cp.ensure(design["world_style_translation"] in text,
                  "Each group prompt must carry the approved style translation verbatim")
        cp.ensure(ratio in text and str(count) in text and all(slot in text for slot in slots),
                  "Group prompt must state ratio, exact depicted count and ordered member slots")
        cp.ensure("全身" in text and "风格" in text,
                  "Group prompt must state full-body visibility and project visual style")
    checks = "\n".join(package["acceptance_checks"])
    cp.ensure(all(x in checks for x in (ratio, "人数", "全身", "顺序", "风格")),
              "Group review must check canvas, count, full bodies, order and project style")
    selected = [(f"{member['slot']}.{field}", member[field])
                for member in design["members"]
                for field in ("body_and_posture", "face_and_hair", "costume_structure",
                              "color_and_material", "action_or_prop")]
    _validate_design_coverage(cp, package, selected)


def _validate_design_coverage(cp, package, selected):
    """Apply to new submissions only; approved historical prompts stay readable.

    These designs predate structured cue items. Their visible design fields are
    therefore the frozen cue units. Repeating a broad label or a slot name must
    not erase an approved person's face, construction, materials or prop owner.
    """
    checks = "\n".join(package["acceptance_checks"])
    for field, cue in selected:
        cp.ensure(isinstance(cue, str) and cue.strip(), f"Approved extra design missing {field}")
        for prompt in package["prompts"]:
            cp.ensure(cue in prompt["text"], f"Extra prompt {prompt['id']} dropped approved {field}")
        cp.ensure(cue in checks, f"Extra acceptance checks do not inspect approved {field}")


def validate_extra_prompt(cp, package, design):
    morphology = design.get("morphology", "human")
    cp.ensure(package.get("morphology") == morphology, "Speaking extra prompt morphology must match its approved design")
    cp.ensure(package.get("anchor_images") == {}, "Single-sheet extra has no identity image prerequisites")
    cp.ensure(package.get("aspect_ratio") == "9:16", "Speaking extra execution sheet must be 9:16")
    required_layout = {"top_left": "front_face", "top_right": "three_quarter_face_45",
                       "bottom_left": "headless_enlarged_front_costume",
                       "bottom_right": "complete_back_head_to_shoes"}
    human = morphology in {"human", "humanoid"}
    expected_layout = required_layout if human else design.get("execution_layout")
    cp.ensure(isinstance(expected_layout, dict) and expected_layout and package.get("layout") == expected_layout,
              "Speaking extra layout must match its approved morphology-specific execution sheet")
    tokens = ("9:16", "正脸", "45", "无头", "背面") if human else ("9:16",)
    for prompt in package["prompts"]:
        content = prompt["text"]
        cp.ensure(all(token in content for token in tokens),
                  "Speaking extra prompt must state the one-sheet layout")
        cp.ensure(design["world_style_translation"] in content,
                  "Speaking extra prompt must carry approved style verbatim")
    checks = "\n".join(package["acceptance_checks"])
    cp.ensure(all(token in checks for token in (*tokens, "风格")),
              "Speaking extra review must check its approved layout and project style")
    fields = (("face_and_hair", "body_and_posture", "costume_front", "costume_back",
               "color_and_material", "prop_and_action") if human else
              ("body_and_posture", "color_and_material", "prop_and_action"))
    selected = [(field, design[field]) for field in fields]
    if not human:
        selected.extend((f"morphology_details.{field}", cue)
                        for field, cue in design["morphology_details"].items())
        selected.append(("execution_layout.description", expected_layout["description"]))
    _validate_design_coverage(cp, package, selected)


def package(cp, args, root, state):
    character, variant = args.character_id, args.variant_id or "base"
    asset_mode = mode(cp, root, state, character)
    cp.ensure(asset_mode in {"ensemble", "speaking_extra"}, "This asset uses the multi-stage pack route")
    cp.ensure(not state["pending_impact"], "Unresolved upstream impact")
    cp.require_known_variant(state, character, variant)
    for source in state["inputs"].values():
        cp.ensure(cp.digest(root / source["path"]) == source["sha256"], "Imported source changed")
    record_key = design_key(asset_mode, character, variant)
    keys = ["script-context", "visual-bible", "cast-plan", record_key,
            cp._record_key("prompt-package", character, variant, "execution")]
    records = {k: cp._checked_record(root, state, k) for k in keys}
    image = cp._checked_image(root, state, "execution", character, variant)
    out = Path(args.output).expanduser().resolve()
    cp.ensure(not out.exists(), f"Output already exists: {out}")
    out.mkdir(parents=True)
    copied = []
    for item in [*records.values(), *cp.image_delivery_files(state, image)]:
        source = root / item["path"]
        target = out / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append({"path": str(target.relative_to(out)), "sha256": cp.digest(target)})
    for record_key, record in records.items():
        if record_key.startswith("prompt-package:"):
            copied.append(cp.copy_prompt_text_delivery(root, out, record))
    refs = [x for x in state["references"] if x.get("character_id") in {None, character}]
    for item in refs:
        source = root / item["path"]
        cp.ensure(cp.digest(source) == item["sha256"], "Group reference changed")
        target = out / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append({"path": str(target.relative_to(out)), "sha256": cp.digest(target)})
    plugin_root = Path(cp.__file__).resolve().parents[1]
    for relative in ("knowledge/source-register.json", "sources.lock.json"):
        source = plugin_root / relative
        cp.ensure(source.is_file(), f"Missing plugin provenance: {relative}")
        target = out / "plugin-provenance" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append({"path": str(target.relative_to(out)), "sha256": cp.digest(target)})
    design = cp.read_json(root / records[record_key]["path"])
    manifest = {"schema_version": ("CharacterSpeakingExtraPackV1" if asset_mode == "speaking_extra"
                                    else "CharacterEnsemblePackV1"), "plugin_version": cp.PLUGIN_VERSION,
                "project_id": state["project_id"], "character_id": character,
                "asset_name": next(x["name"] for x in state["roster"] if x["id"] == character),
                "variant_id": variant, "variant_name": cp.variant_name(state, character, variant),
                "member_count": design.get("member_count", 1),
                "quantity_status": design.get("quantity_status", "scripted_speaker"),
                "approved_image": {"path": image["path"], "sha256": image["sha256"],
                                   "approval": image["approval"]},
                "record_approvals": {k: v["approval"] for k, v in records.items()},
                "input_sources": state["inputs"], "reference_images": refs,
                "files": copied, "created_at": cp.now(),
                "decisions": [x for x in state["decisions"] if x.get("key") in keys or x.get("image_id") == image["id"]]}
    cp.write_json(out / "manifest.json", manifest)
    return {"asset_pack": str(out), "files": len(copied) + 1}

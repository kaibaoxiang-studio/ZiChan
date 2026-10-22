#!/usr/bin/env python3
"""Check the handoff contract for a character specialist proposal."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def require_text(data, key):
    if not isinstance(data.get(key), str) or not data[key].strip():
        raise ValueError(f"{key} must contain text")


def require_list(data, key):
    if not isinstance(data.get(key), list):
        raise ValueError(f"{key} must be a list")


def validate(data):
    if not isinstance(data, dict) or data.get("schema_version") not in {"CharacterSpecialistProposalV1", "CharacterSpecialistProposalV1.1"}:
        raise ValueError("Expected CharacterSpecialistProposalV1 or V1.1")
    for key in ("specialist", "character_id", "scope"):
        require_text(data, key)
    for key in ("facts", "options", "unresolved"):
        require_list(data, key)
    for fact in data["facts"]:
        if not isinstance(fact, dict):
            raise ValueError("Each fact must be an object")
        require_text(fact, "text")
        require_list(fact, "source_refs")
        if not fact["source_refs"]:
            raise ValueError("Facts need source_refs")
    reason = data.get("not_applicable_reason")
    if reason is not None and not isinstance(reason, str):
        raise ValueError("not_applicable_reason must be text or null")
    if reason and reason.strip():
        if data["options"]:
            raise ValueError("Not-applicable proposals cannot contain design options")
        if data.get("recommended_option_id") not in (None, ""):
            raise ValueError("Not-applicable proposals cannot recommend an option")
        return {"applicable": False, "options": 0}
    options = data["options"]
    if not 2 <= len(options) <= 3:
        if len(options) != 1 or not isinstance(data.get("single_option_reason"), str) or not data["single_option_reason"].strip():
            raise ValueError("Applicable proposals need two or three options, or a reason for one")
    ids = []
    for option in options:
        if not isinstance(option, dict):
            raise ValueError("Each option must be an object")
        for key in ("id", "visible_design", "rationale", "comparison_difference", "production_check"):
            require_text(option, key)
        if data["schema_version"] == "CharacterSpecialistProposalV1.1":
            elements = option.get("design_elements")
            if not isinstance(elements, list) or len(elements) < 2:
                raise ValueError("V1.1 options need at least two concrete design_elements")
            for element in elements:
                if not isinstance(element, dict):
                    raise ValueError("Each design element must be an object")
                for key in ("part", "visible_feature", "placement_or_structure", "basis"):
                    require_text(element, key)
        ids.append(option["id"])
    if len(set(ids)) != len(ids):
        raise ValueError("Option IDs must be unique")
    if data.get("recommended_option_id") not in ids:
        raise ValueError("recommended_option_id must name a listed option")
    return {"applicable": True, "options": len(options)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    result = validate(json.loads(args.file.read_text(encoding="utf-8")))
    print(json.dumps({"valid": True, "file": str(args.file.resolve()), **result}, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Read-only validation of a Harness prompt delivery against its real project.

This module never submits, approves, copies knowledge or changes project state.
It runs in its own interpreter so imports bind to this exact plugin snapshot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import character_project as cp


def read_only_knowledge(api, root, refs, specialist=None, strict=True, archive=False):
    """Use the original integrity checks without _knowledge's cache writes."""
    api.ensure(isinstance(refs, list) and refs, "Inline execution needs real knowledge_refs")
    plugin = Path(cp.__file__).resolve().parents[1]
    locked = api.read_json(plugin / 'knowledge-lock.json')['snapshots'] if strict else []
    for item in refs:
        api.ensure(isinstance(item, dict), "Knowledge reference must be an object")
        sha = item.get('sha256', '')
        api.ensure(isinstance(sha, str) and len(sha) == 64 and all(x in '0123456789abcdef' for x in sha),
                   'Knowledge reference SHA must be hexadecimal SHA-256')
        if strict:
            api.ensure(any(row.get('path') == item.get('path') and row.get('rules_sha256') == sha and
                           specialist in row.get('capability_ids', []) for row in locked),
                       f'Knowledge reference is not locked for specialist {specialist}')
        snapshot = root / 'knowledge-snapshots' / sha
        if snapshot.is_file():
            api.ensure(api.digest(snapshot) == sha, 'Project knowledge snapshot changed')
        else:
            path = (plugin / item.get('path', '')).resolve()
            api.ensure(path.is_relative_to(plugin) and path.is_file(), 'Knowledge file must be inside this plugin')
            api.ensure(api.digest(path) == sha, 'Knowledge reference SHA mismatch')


def validate(package_path, inputs):
    cp.ensure(isinstance(inputs, dict), 'Prompt delivery needs task inputs')
    for name in ('project_root', 'character_id', 'stage'):
        cp.require_text(inputs, name)
    root = Path(inputs['project_root']).expanduser().resolve()
    cp.ensure((root / 'project.json').is_file(), 'Prompt delivery needs a real character project')
    state = cp.read_json(root / 'project.json')
    cp.ensure(state.get('schema_version') == cp.SCHEMA, 'Unsupported project state')
    cp.ensure(not state.get('pending_impact'), 'Resolve upstream impact before prompt delivery')
    for source in state.get('inputs', {}).values():
        path = (root / source['path']).resolve()
        cp.ensure(path.is_relative_to(root) and path.is_file(), 'Project source is missing or outside project')
        cp.ensure(cp.digest(path) == source['sha256'], 'Project source changed')
    character, variant, stage = inputs['character_id'], inputs.get('variant_id', 'base'), inputs['stage']
    modern = state.get('pipeline_version', 1) >= 2
    cp.ensure(stage in cp.pipeline_stages(state), 'Stage is not available in this project pipeline')
    cp.ensure(character in {row['id'] for row in state['roster']}, 'Unknown character ID')
    cp.require_known_variant(state, character, variant)
    if modern and stage in cp.IDENTITY_STAGES:
        cp.ensure(variant == 'base', 'Identity stages belong to base')
    content = cp.read_json(package_path)
    cp._validate_record('prompt-package', content, state, character, variant, stage)
    # Approved inline work may read package knowledge without mutating the project.
    cp.phased._knowledge = read_only_knowledge
    api = cp._runtime()
    asset_mode = cp.ensemble.mode(api, root, state, character) if modern else 'individual'
    card_record = None
    if asset_mode in {'ensemble', 'speaking_extra'}:
        cp.ensure(stage == 'execution', 'Extras have one execution sheet')
        card = cp.ensemble.resolve(api, root, state, content, character, variant)
    elif cp.phased.enabled(state):
        card = cp.phased.resolve_basis(api, root, state, content, character, variant, stage)
    else:
        card_record = cp._checked_record(root, state, cp._record_key('design-card', character, variant))
        cp.ensure(content['design_card_sha256'] == card_record['sha256'], 'Prompt refers to another design card')
        card = cp.read_json(root / card_record['path'])
    anchors = {}
    if asset_mode == 'individual':
        for prior in cp.image_predecessors(state, stage):
            prior_variant = 'base' if modern and prior in cp.IDENTITY_STAGES else variant
            anchors[prior] = cp._checked_image(root, state, prior, character, prior_variant)['sha256']
    cp.ensure(content['anchor_images'] == anchors, 'Prompt anchor versions do not match approvals')
    if asset_mode in {'ensemble', 'speaking_extra'}:
        (cp.ensemble.validate_extra_prompt if asset_mode == 'speaking_extra' else cp.ensemble.validate_prompt)(api, content, card)
    else:
        cp.validate_model_card_attire(content, card)
        human = card.get('morphology') in {'human', 'humanoid'}
        if cp.phased.enabled(state) and state.get('pipeline_version', 1) >= 3 and human and stage in {'avatar', 'execution'}:
            design_scope = 'identity' if stage == 'avatar' else 'costume'
            record_key = cp.phased.key('stage-design', character, variant, design_scope)
            record = (cp.phased.draft(api, root, state, record_key) if content.get('purpose') == 'preview'
                      else cp._checked_record(root, state, record_key))
            design = cp.read_json(root / record['path'])
            cp.phased.validate_prompt_detail_contract(api, design, root=root, state=state,
                strict=design.get('execution_contract_version') == 2 or not record.get('approval'))
            cp.phased.validate_prompt_detail_coverage(api, root, state, content, character, variant, stage)
        if stage == 'expression' and human:
            key = cp._record_key('prompt-package', character, 'base' if modern else variant, 'avatar')
            avatar = cp._checked_record(root, state, key)
            cp.validate_expression_attire_transition(content, cp.read_json(root / avatar['path']))
        if stage == 'full_body' and human and (cp.phased.enabled(state) or card.get('schema_version') in {'CharacterDesignCardV2.2', 'CharacterDesignCardV2.4'}):
            cp.validate_full_body_prompt_proportions(content, card)
        if stage == 'execution':
            if cp.phased.enabled(state) and state.get('pipeline_version', 1) >= 3:
                cp.phased.validate_scene_prompt_coverage(api, root, state, content, character, variant)
            cp.ensure(content.get('morphology') == card['morphology'], 'Execution morphology differs from approved design')
            if card['morphology'] != 'human':
                cp.ensure(isinstance(card.get('execution_layout'), dict) and card['execution_layout'], 'Nonhuman layout missing')
                cp.ensure(content.get('layout') == card['execution_layout'], 'Execution layout differs from approved design')
    return {'valid': True, 'project_id': state.get('project_id'), 'character_id': character,
            'variant_id': variant, 'stage': stage, 'asset_mode': asset_mode,
            'package_sha256': cp.digest(content), 'project_write_performed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.package, json.load(sys.stdin)), ensure_ascii=False))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

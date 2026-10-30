"""Read-only validation of a Harness prompt delivery against its real project.

This module never submits, approves, copies knowledge or changes project state.
It runs in its own interpreter so imports bind to this exact plugin snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import character_project as cp
from export_prompt_text import render_prompt_text
from prompt_fidelity import design_inventory, validate_fidelity, check_hard_markers
from prompt_canvas import resolve_canvas, validate_canvas_package, validate_canvas_text


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
        snapshot = root / 'knowledge-snapshots' / sha
        if cp.phased._APPROVED_KNOWLEDGE_READ.get() and not archive:
            if snapshot.is_file():
                api.ensure(api.digest(snapshot) == sha, 'Project knowledge snapshot changed')
                continue
            api.ensure(any(row.get('path') == item.get('path') and row.get('rules_sha256') == sha and
                           specialist in row.get('capability_ids', []) for row in locked),
                       'Approved historical knowledge archive is missing')
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


def frozen_inventory(delivery, stage, source, resolved_delivery=None):
    """Use the design validator's single, read-only parent/delta projection."""
    if resolved_delivery is None and source.get('project_root'):
        import verify_design_delivery as design_delivery
        frozen = design_delivery.validate_frozen(source)
        resolved_delivery = frozen.get('resolved_delivery', delivery)
    return design_inventory(resolved_delivery or delivery, stage)


def _frozen_candidate(package_path, inputs):
    """Explicit task-local branch, never a fallback after project validation fails."""
    import verify_design_delivery as design_delivery
    source = inputs.get('design_source')
    cp.ensure(isinstance(source, dict) and source.get('kind') == 'task_frozen_delivery',
              'Independent candidate needs an explicit task_frozen_delivery source')
    # A declared project remains a project even if the task also carries a draft.
    if 'project_root' in inputs:
        cp.require_text(inputs, 'project_root')
        declared_root = Path(inputs['project_root']).expanduser().resolve()
        cp.ensure((declared_root / 'project.json').is_file(), 'Prompt delivery needs a real character project')
    else:
        declared_root = None
    frozen = design_delivery.validate_frozen(source)
    delivery, design_inputs = frozen['delivery'], frozen['inputs']
    cp.ensure(frozen.get('validation', {}).get('valid') is True, 'Frozen design did not pass its real task validation')
    source_root = source.get('project_root') or design_inputs.get('project_root')
    if declared_root is not None:
        cp.ensure(source_root and Path(source_root).expanduser().resolve() == declared_root,
                  'Candidate project must match the frozen design project constraints')
    if 'parent_refs' in inputs:
        cp.ensure(inputs['parent_refs'] == source.get('parent_refs', {}),
                  'Candidate parents differ from the actual task constraints')
    if source_root:
        for field in ('character_id', 'variant_id'):
            if field in inputs:
                cp.ensure(inputs[field] == design_inputs.get(field, 'base' if field == 'variant_id' else None),
                          'Candidate frozen target differs from the actual task')
    package = cp.read_json(package_path)
    cp.ensure(package.get('schema_version') == 'CharacterPromptPackageV1', 'Expected CharacterPromptPackageV1')
    cp.ensure(package.get('design_source') == source, 'Candidate design_source differs from actual task inputs')
    cp.ensure(package.get('purpose') == 'candidate' and inputs.get('purpose', 'candidate') == 'candidate',
              'Task-local frozen delivery is candidate only; it cannot inherit formal approval')
    cp.ensure(package.get('approved') is not True, 'A candidate cannot claim formal approval')
    stage = inputs['stage']
    cp.ensure(stage in {'avatar', 'expression', 'full_body', 'costume_design', 'execution'}, 'Unsupported candidate stage')
    cp.ensure(package.get('stage') == stage, 'Prompt stage mismatch')
    cp.ensure(str(package.get('target_model', '')).startswith('gpt-image-2.5'), 'Prompts must target GPT Image 2.5')
    cp.ensure(not package.get('anchor_images'), 'Task-local candidate cannot assert formal image anchors')
    cp.ensure(not package.get('design_basis') and not package.get('design_card_sha256'),
              'Task-local candidate must use its frozen delivery, not a substituted formal basis')
    if not source_root:
        cp.ensure(not any(key in inputs or key in package for key in ('character_id', 'variant_id', 'project_id')),
                  'Standalone candidate cannot manufacture formal IDs or a project')
    else:
        for field in ('character_id', 'variant_id'):
            if field in package:
                target = inputs.get(field, design_inputs.get(field))
                cp.ensure(target is not None and package[field] == target, 'Candidate formal target differs from actual task')
    if 'subject' in package:
        cp.ensure(package['subject'] == delivery['data'].get('subject'), 'Candidate subject differs from frozen design')
    cp.require_list(package, 'reference_images')
    cp.require_list(package, 'acceptance_checks')
    cp.ensure(package['acceptance_checks'] and all(isinstance(x, str) and x.strip() for x in package['acceptance_checks']),
              'Candidate needs concrete text acceptance checks')
    canvas = resolve_canvas(inputs, stage, design_inputs)
    validate_canvas_package(package, canvas)
    result = validate_fidelity(package, frozen_inventory(delivery, stage, source, frozen.get('resolved_delivery')), source['sha256'])
    mode = inputs.get('delivery_mode', 'files')
    cp.ensure(mode in {'files', 'text'}, 'A prompt request cannot be downgraded to discussion')
    if mode == 'files':
        text_path = Path(package_path).with_name('提示词.txt')
        cp.ensure(text_path.is_file() and not text_path.is_symlink(), 'Prompt files need the real same-source 提示词.txt')
        cp.ensure(text_path.read_bytes() == render_prompt_text(package).encode('utf-8'),
                  '提示词.txt must be the exact UTF-8 export of prompts[].text')
    return {'valid': True, 'purpose': 'candidate', 'stage': stage,
            'package_sha256': cp.digest(package), 'design_sha256': source['sha256'],
            'aspect_ratio': canvas['aspect_ratio'], 'aspect_ratio_source': canvas['source'],
            'project_write_performed': False, 'approved': False, **result}


def _task_text_candidate(content, inputs, stage):
    """Bind an explicitly fileless candidate to actual current design prose.

    A message locator and a text hash identify the supplied source; neither is
    evidence that the design is mature or that prose retains every visible
    structure. The controller still performs that review. Optional preserve
    excerpts protect only selected, unambiguous markers, never all story text.
    This branch performs no filesystem operations or formal-state resolution.
    """
    source = inputs['design_source']
    cp.ensure(isinstance(source, dict) and source.get('kind') == 'task_text_design',
              'Fileless candidate needs an actual task_text_design source')
    cp.ensure(inputs.get('purpose', 'candidate') == 'candidate',
              'Task text design is candidate only; it cannot become a formal prompt')
    forbidden = {'project_root', 'parent_refs', 'character_id', 'variant_id', 'project_id',
                 'anchor_images', 'design_basis', 'design_card_sha256', 'approved'}
    cp.ensure(not forbidden.intersection(inputs),
              'Task text design cannot carry a project, formal IDs, parents, approval or anchors')
    cp.ensure(set(source) <= {'kind', 'text', 'source_ref', 'text_sha256', 'preserve'},
              'Task text design source only accepts current prose, message locator and optional text guards')
    cp.require_text(source, 'text')
    cp.require_text(source, 'source_ref')
    sha = hashlib.sha256(source['text'].encode('utf-8')).hexdigest()
    if 'text_sha256' in source:
        cp.ensure(source['text_sha256'] == sha, 'Task text design SHA changed')
    preserve = source.get('preserve', [])
    cp.ensure(isinstance(preserve, list) and all(isinstance(value, str) and value.strip() and
              value in source['text'] for value in preserve),
              'Optional text preserve guards must be actual nonempty source excerpts')
    canvas = resolve_canvas(inputs, stage)
    validate_canvas_text(content, canvas)
    for index, value in enumerate(preserve):
        check_hard_markers(value, content, f'task_text_design.preserve.{index}')
    return {'valid': True, 'purpose': 'candidate', 'stage': stage,
            'project_write_performed': False, 'approved': False,
            'basis': {'text_design_sha256': sha, 'source_ref': source['source_ref']},
            'aspect_ratio': canvas['aspect_ratio'], 'aspect_ratio_source': canvas['source'],
            'verification_scope': ('current-text-design-binding-canvas-and-selected-hard-markers'
                                   if preserve else 'current-text-design-binding-and-canvas'),
            'selected_hard_guard_count': len(preserve),
            'source_locator_authenticated_by_code': False,
            'controller_semantic_review_required': True, 'semantic_equivalence_proven_by_code': False,
            'design_maturity_proven_by_code': False, 'image_review_performed': False}


def validate_text(content, inputs):
    """Explicit dialogue-only exception: check real basis without inventing receipts.

    The controller's task review remains necessary. Unlike a structured file
    package, plain prose cannot provide a machine-verifiable detail/span map.
    This function does not manufacture a semantic-review pass on its behalf.
    """
    cp.ensure(isinstance(inputs, dict), 'Text prompt delivery needs actual task inputs')
    cp.ensure(inputs.get('delivery_mode') == 'text', 'Prompt text-only delivery must be an explicit actual task exception')
    cp.ensure(isinstance(content, str) and content.strip(), 'Text prompt needs its actual complete body')
    cp.require_text(inputs, 'request')
    cp.require_text(inputs, 'stage')
    stage = inputs['stage']
    design_inputs = None
    cp.ensure(stage in {'avatar', 'expression', 'full_body', 'costume_design', 'execution'}, 'Unsupported prompt stage')
    if isinstance(inputs.get('design_source'), dict) and inputs['design_source'].get('kind') == 'task_text_design':
        return _task_text_candidate(content, inputs, stage)
    declared = None
    if 'project_root' in inputs:
        cp.require_text(inputs, 'project_root')
        declared = Path(inputs['project_root']).expanduser().resolve()
        cp.ensure((declared / 'project.json').is_file(), 'Prompt delivery needs a real character project')
    if 'design_source' in inputs:
        import verify_design_delivery as design_delivery
        source = inputs['design_source']
        frozen = design_delivery.validate_frozen(source)
        design_inputs = frozen['inputs']
        cp.ensure(inputs.get('purpose', 'candidate') == 'candidate', 'Frozen text draft cannot become a formal approved prompt')
        source_root = source.get('project_root') or frozen['inputs'].get('project_root')
        if declared is not None:
            cp.ensure(source_root and declared == Path(source_root).expanduser().resolve(),
                      'Candidate project must match the frozen design project constraints')
        if 'parent_refs' in inputs:
            cp.ensure(inputs['parent_refs'] == source.get('parent_refs', {}), 'Candidate parents differ from actual task')
        if not source_root:
            cp.ensure(not any(key in inputs for key in ('character_id', 'variant_id', 'project_id')),
                      'Standalone text candidate cannot manufacture formal IDs')
        else:
            for field in ('character_id', 'variant_id'):
                if field in inputs:
                    cp.ensure(inputs[field] == frozen['inputs'].get(field, 'base' if field == 'variant_id' else None),
                              'Candidate frozen target differs from actual task')
        items = frozen_inventory(frozen['delivery'], stage, source, frozen.get('resolved_delivery'))
        basis = {'frozen_design': source['sha256'], 'frozen_inputs': source['inputs_sha256'],
                 'parent_refs': source.get('parent_refs', {})}
    else:
        cp.ensure(declared is not None, 'Text prompt needs a frozen design or a real formal project basis')
        state = cp.read_json(declared / 'project.json')
        cp.ensure(state.get('schema_version') == cp.SCHEMA, 'Unsupported project state')
        cp.ensure(not state.get('pending_impact'), 'Resolve upstream impact before text prompt delivery')
        for record in state.get('inputs', {}).values():
            path = (declared / record['path']).resolve()
            cp.ensure(path.is_relative_to(declared) and path.is_file() and cp.digest(path) == record['sha256'],
                      'Project source changed or is missing')
        cp.require_text(inputs, 'character_id')
        character, variant = inputs['character_id'], inputs.get('variant_id', 'base')
        cp.ensure(character in {row['id'] for row in state['roster']}, 'Unknown character ID')
        cp.require_known_variant(state, character, variant)
        cp.ensure(stage in cp.pipeline_stages(state), 'Stage is not available in this project pipeline')
        cp.phased._knowledge = read_only_knowledge
        api = cp._runtime()
        asset_mode = cp.ensemble.mode(api, declared, state, character) if state.get('pipeline_version', 1) >= 2 else 'individual'
        if asset_mode in {'ensemble', 'speaking_extra'}:
            cp.ensure(stage == 'execution', 'Extras have one execution sheet')
            record_key = cp.ensemble.design_key(asset_mode, character, variant)
            record = cp._checked_record(declared, state, record_key)
            basis = {record_key: record['sha256']}
            card = cp.ensemble.resolve(api, declared, state, {'design_basis': {'records': basis}}, character, variant)
        elif cp.phased.enabled(state):
            basis = {key: cp._checked_record(declared, state, key)['sha256']
                     for key in cp.phased.basis_keys(character, variant, stage, state)}
            card = cp.phased.resolve_basis(api, declared, state,
                {'purpose': 'production', 'design_basis': {'records': basis}}, character, variant, stage, force_approved=True)
        else:
            record_key = cp._record_key('design-card', character, variant)
            record = cp._checked_record(declared, state, record_key)
            basis = {record_key: record['sha256']}
            card = cp.read_json(declared / record['path'])
        if asset_mode == 'individual':
            for prior in cp.image_predecessors(state, stage):
                prior_variant = 'base' if state.get('pipeline_version', 1) >= 2 and prior in cp.IDENTITY_STAGES else variant
                cp._checked_image(declared, state, prior, character, prior_variant)
        items = design_inventory(card, stage)
    canvas = resolve_canvas(inputs, stage, design_inputs)
    validate_canvas_text(content, canvas)
    for detail_id, value in items.items():
        check_hard_markers(value, content, detail_id)
    return {'valid': True, 'project_write_performed': False, 'approved': False, 'basis': basis,
            'aspect_ratio': canvas['aspect_ratio'], 'aspect_ratio_source': canvas['source'],
            'verification_scope': 'real-design-basis-and-unambiguous-text-hard-markers',
            'controller_semantic_review_required': True, 'semantic_equivalence_proven_by_code': False,
            'image_review_performed': False}


def validate(package_path, inputs):
    cp.ensure(isinstance(inputs, dict), 'Prompt delivery needs task inputs')
    if 'design_source' in inputs:
        for name in ('request', 'stage'):
            cp.require_text(inputs, name)
        return _frozen_candidate(package_path, inputs)
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
    # Existing formal records keep their original contract when this actual task
    # introduces no new frame constraint; a current explicit constraint is binding.
    canvas = resolve_canvas(inputs, stage, use_default=False)
    if canvas:
        validate_canvas_package(content, canvas)
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
    # This entry point verifies a newly delivered/generation prompt. Ordinary
    # historical approved-record reads retain their original contract.
    cp.validate_new_execution_layout(content, card, asset_mode, inputs)
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
            if 'fidelity_review' in content:
                validate_fidelity(content, design_inventory(card, stage), cp.digest(card))
            else:
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
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--package', type=Path)
    target.add_argument('--text', action='store_true', help='Read {content,inputs} from stdin for an explicit dialogue-only task')
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        checked = validate_text(payload.get('content'), payload.get('inputs')) if args.text else validate(args.package, payload)
        print(json.dumps(checked, ensure_ascii=False))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

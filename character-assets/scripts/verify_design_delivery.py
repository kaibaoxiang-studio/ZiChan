"""Bind a typed design delivery to the real Harness inputs, without project writes.

Validation uses a disposable project/artifact copy. It never submits, approves or
replaces a production record. ``render`` exports every JSON value to design.md;
``validate`` reads the actual task inputs from stdin, not from the design file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import character_project as cp

SCHEMA = 'CharacterDesignDeliveryV1'
STANDALONE = 'StandaloneCharacterDesignV1'
SCOPES = {'direction', 'identity', 'body', 'costume', 'complete'}


def source_bindings(inputs):
    """A request-only biography is valid; file evidence is bound when supplied."""
    cp.require_text(inputs, 'request')
    result = [{'kind': 'request', 'sha256': hashlib.sha256(inputs['request'].encode('utf-8')).hexdigest()}]
    sources = inputs.get('sources', [])
    cp.ensure(isinstance(sources, list), 'sources must be a list of real paths')
    paths = [('source', value) for value in sources]
    paths += [(name, inputs[name]) for name in ('script_context_path', 'direction_brief_path') if inputs.get(name)]
    for kind, value in paths:
        cp.ensure(isinstance(value, str) and value.strip(), 'Source path must be text')
        path = Path(value).expanduser().resolve()
        cp.ensure(path.is_file(), f'Design source does not exist: {path}')
        result.append({'kind': kind, 'path': str(path), 'sha256': cp.digest(path)})
    return result


def render(delivery):
    """Deterministic readable export: no second authored summary can drop detail."""
    cp.ensure(isinstance(delivery, dict), 'Design delivery must be an object')
    labels = {'data': '设计内容', 'payload': '具象设计', 'specialist_execution': '实际专项成果',
              'understanding': '人物理解', 'sources': '实际输入来源', 'subject': '独立设计对象',
              'parent_refs': '上游版本', 'specialist_plan': '专项任务计划'}
    lines = ['# 角色设计交付', '']

    def scalar(value):
        if isinstance(value, str):
            return value.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    def walk(value, depth=0):
        if isinstance(value, dict):
            if not value:
                lines.append('  ' * depth + '- {}')
            for key in sorted(value):
                item = value[key]
                label = labels.get(key, key)
                if isinstance(item, (dict, list)):
                    lines.append('  ' * depth + f'- **{label}**')
                    walk(item, depth + 1)
                else:
                    lines.append('  ' * depth + f'- **{label}**：{scalar(item)}')
        elif isinstance(value, list):
            if not value:
                lines.append('  ' * depth + '- []')
            for index, item in enumerate(value, 1):
                if isinstance(item, (dict, list)):
                    lines.append('  ' * depth + f'- 第 {index} 项')
                    walk(item, depth + 1)
                else:
                    lines.append('  ' * depth + '- ' + scalar(item))
        else:
            lines.append('  ' * depth + '- ' + scalar(value))

    walk(delivery)
    return '\n'.join(lines) + '\n'


def _project_sources(root, state):
    for source in state.get('inputs', {}).values():
        path = (root / source['path']).resolve()
        cp.ensure(path.is_relative_to(root) and path.is_file(), 'Project source is missing or outside project')
        cp.ensure(cp.digest(path) == source['sha256'], 'Project source changed')


def _copy_resource(source_root, target_root, relative):
    """Copy one referenced resource, rejecting traversal and linked inputs."""
    relative = Path(relative)
    cp.ensure(not relative.is_absolute() and '..' not in relative.parts,
              'Design validation resource must be project/artifact-relative')
    source_root = source_root.resolve()
    source = source_root / relative
    cp.ensure(source.resolve().is_relative_to(source_root), 'Design validation resource escapes its root')
    cp.ensure(all(not part.is_symlink() for part in [source, *source.parents] if part != source_root.parent),
              'Design validation resources must not follow symlinks')
    cp.ensure(source.is_file(), f'Design validation resource is missing: {relative}')
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _proposal_resources(data):
    refs = [work['proposal_ref'] for work in data.get('specialist_execution', {}).values()
            if isinstance(work, dict) and work.get('mode') == 'independent' and isinstance(work.get('proposal_ref'), str)]
    if isinstance(data.get('route_ref'), str):
        refs.append(data['route_ref'])
    refs += [work['proposal_ref'] for work in data.get('specialist_coverage', {}).values()
             if isinstance(work, dict) and work.get('status') == 'used' and isinstance(work.get('proposal_ref'), str)]
    return refs


def _minimal_copy(source_root, target_root, state, data, artifact_root):
    """No generated images, archives or unrelated files enter the validator."""
    target_root.mkdir(parents=True, exist_ok=True)
    if state is not None:
        _copy_resource(source_root, target_root, 'project.json')
        for source in state.get('inputs', {}).values():
            _copy_resource(source_root, target_root, source['path'])
        for record in state.get('records', {}).values():
            _copy_resource(source_root, target_root, record['path'])
    # A new independent result stays in artifact_dir until normal project import.
    # Its bound JSON is overlaid only in this throwaway validation tree.
    for relative in _proposal_resources(data):
        origin = artifact_root if (artifact_root / relative).is_file() else source_root
        _copy_resource(origin, target_root, relative)
    # Copy only knowledge snapshots actually referenced by this or parent work.
    documents = [data]
    if state is not None:
        documents += [cp.read_json(target_root / row['path']) for row in state.get('records', {}).values()]
    for document in documents:
        for relative in _proposal_resources(document):
            if not (target_root / relative).is_file():
                _copy_resource(source_root, target_root, relative)
        for work in document.get('specialist_execution', {}).values():
            if not isinstance(work, dict):
                continue
            if work.get('mode') == 'independent':
                relative = work.get('proposal_ref')
                if isinstance(relative, str) and not (target_root / relative).is_file():
                    _copy_resource(source_root, target_root, relative)
                if isinstance(relative, str):
                    refs = cp.read_json(target_root / relative).get('knowledge_refs', [])
                else:
                    refs = []
            else:
                refs = work.get('knowledge_refs', [])
            for ref in refs:
                sha = ref.get('sha256', '') if isinstance(ref, dict) else ''
                if re.fullmatch(r'[0-9a-f]{64}', sha):
                    relative = 'knowledge-snapshots/' + sha
                    if (source_root / relative).is_file():
                        _copy_resource(source_root, target_root, relative)


def _legacy_card(root, state, data, character, variant):
    """Keep the complete-card submission contract without migrating the project."""
    for dependency in ('visual-bible', 'cast-plan'):
        cp._checked_record(root, state, dependency)
    cp._validate_record('design-card', data, state, character, variant)
    record_key = cp._record_key('design-card', character, variant)
    prior = state.get('records', {}).get(record_key)
    unchanged = bool(prior and prior.get('approval') and not prior.get('stale') and
                     prior.get('sha256') == cp.digest(data))
    if unchanged:
        cp._checked_record(root, state, record_key)
        return
    human = data.get('morphology') in {'human', 'humanoid'}
    if human:
        row = next(row for row in state['roster'] if row['id'] == character)
        if row.get('tier') in cp.HEAVY_TIERS or row.get('priority') == 'deep':
            schema = 'CharacterDesignCardV2.4' if state.get('pipeline_version', 1) >= 2 else 'CharacterDesignCardV2.2'
            cp.ensure(data.get('schema_version') == schema,
                      f'Submitted lead/important human design cards require {schema}; existing approvals remain readable')
        if data.get('schema_version') in {'CharacterDesignCardV2.2', 'CharacterDesignCardV2.4'}:
            cp.validate_body_proportion_anchors(data)
            cp.validate_design_handoffs(data, root)


def _standalone_payload(data, artifact_root):
    scope = data['scope']
    cp.ensure(data.get('execution_contract_version') == 2, 'Standalone design needs execution_contract_version:2')
    payload = data.get('payload')
    cp.ensure(isinstance(payload, dict), 'Standalone design needs a concrete payload')
    cp.ensure(payload.get('morphology') in {'human', 'humanoid', 'nonhuman'}, 'Standalone needs explicit morphology')
    cp.ensure(set(payload) <= cp.phased.COMMON_PAYLOAD | cp.phased.SCOPE_PAYLOAD[scope] | {'visual_details'},
              'Standalone payload changes another scope')
    details = payload.get('visual_details')
    cp.ensure(isinstance(details, dict), 'Standalone needs visual_details')
    allowed = cp.phased.OWNERS[scope] | ({'adornments'} if scope != 'body' else set())
    cp.ensure(set(details) <= allowed, 'Standalone visual fields belong to another scope')
    human = payload['morphology'] in {'human', 'humanoid'}
    if human:
        for domain in cp.phased.OWNERS[scope]:
            cp.ensure(isinstance(details.get(domain), dict), f'Standalone needs visual_details.{domain}')
            for field in cp.DETAIL_FIELDS[domain]:
                cp.require_text(details[domain], field)
                cp.ensure(len(details[domain][field].strip()) >= 8, f'Concrete design missing: {domain}.{field}')
        if scope in {'identity', 'costume'}:
            owned = 'head_neck' if scope == 'identity' else 'body_hands'
            cp.ensure(set(details.get('adornments', {})) == {owned}, 'Standalone adornment ownership mismatch')
            cp.require_text(details['adornments'], owned)
        if scope == 'identity':
            cp.validate_world_and_face(payload, allow_proposals=True)
            cp.validate_feature_focus(payload)
            cp.ensure(isinstance(payload.get('identity_invariants'), list) and payload['identity_invariants'],
                      'Standalone identity needs stable identity_invariants')
        elif scope == 'body':
            cp.validate_body_form(payload)
            cp.validate_body_proportion_anchors(payload)
        else:
            cp.ensure(isinstance(payload.get('costume'), dict) and payload['costume'], 'Standalone costume needs costume summary')
    else:
        form = payload.get('morphology_details')
        cp.ensure(isinstance(form, dict) and set(form) == {scope} and form[scope],
                  'Nonhuman standalone needs current-scope morphology_details')
    cp.require_list(data, 'deferred_dimensions')
    cp.require_list(data, 'unresolved')
    # The local key is only a temporary proposal target, never a formal asset ID.
    stage = {**data, 'character_id': data['subject']['local_key'], 'variant_id': 'base'}
    cp.phased.validate_execution(cp._runtime(), artifact_root, stage, state=None, strict=True)
    if human and scope == 'identity':
        cp.phased.validate_prompt_detail_contract(cp._runtime(), stage, root=artifact_root, state=None, strict=True)
    elif payload.get('prompt_detail_contract'):
        cp.phased.validate_prompt_detail_contract(cp._runtime(), stage, root=artifact_root, state=None, strict=True)


def validate(design_path, inputs, markdown_path=None):
    cp.ensure(isinstance(inputs, dict), 'Design delivery needs the actual task inputs')
    cp.require_text(inputs, 'request')
    scope = inputs.get('scope')
    if scope is None:
        scope = 'identity'
        if inputs.get('project_root'):
            metadata = Path(inputs['project_root']).expanduser().resolve() / 'project.json'
            if metadata.is_file():
                state = cp.read_json(metadata)
                if state.get('schema_version') == cp.SCHEMA and not cp.phased.enabled(state):
                    scope = 'complete'
    cp.ensure(scope in SCOPES, 'Unsupported requested design scope')
    design_path = Path(design_path).resolve()
    delivery = cp.read_json(design_path)
    cp.ensure(isinstance(delivery, dict) and set(delivery) == {'schema_version', 'kind', 'scope', 'data'},
              'Design delivery needs schema_version, kind, scope and data only')
    cp.ensure(delivery['schema_version'] == SCHEMA, f'Expected {SCHEMA}')
    cp.ensure(delivery['scope'] == scope, 'Design delivery scope differs from actual task scope')
    data = delivery['data']
    cp.ensure(isinstance(data, dict), 'Design delivery data must be an object')
    markdown_path = Path(markdown_path) if markdown_path else design_path.with_name('design.md')
    cp.ensure(markdown_path.is_file() and not markdown_path.is_symlink(), 'Design delivery needs design.md')
    cp.ensure(markdown_path.read_bytes() == render(delivery).encode('utf-8'),
              'design.md must be the exact deterministic export of design-result.json')
    with tempfile.TemporaryDirectory(prefix='character-design-validation-') as folder:
        sandbox = Path(folder)
        if inputs.get('project_root'):
            root = Path(inputs['project_root']).expanduser().resolve()
            cp.ensure((root / 'project.json').is_file(), 'Design delivery needs a real character project')
            state = cp.read_json(root / 'project.json')
            cp.ensure(state.get('schema_version') == cp.SCHEMA, 'Unsupported project state')
            cp.ensure(not state.get('pending_impact'), 'Resolve upstream impact before design delivery')
            _project_sources(root, state)
            cp.require_text(inputs, 'character_id')
            character, variant = inputs['character_id'], inputs.get('variant_id', 'base')
            cp.ensure(character in {row['id'] for row in state['roster']}, 'Unknown character ID in actual task')
            cp.require_known_variant(state, character, variant)
            working = sandbox / 'project'
            _minimal_copy(root, working, state, data, design_path.parent)
            if not cp.phased.enabled(state):
                cp.ensure(scope == 'complete', 'Legacy complete projects only accept scope complete; do not auto-migrate')
                cp.ensure(delivery['kind'] == 'legacy_card', 'Complete task needs kind legacy_card')
                _legacy_card(working, state, data, character, variant)
            elif scope == 'direction':
                cp.ensure(delivery['kind'] == 'direction', 'Direction task needs kind direction')
                cp.ensure(variant == 'base', 'Direction belongs to base')
                cp.phased.validate_brief(cp._runtime(), working, state, data, character)
            else:
                cp.ensure(scope != 'complete', 'Scope complete belongs only to legacy complete projects')
                cp.ensure(delivery['kind'] == 'stage', 'Stage task cannot be satisfied by a direction draft')
                cp.ensure(data.get('schema_version') == 'CharacterStageDesignV1.2', 'New stage delivery needs CharacterStageDesignV1.2')
                cp.ensure(data.get('execution_contract_version') == 2, 'Stage delivery needs execution_contract_version:2')
                cp.phased.validate_stage(cp._runtime(), working, state, data, character, variant, scope, strict=True)
        else:
            cp.ensure(scope in {'identity', 'body', 'costume'}, 'Standalone needs a concrete identity/body/costume scope')
            cp.ensure(delivery['kind'] == 'standalone', 'A project-free design needs kind standalone')
            cp.ensure(not inputs.get('character_id') and not inputs.get('variant_id'), 'Standalone task cannot assert a formal asset ID or variant')
            cp.ensure(data.get('schema_version') == STANDALONE and data.get('scope') == scope, 'Standalone schema or scope mismatch')
            cp.ensure(not any(key in data for key in ('character_id', 'variant_id', 'parent_refs', 'project_id')),
                      'Standalone design cannot manufacture formal IDs, project or approved parents')
            subject = data.get('subject')
            cp.ensure(isinstance(subject, dict), 'Standalone needs a named local subject')
            cp.require_text(subject, 'name')
            cp.require_text(subject, 'local_key')
            cp.ensure(not re.match(r'^CHR-', subject['local_key'], re.I), 'Standalone local key must not impersonate a formal character ID')
            cp.ensure(data.get('sources') == source_bindings(inputs), 'Standalone sources must match the actual task request and source hashes')
            cp.ensure(isinstance(data.get('understanding'), dict), 'Standalone needs character understanding')
            for field in cp.phased.UNDERSTANDING_FIELDS:
                cp.require_text(data['understanding'], field)
            cp.require_text(data, 'design_thesis')
            working = sandbox / 'artifacts'
            _minimal_copy(design_path.parent, working, None, data, design_path.parent)
            _standalone_payload(data, working)
    return {'valid': True, 'kind': delivery['kind'], 'scope': scope, 'design_sha256': cp.digest(delivery),
            'project_write_performed': False, 'approved': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('render', help='Export design.md mechanically; does not approve or validate design')
    export.add_argument('--design', required=True, type=Path)
    export.add_argument('--output', type=Path)
    check = commands.add_parser('validate', help='Validate using actual task inputs JSON from stdin')
    check.add_argument('--design', required=True, type=Path)
    check.add_argument('--markdown', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'render':
            output = args.output or args.design.with_name('design.md')
            output.write_bytes(render(cp.read_json(args.design)).encode('utf-8'))
            print(json.dumps({'path': str(output), 'sha256': cp.digest(output)}, ensure_ascii=False))
        else:
            print(json.dumps(validate(args.design, json.load(sys.stdin), args.markdown), ensure_ascii=False))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()

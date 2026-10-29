#!/usr/bin/env python3
"""Save one current prompt document and its mechanical provenance sidecar.

This is a candidate-text store, not a design or image approval interface.
It checks real inputs, bytes, scope and prompt layout. Generated pictures go to
the user by default; image review runs only on explicit request. No legacy
production ledger is written.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

UPDATE_SCHEMA = 'CharacterPromptDocumentUpdateV1'
SCHEMA = 'CharacterPromptDocumentV1'
STAGES = ('avatar', 'expression', 'full_body', 'execution')
LABELS = {'avatar': '基础头像', 'expression': '九宫格表情',
          'full_body': '全身模卡', 'execution': '状态服饰执行'}
FORBIDDEN = {'approved', 'approval', 'anchor_images', 'anchors', 'design_basis',
             'design_card_sha256', 'image_approval', 'image_approved', 'operator',
             'adoption_status', 'approval_status'}
LIMITATIONS = ['Structure, provenance and layout checks do not prove design depth, '
               'semantic continuity, image quality or user approval.']


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def _bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def _hash(value):
    raw = value if isinstance(value, bytes) else json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _text(value, label):
    ensure(isinstance(value, str) and value.strip(), f'{label} must be nonblank text')
    ensure('\x00' not in value, f'{label} contains a NUL byte')
    return value


def _id(value, label):
    _text(value, label)
    ensure(re.fullmatch(r'[\w.-]{1,100}', value), f'Unsafe {label}')
    return value


def _reject_approval(value):
    if isinstance(value, dict):
        ensure(not (set(value) & FORBIDDEN), 'Update cannot declare approval, adopted status or anchors')
        for child in value.values():
            _reject_approval(child)
    elif isinstance(value, list):
        for child in value:
            _reject_approval(child)


def _locations(document):
    document = Path(document).expanduser().absolute()
    ensure(not document.is_symlink(), 'Document must not be a symlink')
    document = document.resolve()
    ensure(document.suffix.lower() in {'.md', '.markdown'}, 'Document must be a Markdown file')
    side = document.parent / f'.{document.stem}.character-assets'
    ensure(not side.is_symlink(), 'Sidecar directory must not be a symlink')
    return document, side, side / 'current.json', side / '提示词.txt'


def _document_binding(document, inputs):
    if inputs.get('document_path'):
        selected = Path(_text(inputs['document_path'], 'Actual document_path')).expanduser()
        ensure(selected.is_absolute() and selected.resolve() == document,
               'Document differs from the absolute actual task document_path')


def _safe_target(path):
    ensure(not path.is_symlink(), f'Output must not be a symlink: {path}')
    ensure(not path.exists() or path.is_file(), f'Output must be a regular file: {path}')


def _atomic_write(path, content):
    _safe_target(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('wb', prefix='.prompt-tmp-', dir=path.parent, delete=False) as stream:
        tmp = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


@contextlib.contextmanager
def _locked(side, create=False):
    if create:
        side.mkdir(parents=True, exist_ok=True)
    ensure(side.is_dir() and not side.is_symlink(), 'Prompt sidecar directory is missing or unsafe')
    lock_path = side / '.lock'
    _safe_target(lock_path)
    with lock_path.open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b'\0')
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _transaction_target(label, document, side):
    fixed = {'document': document, 'metadata': side / 'current.json', 'text': side / '提示词.txt'}
    if label in fixed:
        return fixed[label]
    ensure(re.fullmatch(r'history/[0-9a-f]{64}\.json', label or ''), 'Unsafe transaction target')
    ensure(not (side / 'history').is_symlink(), 'History directory must not be a symlink')
    return side / label


def _recover(document, side):
    journal_path = side / 'transaction.json'
    if not journal_path.exists():
        return
    _safe_target(journal_path)
    journal = _read(journal_path)
    ensure(journal.get('schema_version') == 'PromptDocumentTransactionV1' and
           journal.get('document') == str(document), 'Invalid prompt transaction journal')
    targets = journal.get('targets')
    ensure(isinstance(targets, list) and targets, 'Empty prompt transaction journal')
    ensure(len({row.get('target') for row in targets}) == len(targets), 'Duplicate transaction targets')
    ready = []
    for row in targets:
        path = _transaction_target(row['target'], document, side)
        _safe_target(path)
        raw = base64.b64decode(row['content'], validate=True)
        ensure(_hash(raw) == row['sha256'], 'Transaction payload changed')
        actual = _hash(path.read_bytes()) if path.exists() else None
        ensure(actual in {row['before_sha256'], row['sha256']},
               'Transaction recovery refuses externally edited files')
        ready.append((path, raw))
    # All old/new states have been checked before any recovery mutation.
    for path, raw in ready:
        if not path.exists() or path.read_bytes() != raw:
            _atomic_write(path, raw)
    journal_path.unlink()


def _commit(document, side, payloads):
    rows = []
    for label, raw in payloads:
        path = _transaction_target(label, document, side)
        _safe_target(path)
        if label.startswith('history/') and path.exists():
            ensure(path.read_bytes() == raw, 'Existing history snapshot was edited; refusing overwrite')
        rows.append({'target': label, 'before_sha256': _hash(path.read_bytes()) if path.exists() else None,
                     'sha256': _hash(raw), 'content': base64.b64encode(raw).decode('ascii')})
    journal = {'schema_version': 'PromptDocumentTransactionV1', 'document': str(document), 'targets': rows}
    _atomic_write(side / 'transaction.json', _bytes(journal))
    _recover(document, side)


def _file_receipt(value, kind='source'):
    ensure(isinstance(value, str), 'sources must contain actual path strings')
    path = Path(_text(value, 'source path')).expanduser().resolve()
    ensure(path.is_file(), f'Actual {kind} file does not exist: {path}')
    return {'kind': kind, 'path': str(path), 'sha256': _hash(path.read_bytes())}


def _inside(root, value):
    ensure(isinstance(value, str), 'Project path must be text')
    path = (root / value).resolve()
    ensure(path.is_relative_to(root) and path.is_file(), 'Project record path is missing or escapes project')
    return path


def _project_context(inputs):
    root_value, character = inputs.get('project_root'), inputs.get('character_id')
    if not root_value:
        ensure(not character and not inputs.get('parent_refs'), 'Formal character IDs/parents need a real project_root')
        return None
    root = Path(root_value).expanduser().resolve()
    ensure((root / 'project.json').is_file(), 'project_root is not a real character project; cannot downgrade')
    import character_project as cp
    state = _read(root / 'project.json')
    ensure(state.get('schema_version') == cp.SCHEMA, 'Unsupported character project schema')
    _text(character, 'project character_id')
    item = next((r for r in state.get('roster', []) if r.get('id') == character), None)
    ensure(item, 'Unknown project character_id')
    sources = []
    for value in state.get('inputs', {}).values():
        path = _inside(root, value.get('path'))
        ensure(_hash(path.read_bytes()) == value.get('sha256'), 'Project input source changed')
        sources.append({'kind': 'project_source', 'path': str(path), 'sha256': value['sha256']})
    records = {}
    morphology = None
    for key, value in state.get('records', {}).items():
        relevant = key in {'script-context', 'visual-bible', 'cast-plan'} or character in key.split(':')
        if not relevant or value.get('stale') or not value.get('approval'):
            continue
        _inside(root, value.get('path'))
        cp._checked_record(root, state, key)  # Existing contract, read-only; no re-authoring or approval.
        records[key] = {'path': str(root / value['path']), 'sha256': value['sha256'],
                        'approval': copy.deepcopy(value['approval'])}
        if key.startswith(('stage-design:identity:', 'design-card:')):
            data = _read(root / value['path'])
            known = data.get('payload', data).get('morphology')
            if known:
                ensure(morphology is None or morphology == known, 'Approved project morphology conflict')
                morphology = known
    parents = inputs.get('parent_refs', {})
    ensure(isinstance(parents, dict), 'parent_refs must map real project record keys to SHA')
    for key, sha in parents.items():
        ensure(key in records and records[key]['sha256'] == sha, 'Read-only parent missing, stale or changed')
    images = []
    for image in state.get('images', []):
        if image.get('character_id') != character or image.get('stale') or not image.get('approval'):
            continue
        _inside(root, image.get('path'))
        cp._checked_image(root, state, image['stage'], character, image['variant_id'])
        images.append({'path': str(root / image['path']), 'sha256': image['sha256'],
                       'stage': image['stage'], 'state_id': image['variant_id'],
                       'approval': copy.deepcopy(image['approval'])})
    return {'root': str(root), 'character_id': character, 'name': item.get('name'),
            'state_ids': [r['id'] for r in item.get('states', [])] or ['base'],
            'sources': sources, 'records': records, 'images': images,
            'morphology': morphology, 'asset_mode': cp.ensemble.mode(cp._runtime(), root, state, character),
            'pending_impact': copy.deepcopy(state.get('pending_impact'))}


def _actual_inputs(inputs):
    ensure(isinstance(inputs, dict), 'Actual task inputs must be an object')
    _text(inputs.get('request'), 'Actual task request')
    ensure(inputs.get('delivery_contract') != 'legacy_typed' and inputs.get('purpose') not in {'formal', 'production'}
           and not inputs.get('formal') and not inputs.get('design_source') and not inputs.get('base_designs')
           and inputs.get('scope') not in {'identity', 'body', 'costume', 'direction', 'complete'},
           'Formal/legacy typed task must use its original delivery contract')
    ensure(inputs.get('delivery_mode', 'files') == 'files', 'Prompt document requires actual files delivery')
    sources = inputs.get('sources', [])
    ensure(isinstance(sources, list), 'sources must be a list of actual file paths')
    bound = [_file_receipt(path) for path in sources]
    for name in ('script_context_path', 'direction_brief_path'):
        if inputs.get(name):
            bound.append(_file_receipt(inputs[name], name))
    project = _project_context(inputs)
    if project:
        bound += project['sources']
    stages = inputs.get('target_stages', [inputs['stage']] if inputs.get('stage') else [])
    ensure(isinstance(stages, list) and all(s in STAGES for s in stages), 'Invalid target_stages')
    states = inputs.get('state_ids', [inputs['variant_id']] if inputs.get('variant_id') else [])
    ensure(isinstance(states, list), 'state_ids must be a list')
    for value in states:
        _id(value, 'state_id')
        ensure(not project or value in project['state_ids'] or value == 'base', 'Unknown project state_id')
    morphology = inputs.get('morphology', (project or {}).get('morphology') or 'human')
    mode = inputs.get('asset_mode', (project or {}).get('asset_mode', 'individual'))
    ensure(morphology in {'human', 'humanoid', 'nonhuman'}, 'Invalid morphology')
    ensure(mode in {'individual', 'ensemble', 'speaking_extra'}, 'Invalid asset_mode')
    if project:
        ensure(not project['morphology'] or morphology == project['morphology'], 'Actual morphology contradicts approved project identity')
        ensure(mode == project['asset_mode'], 'Actual asset_mode contradicts the real project character')
    return {'sha256': _hash(inputs), 'sources': bound, 'project': project,
            'stages': stages, 'states': states, 'morphology': morphology, 'asset_mode': mode}


def _references(values, inputs, project=None):
    ensure(isinstance(values, list), 'references must be a list')
    actual = inputs.get('references', inputs.get('reference_images', []))
    ensure(isinstance(actual, list), 'Actual references must be a list')
    # Actual task references are mechanically retained even when the model only
    # writes prompt text. An unspecified role is honestly marked, not invented.
    requested_paths = {str(Path(r.get('path', '')).expanduser().resolve()) for r in values if isinstance(r, dict)}
    inherited = []
    for reference in actual:
        path = reference if isinstance(reference, str) else reference.get('path') if isinstance(reference, dict) else None
        _text(path, 'Actual reference path')
        if str(Path(path).expanduser().resolve()) not in requested_paths:
            inherited.append({'path': path, 'role': reference.get('role') or '用户提供参考，具体职责未声明'
                              if isinstance(reference, dict) else '用户提供参考，具体职责未声明'})
    values = inherited + values
    bound_paths = {str(Path(r if isinstance(r, str) else r.get('path', '')).expanduser().resolve()) for r in actual}
    bound_paths |= {str(Path(p).expanduser().resolve()) for p in inputs.get('sources', [])}
    bound_paths |= {row['path'] for row in (project or {}).get('images', [])}
    result = []
    for ref in values:
        ensure(isinstance(ref, dict) and set(ref) == {'path', 'role'}, 'Reference needs only actual path and role')
        _text(ref['role'], 'Reference role')
        receipt = _file_receipt(ref['path'], 'reference')
        ensure(receipt['path'] in bound_paths or ref['path'] in inputs['request'],
               'Reference is not bound to actual task inputs')
        supplied = next((r for r in actual if isinstance(r, dict) and
                         str(Path(r.get('path', '')).expanduser().resolve()) == receipt['path']), None)
        if supplied and supplied.get('role'):
            ensure(supplied['role'] == ref['role'], 'Reference role contradicts actual task inputs')
        if supplied and supplied.get('sha256'):
            ensure(supplied['sha256'] == receipt['sha256'], 'Reference differs from actual task reference SHA')
        result.append({**receipt, 'role': ref['role']})
    return result


def _constraints(values, inputs, sources):
    ensure(isinstance(values, list), 'constraints must be a list')
    result = []
    for value in values:
        ensure(isinstance(value, dict) and set(value) == {'text', 'source_ref'}, 'Constraint needs text/source_ref')
        _text(value['text'], 'Constraint text')
        ref = _text(value['source_ref'], 'Constraint source_ref')
        if ref == 'request':
            ensure(value['text'] in inputs['request'], 'Request constraint is not in the actual request')
        else:
            # macOS /var and /private/var (and explicit relative paths) may
            # name the same actual input. Canonicalise only the path portion.
            parts = re.match(r'^(.*?)(:L\d.*|#.*)$', ref)
            base, suffix = (parts.group(1), parts.group(2)) if parts else (ref, '')
            ref = str(Path(base).expanduser().resolve()) + suffix
            ensure(any(ref == s['path'] or ref.startswith(s['path'] + '#') or
                       ref.startswith(s['path'] + ':L') for s in sources), 'Constraint source_ref is not an actual source')
        result.append({'text': value['text'], 'source_ref': ref})
    return result


def _merge(previous, fresh, key):
    merged = {key(row): copy.deepcopy(row) for row in previous}
    for row in fresh:
        merged[key(row)] = copy.deepcopy(row)
    return [merged[k] for k in sorted(merged)]


def _entry(value, inputs, actual):
    ensure(isinstance(value, dict) and set(value) <= {'stage', 'state_id', 'text', 'aspect_ratio'},
           'Entry contains unsupported fields; do not declare approval or typed design')
    stage = value.get('stage')
    ensure(stage in STAGES, 'Unknown prompt stage')
    state = _id(value.get('state_id', 'base'), 'state_id')
    ensure(stage == 'execution' or state == 'base', 'Identity prompt stages belong to base')
    _text(value.get('text'), 'Complete prompt text')
    from prompt_canvas import resolve_canvas, canonical_ratio
    ratio = canonical_ratio(value['aspect_ratio']) if value.get('aspect_ratio') else resolve_canvas(inputs, stage)['aspect_ratio']
    result = {'stage': stage, 'state_id': state, 'text': value['text'], 'aspect_ratio': ratio}
    _layout(result, inputs, actual)
    return result


def _layout(entry, inputs, actual):
    from prompt_layout import validate_entry
    errors = validate_entry(entry, inputs, morphology=actual['morphology'], asset_mode=actual['asset_mode'])
    ensure(isinstance(errors, list), 'prompt_layout.validate_entry must return a list of errors')
    ensure(not errors, 'Prompt layout: ' + '; '.join(errors))


def _required(entries, actual):
    keys = {(e['stage'], e['state_id']) for e in entries}
    for stage in actual['stages']:
        wanted = actual['states'] if stage == 'execution' and actual['states'] else ['base']
        ensure(all((stage, state) in keys for state in wanted), 'Required target stage/state is missing')
    if actual['project']:
        ensure(all(e['state_id'] in actual['project']['state_ids'] or e['state_id'] == 'base' for e in entries),
               'Document contains an unknown project state')


def _render(state):
    lines = [f"# {state['subject']['name']}｜角色提示词", '', '当前为候选文字；不构成正式图片批准。', '']
    for entry in state['entries']:
        label = LABELS[entry['stage']]
        suffix = f"｜{entry['state_id']}" if entry['stage'] == 'execution' else ''
        lines += [f"## {label}{suffix}", '', entry['text'], '']
    return '\n'.join(lines).encode('utf-8'), ('\n\n'.join(e['text'] for e in state['entries']) + '\n').encode('utf-8')


def _revision(state):
    return _hash({k: v for k, v in state.items() if k not in {'revision', 'document_sha256', 'text_sha256', 'last_operation', 'task_sha256'}})


def _check_files(document, side):
    metadata, text = side / 'current.json', side / '提示词.txt'
    for path in (document, metadata, text):
        _safe_target(path)
        ensure(path.is_file(), f'Current document/sidecar is missing: {path}')
    state = _read(metadata)
    ensure(state.get('schema_version') == SCHEMA and state.get('status') == 'candidate', 'Invalid current prompt record')
    ensure(state.get('revision') == _revision(state), 'Current metadata revision drift')
    md, txt = _render(state)
    ensure(document.read_bytes() == md and state.get('document_sha256') == _hash(md), 'Document editing drift; use an expected-revision update')
    ensure(text.read_bytes() == txt and state.get('text_sha256') == _hash(txt), 'Prompt TXT editing drift')
    for receipt in state.get('sources', []) + state.get('references', []):
        path = Path(receipt['path'])
        ensure(path.is_file() and _hash(path.read_bytes()) == receipt['sha256'], 'Bound source/reference file changed or disappeared')
    old_project = state.get('project')
    if old_project:
        current = _project_context({'project_root': old_project['root'], 'character_id': old_project['character_id']})
        ensure(current == old_project, 'Read-only project basis changed; do not silently reuse old approval')
    return state


def _result(document, side, state, changed=False):
    return {'document_path': str(document), 'metadata_path': str(side / 'current.json'),
            'text_path': str(side / '提示词.txt'), 'revision': state['revision'], 'changed': changed,
            'artifacts': [str(document), str(side / 'current.json'), str(side / '提示词.txt')],
            'approved': False, 'project_ledger_write_performed': False,
            'checked': ['actual_inputs', 'source_and_reference_bytes', 'same_source_text', 'stage_state_layout', 'revision'],
            'limitations': LIMITATIONS}


def save_document(update, inputs, document_path):
    """Merge requested prompt entries; save all derived files in one recoverable transaction."""
    actual = _actual_inputs(inputs)
    ensure(isinstance(update, dict), 'Update must be an object')
    _reject_approval(update)
    allowed = {'schema_version', 'subject', 'entries', 'expected_revision', 'references', 'constraints', 'morphology', 'asset_mode'}
    ensure(set(update) <= allowed and update.get('schema_version') == UPDATE_SCHEMA, 'Invalid prompt update schema/fields')
    subject = update.get('subject')
    ensure(isinstance(subject, dict) and set(subject) == {'name', 'local_key'}, 'Subject needs name/local_key only')
    _text(subject['name'], 'Subject name')
    _id(subject['local_key'], 'Subject local_key')
    if inputs.get('subject'):
        ensure(subject == inputs['subject'], 'Subject differs from actual task inputs')
    if actual['project']:
        ensure(subject['name'] == actual['project']['name'], 'Subject differs from the actual project character')
    for field in ('morphology', 'asset_mode'):
        ensure(field not in update or update[field] == actual[field], f'Update cannot change actual task {field}')
    values = update.get('entries')
    ensure(isinstance(values, list) and values, 'Update needs complete prompt entries')
    fresh = [_entry(value, inputs, actual) for value in values]
    ensure(len({(e['stage'], e['state_id']) for e in fresh}) == len(fresh), 'Only one integrated direction per stage/state')
    ensure(not actual['stages'] or all(e['stage'] in actual['stages'] for e in fresh), 'Update stage differs from actual task targets')
    ensure(not actual['states'] or all(e['stage'] != 'execution' or e['state_id'] in actual['states'] for e in fresh),
           'Update state differs from actual task targets')
    references = _references(update.get('references', []), inputs, actual['project'])
    constraints = _constraints(update.get('constraints', []), inputs, actual['sources'])
    document, side, metadata, _ = _locations(document_path)
    _document_binding(document, inputs)
    if inputs.get('expected_revision'):
        ensure(update.get('expected_revision') == inputs['expected_revision'], 'Update differs from actual task expected_revision')
    if actual['project']:
        ensure(not document.is_relative_to(Path(actual['project']['root'])), 'Read-only legacy project cannot contain new delivery writes')
    fingerprint = _hash({'update': update, 'inputs': inputs})
    with _locked(side, create=True):
        _recover(document, side)
        previous = _check_files(document, side) if metadata.exists() else None
        ensure(previous is not None or not document.exists(), 'Existing document has no managed sidecar; refusing overwrite')
        if previous:
            ensure(subject == previous['subject'], 'Cannot change the current document subject')
            if update.get('expected_revision') != previous['revision']:
                ensure(previous.get('last_operation') == fingerprint and previous['task_sha256'] == actual['sha256'],
                       'expected_revision is required and must match the current revision')
                return _result(document, side, previous)
        else:
            ensure(not update.get('expected_revision'), 'expected_revision supplied for a new document')
        state = {'schema_version': SCHEMA, 'status': 'candidate', 'subject': copy.deepcopy(subject),
                 'morphology': actual['morphology'], 'asset_mode': actual['asset_mode'],
                 'entries': _merge(previous['entries'] if previous else [], fresh, lambda r: (STAGES.index(r['stage']), r['state_id'])),
                 'sources': _merge(previous['sources'] if previous else [], actual['sources'], lambda r: r['path']),
                 'references': _merge(previous['references'] if previous else [], references, lambda r: (r['path'], r['role'])),
                 'constraints': _merge(previous['constraints'] if previous else [], constraints, lambda r: (r['text'], r['source_ref'])),
                 'project': actual['project'], 'task_sha256': actual['sha256']}
        ensure(not previous or (previous['morphology'], previous['asset_mode'], previous['project']) ==
               (state['morphology'], state['asset_mode'], state['project']), 'Document identity/project context cannot be silently replaced')
        _required(state['entries'], actual)
        state['revision'] = _revision(state)
        if previous and previous['revision'] == state['revision']:
            # A reworded request with identical design/resources is not a new
            # design revision. Bind the current task without copying documents
            # or inventing a change-history snapshot.
            if previous['task_sha256'] != actual['sha256']:
                previous.update(task_sha256=actual['sha256'], last_operation=fingerprint)
                _atomic_write(metadata, _bytes(previous))
            return _result(document, side, previous)
        md, txt = _render(state)
        state.update(document_sha256=_hash(md), text_sha256=_hash(txt), last_operation=fingerprint)
        payloads = []
        if previous:
            payloads.append((f"history/{previous['revision']}.json", _bytes(previous)))
        payloads += [('document', md), ('text', txt), ('metadata', _bytes(state))]
        # Recheck live resources immediately before recording transaction intent.
        # This is one local call, not a second model or semantic design pass.
        ensure(_actual_inputs(inputs) == actual, 'Actual inputs/project changed during save')
        for receipt in state['sources'] + state['references']:
            ensure(Path(receipt['path']).is_file() and _hash(Path(receipt['path']).read_bytes()) == receipt['sha256'],
                   'Actual source/reference changed during save')
        _commit(document, side, payloads)
        return _result(document, side, state, changed=True)


def validate_document(document_path, inputs):
    """Validate the actual saved document against the actual current task inputs."""
    actual = _actual_inputs(inputs)
    document, side, _, _ = _locations(document_path)
    _document_binding(document, inputs)
    with _locked(side):
        _recover(document, side)
        state = _check_files(document, side)
        ensure(state['task_sha256'] == actual['sha256'], 'Document is not bound to these actual task inputs')
        ensure(state['project'] == actual['project'] and state['morphology'] == actual['morphology'] and
               state['asset_mode'] == actual['asset_mode'], 'Actual project/morphology/asset_mode differs')
        _required(state['entries'], actual)
        for entry in state['entries']:
            # Current task framing only governs its requested targets; inherited
            # entries keep their own stored framing until explicitly revised.
            targeted = not actual['stages'] or (entry['stage'] in actual['stages'] and
                       (entry['stage'] != 'execution' or not actual['states'] or entry['state_id'] in actual['states']))
            layout_inputs = inputs if targeted else {'request': 'Validate preserved current prompt', 'aspect_ratio': entry['aspect_ratio']}
            _layout(entry, layout_inputs, actual)
        return _result(document, side, state)


def context_document(document_path, project_root=None, character_id=None):
    document, side, _, _ = _locations(document_path)
    if not document.exists() and not (side / 'current.json').exists() and not (side / 'transaction.json').exists():
        project = _project_context({'project_root': project_root, 'character_id': character_id})
        return {'document_path': str(document), 'revision': None, 'entries': [], 'artifacts': [],
                'approved': False, 'project_ledger_write_performed': False, 'project_context': project,
                'legacy_records': {key: _read(row['path']) for key, row in project['records'].items()} if project else {},
                'limitations': LIMITATIONS}
    with _locked(side):
        _recover(document, side)
        state = _check_files(document, side)
        result = _result(document, side, state)
        result.update(subject=state['subject'], entries=state['entries'], sources=state['sources'],
                      references=state['references'], constraints=state['constraints'])
        project = state.get('project')
        if project_root or character_id:
            selected = _project_context({'project_root': project_root, 'character_id': character_id})
            ensure(not project or selected == project, 'Context project differs from current document')
            project = selected
        result['project_context'] = project
        if project:
            result['legacy_records'] = {key: _read(row['path']) for key, row in project['records'].items()}
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    save = commands.add_parser('save')
    save.add_argument('--update', required=True, type=Path)
    save.add_argument('--inputs', required=True, type=Path)
    save.add_argument('--document', required=True, type=Path)
    validate = commands.add_parser('validate')
    validate.add_argument('--document', required=True, type=Path)
    validate.add_argument('--inputs', type=Path, help='Actual inputs JSON; defaults to stdin')
    context = commands.add_parser('context')
    context.add_argument('--document', required=True, type=Path)
    context.add_argument('--project-root')
    context.add_argument('--character-id')
    args = parser.parse_args()
    try:
        if args.command == 'save':
            result = save_document(_read(args.update), _read(args.inputs), args.document)
        elif args.command == 'validate':
            result = validate_document(args.document, _read(args.inputs) if args.inputs else json.load(sys.stdin))
        else:
            result = context_document(args.document, args.project_root, args.character_id)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError, ImportError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

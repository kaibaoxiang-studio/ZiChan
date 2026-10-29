"""Task-bound completion checks; content quality remains a design judgement."""
from pathlib import Path
import json
import re


def completion_mode(capability, inputs, output):
    inputs = inputs or {}
    mode = inputs.get('delivery_mode', 'files')
    if mode not in {'files', 'text', 'discussion'}:
        raise ValueError('Unsupported requested delivery_mode')
    if output.get('delivery_mode', mode) != mode:
        raise ValueError('Delivery mode differs from the actual task; do not downgrade the task')
    if inputs.get('project_root'):
        root = Path(inputs['project_root']).expanduser().resolve()
        metadata = root / 'project.json'
        if not metadata.is_file():
            raise ValueError('The actual project_root needs a real character project; no standalone fallback')
        state = json.loads(metadata.read_text(encoding='utf-8'))
        if state.get('schema_version') != 'CharacterProjectV1':
            raise ValueError('Unsupported project state')
    if mode == 'discussion':
        # Discussion is a task chosen by the caller, never an agent's escape
        # from a requested design or usable prompt.
        if inputs.get('task_kind', 'discussion') != 'discussion':
            raise ValueError('A design/prompt task cannot complete as discussion')
        if capability.get('id') == 'character-image-prompt':
            raise ValueError('Prompt delivery cannot downgrade to discussion')
    return mode


def verify_text(output):
    content = output.get('content')
    if not isinstance(content, str) or not content.strip():
        raise ValueError('Text completion needs the actual complete content, not only a summary or path')
    if re.fullmatch(r'[\s。.!！]*(?:done|completed|success|已完成|完成|已分析|已生成|已交付)[\s。.!！]*',
                    content, re.I):
        raise ValueError('A completion acknowledgement is not the requested content')
    if output.get('artifact_path'):
        raise ValueError('Text completion must carry content, not a fictitious artifact_path')


def verify_main_file(output, declared, artifact_dir):
    relative = output.get('artifact_path')
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError('File completion needs an actual main artifact_path')
    if relative not in declared:
        raise ValueError('Main artifact_path must be declared in artifacts')
    path = Path(artifact_dir) / relative
    if path.stat().st_size == 0:
        raise ValueError('Main artifact is empty; file existence is not content delivery')
    if path.suffix.lower() in {'.md', '.markdown', '.txt', '.json', '.csv', '.tsv', '.html', '.yaml', '.yml'}:
        if not path.read_text(encoding='utf-8').strip():
            raise ValueError('Main text artifact is blank; file existence is not content delivery')

"""Task-bound completion checks; content quality remains a design judgement."""
from pathlib import Path
import json
import re
import subprocess
import sys


PROMPT_DOCUMENT_CAPABILITIES = {'character-assets', 'character-design', 'character-image-prompt'}


def legacy_delivery_required(inputs):
    """Route from the actual task, never from an agent's preferred output file."""
    inputs = inputs or {}
    return (inputs.get('purpose') == 'formal'
            or inputs.get('delivery_contract') == 'legacy_typed'
            or inputs.get('scope') in {'identity', 'body', 'costume', 'direction', 'complete'}
            or inputs.get('stage') == 'costume_design' or 'costume_design' in inputs.get('target_stages', [])
            or bool(inputs.get('design_source')) or bool(inputs.get('base_designs')))


def prompt_document_allowed(capability, inputs):
    if capability.get('id') not in PROMPT_DOCUMENT_CAPABILITIES:
        return False
    if not isinstance(inputs, dict) or not inputs.get('request'):
        return False
    if (inputs or {}).get('delivery_contract') == 'prompt_document' and legacy_delivery_required(inputs):
        raise ValueError('Actual formal/typed task cannot downgrade to prompt_document')
    return not legacy_delivery_required(inputs)


def verify_prompt_document(path, inputs, plugin_root):
    """Use the real document validator, including source and sidecar checks."""
    helper = Path(plugin_root) / 'scripts/prompt_document.py'
    checked = subprocess.run([sys.executable, str(helper), 'validate', '--document', str(path)],
                             input=json.dumps(inputs, ensure_ascii=False), capture_output=True,
                             text=True, encoding='utf-8', timeout=30)
    if checked.returncode:
        raise ValueError('Prompt document contract failed: ' + (checked.stderr or checked.stdout).strip())
    try:
        validated = json.loads(checked.stdout)
    except (ValueError, TypeError) as exc:
        raise ValueError('Prompt document validator did not return its actual artifact paths') from exc
    if not isinstance(validated, dict) or not isinstance(validated.get('artifacts'), list):
        raise ValueError('Prompt document validator needs document/metadata/text artifact paths')
    expected = {str(Path(path).resolve()), str(Path(validated.get('metadata_path', '')).resolve()),
                str(Path(validated.get('text_path', '')).resolve())}
    actual = {str(Path(item).resolve()) for item in validated['artifacts'] if isinstance(item, str)}
    if len(expected) != 3 or not expected.issubset(actual):
        raise ValueError('Prompt document validator omitted required derived artifacts')
    return validated


def verify_prompt_text(content, inputs, plugin_root):
    """Fileless ordinary prompts still carry real presentation instructions."""
    stages = inputs.get('target_stages') or ([inputs['stage']] if inputs.get('stage') else [])
    if not stages:
        raise ValueError('Prompt text needs actual stage/target_stages')
    if len(stages) == 1:
        entries = [{'stage': stages[0], 'text': content}]
    else:
        aliases = {'avatar': 'avatar', '头像': 'avatar', 'expression': 'expression', '表情': 'expression',
                   'full_body': 'full_body', '模卡': 'full_body', '全身': 'full_body',
                   'execution': 'execution', '执行': 'execution'}
        headings = list(re.finditer(r'^#{1,6}\s*(avatar|头像|expression|表情|full_body|模卡|全身|execution|执行)\b[^\n]*\n', content, re.M))
        entries = [{'stage': aliases[m.group(1)], 'text': content[m.end():headings[i + 1].start() if i + 1 < len(headings) else len(content)]}
                   for i, m in enumerate(headings)]
        if set(stages) != {e['stage'] for e in entries}:
            raise ValueError('Multi-stage text needs complete, separately labelled stage prompts')
    helper = Path(plugin_root) / 'scripts/prompt_layout.py'
    # Import in an isolated interpreter bound to this exact plugin snapshot.
    code = ('import json,sys;sys.path.insert(0,sys.argv[1]);'
            'from prompt_layout import validate_entry;v=json.load(sys.stdin);'
            'e=[x for p in v["entries"] for x in validate_entry(p,v["inputs"],'
            'v["inputs"].get("morphology","human"),v["inputs"].get("asset_mode","individual"))];'
            'print(json.dumps(e,ensure_ascii=False));sys.exit(bool(e))')
    checked = subprocess.run([sys.executable, '-c', code, str(helper.parent)],
                             input=json.dumps({'entries': entries, 'inputs': inputs}, ensure_ascii=False),
                             capture_output=True, text=True, encoding='utf-8', timeout=30)
    if checked.returncode:
        raise ValueError('Prompt text layout failed: ' + (checked.stderr or checked.stdout).strip())


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

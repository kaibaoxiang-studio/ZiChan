#!/usr/bin/env python3
"""Validate/package a skill-only plugin. --check never writes files.

Build replaces only the two named generated ZIPs in this project's dist/.
No network, configuration changes, skill edits, or runtime generation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.git', '.DS_Store', '__pycache__'}


def inventory(root):
    files = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in IGNORED for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f'Symlink is not portable: {relative}')
        if path.is_file():
            files[relative.as_posix()] = path.read_bytes()
    return files


def validate(root):
    files = inventory(root / 'scene-assets')
    manifests = [json.loads(files[name]) for name in
                 ('plugin.json', '.codex-plugin/plugin.json')]
    for manifest in manifests:
        if manifest['name'] != 'scene-assets' or manifest['version'] != '0.1.0':
            raise ValueError('Plugin identity/version must be scene-assets / 0.1.0')
    codex = manifests[1]
    if codex.get('skills') != './skills/':
        raise ValueError('Codex skill root must be ./skills/')
    for interface in (codex['interface'],
                      manifests[0]['extensions']['com.openai']['interface']):
        if '$sence-prompts' not in interface.get('defaultPrompt', ''):
            raise ValueError('Missing direct sence-prompts invocation')
    entry = files['skills/sence-prompts/SKILL.md'].decode('utf-8')
    frontmatter = entry.split('---', 2)[1]
    if not re.search(r'^name: sence-prompts$', frontmatter, re.M):
        raise ValueError('Skill name differs from sence-prompts')
    if not re.search(r'^  version: "0\.1\.0"$', frontmatter, re.M):
        raise ValueError('Skill version differs from 0.1.0')
    if not files.get('skills/sence-prompts/agents/openai.yaml'):
        raise ValueError('Missing skill UI metadata')
    if [key for key in files if key.startswith('skills/') and key.endswith('/SKILL.md')] != ['skills/sence-prompts/SKILL.md']:
        raise ValueError('Unexpected additional skills')
    market = json.loads((root / '.agents/plugins/marketplace.json').read_text())
    if market['name'] != 'scene-assets-local' or len(market['plugins']) != 1:
        raise ValueError('Unexpected marketplace identity or plugin count')
    listing = market['plugins'][0]
    if listing['name'] != codex['name'] or listing['source'] != {'source': 'local', 'path': './scene-assets'}:
        raise ValueError('Marketplace must resolve the bundled plugin')
    return files, market


def zip_entries(files, marketplace):
    direct = {'scene-assets/' + name: data for name, data in files.items()}
    prefix = 'scene-assets-local-marketplace/'
    local = {prefix + 'plugins/scene-assets/' + name: data for name, data in files.items()}
    market = json.loads(json.dumps(marketplace))
    market['plugins'][0]['source']['path'] = './plugins/scene-assets'
    local[prefix + '.agents/plugins/marketplace.json'] = (json.dumps(market, ensure_ascii=False, indent=2) + '\n').encode()
    return {'scene-assets-0.1.0.zip': direct, 'scene-assets-local-marketplace.zip': local}


def write_zip(path, entries):
    # Stage beside output, then atomically replace only the named generated ZIP.
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.zip', delete=False) as temp:
        staged = Path(temp.name)
    try:
        with zipfile.ZipFile(staged, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(entries.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        verify_zip(staged, entries)
        staged.replace(path)
    finally:
        if staged.exists():
            staged.unlink()


def verify_zip(path, expected):
    with zipfile.ZipFile(path) as archive:
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != set(expected):
            raise ValueError(f'ZIP inventory mismatch: {path.name}')
        for name, data in expected.items():
            if archive.read(name) != data:
                raise ValueError(f'ZIP content mismatch: {name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files, market = validate(ROOT)
    expected = zip_entries(files, market)
    if not args.check:
        (ROOT / 'dist').mkdir(exist_ok=True)
        for name, entries in expected.items():
            write_zip(ROOT / 'dist' / name, entries)
    for name, entries in expected.items():
        target = ROOT / 'dist' / name
        if not target.exists():
            raise ValueError(f'Missing release ZIP: run python3 -B scene-plugin-maintenance/package_plugin.py ({name})')
        verify_zip(target, entries)
        print(f'ZIP OK {name}: {len(entries)} files; SHA256 {hashlib.sha256(target.read_bytes()).hexdigest()}')
    print(f'PLUGIN OK scene-assets 0.1.0; {len(files)} files; skill sence-prompts')


if __name__ == '__main__':
    main()

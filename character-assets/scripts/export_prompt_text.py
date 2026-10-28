"""Export human-readable UTF-8 text mechanically from a prompt package."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def render_prompt_text(package):
    if not isinstance(package, dict) or package.get('schema_version') != 'CharacterPromptPackageV1':
        raise ValueError('Expected CharacterPromptPackageV1')
    prompts = package.get('prompts')
    if not isinstance(prompts, list) or not prompts:
        raise ValueError('Prompt package needs prompts[].text')
    bodies = []
    for prompt in prompts:
        if not isinstance(prompt, dict) or not isinstance(prompt.get('text'), str) or not prompt['text'].strip():
            raise ValueError('Each prompt needs nonempty text')
        bodies.append(prompt['text'])
    return '\n\n'.join(bodies) + '\n'


def write_prompt_text(package, output):
    output = Path(output)
    data = render_prompt_text(package).encode('utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return {'path': str(output.resolve()), 'sha256': hashlib.sha256(data).hexdigest(),
            'source': 'prompts[].text', 'encoding': 'utf-8'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or args.package.parent / '提示词.txt'
    if output.resolve() == args.package.resolve():
        parser.error('Text output must differ from JSON input')
    package = json.loads(args.package.read_text(encoding='utf-8-sig'))
    print(json.dumps(write_prompt_text(package, output), ensure_ascii=False))


if __name__ == '__main__':
    main()

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'runtime'))
import phased_design
from harness_core.engine import verify_result
from prompt_fixture import make_avatar_project, write_delivery, envelope


class CP:
    @staticmethod
    def ensure(condition, message):
        if not condition:
            raise ValueError(message)

    @staticmethod
    def require_text(item, key):
        CP.ensure(isinstance(item.get(key), str) and item[key].strip(), key)

    @staticmethod
    def read_json(path):
        return json.loads(Path(path).read_text())

    @staticmethod
    def _checked_record(root, state, key):
        return state['records'][key]


class PromptContractTest(unittest.TestCase):
    def avatar_design(self):
        items = []
        for kind in sorted(phased_design.PROMPT_DETAIL_REQUIRED['avatar']):
            fields = phased_design.PROMPT_DETAIL_FIELDS[kind]
            items.append({'id': kind, 'kind': kind, 'source_refs': ['script:bio'],
                          'cues': {field: f'{kind}的{field}具体可画视觉特征' for field in fields}})
        return {'scope': 'identity', 'payload': {'prompt_detail_contract': {
            'schema_version': 'PromptDetailContractV1', 'stage': 'avatar',
            'complexity': 'ordinary', 'items': items}}}

    def test_design_requires_every_avatar_dimension(self):
        design = self.avatar_design()
        phased_design.validate_prompt_detail_contract(CP, design, strict=False)
        design['payload']['prompt_detail_contract']['items'].pop()
        with self.assertRaisesRegex(ValueError, 'Missing required avatar'):
            phased_design.validate_prompt_detail_contract(CP, design, strict=False)

    def test_prompt_cannot_drop_approved_cue(self):
        design = self.avatar_design()
        design['schema_version'] = 'CharacterStageDesignV1.2'
        contract = design['payload']['prompt_detail_contract']
        cues = [value for item in contract['items'] for value in item['cues'].values()]
        package = {'purpose': 'final', 'prompts': [{'id': 'p1', 'text': '。'.join(cues)}],
                   'acceptance_checks': [next(iter(item['cues'].values())) for item in contract['items']]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'identity.json').write_text(json.dumps(design, ensure_ascii=False))
            state = {'records': {'stage-design:identity:CHR:base': {'path': 'identity.json'}}}
            phased_design.validate_prompt_detail_coverage(CP, root, state, package, 'CHR', 'base', 'avatar')
            package['prompts'][0]['text'] = package['prompts'][0]['text'].replace(cues[0], '')
            with self.assertRaisesRegex(ValueError, 'dropped'):
                phased_design.validate_prompt_detail_coverage(CP, root, state, package, 'CHR', 'base', 'avatar')

    def test_harness_rejects_markdown_only_delivery(self):
        catalog = json.loads((ROOT / 'capabilities.json').read_text())
        cap = next(item for item in catalog['capabilities'] if item['id'] == 'character-image-prompt')
        result = {'status': 'succeeded', 'result': {'status': 'done', 'artifact_path': 'design.md',
                  'summary': 'draft', 'questions': []}, 'artifacts': ['design.md'],
                  'questions': [], 'error': None}
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'design.md').write_text('苏老太，写实，古装。')
            with self.assertRaisesRegex(ValueError, 'Required artifact'):
                verify_result(result, cap, folder)

    def test_harness_accepts_structured_delivery(self):
        catalog = json.loads((ROOT / 'capabilities.json').read_text())
        cap = next(item for item in catalog['capabilities'] if item['id'] == 'character-image-prompt')
        with tempfile.TemporaryDirectory() as folder:
            _, package, inputs = make_avatar_project(Path(folder) / 'project')
            delivery = Path(folder) / 'delivery'
            write_delivery(delivery, package)
            self.assertEqual(len(verify_result(envelope(), cap, delivery, inputs, ROOT)), 2)

    def test_featured_execution_requires_focus_component(self):
        items = []
        for kind in sorted(phased_design.PROMPT_DETAIL_REQUIRED['execution']):
            fields = phased_design.PROMPT_DETAIL_FIELDS[kind]
            items.append({'id': kind, 'kind': kind, 'source_refs': ['script:scene'],
                          'cues': {field: f'{kind}的{field}具体可画视觉特征' for field in fields}})
        requirements = {name: {'decision': 'inherit'} for name in
                        ('makeup', 'head_ear_neck', 'wearable_accessories')}
        design = {'scope': 'costume', 'payload': {'prompt_detail_contract': {
            'schema_version': 'PromptDetailContractV1', 'stage': 'execution',
            'complexity': 'featured', 'items': items},
            'costume_direction': {'scene_needs': {'requirements': requirements}}}}
        with self.assertRaisesRegex(ValueError, 'focus_component'):
            phased_design.validate_prompt_detail_contract(CP, design, strict=False)


if __name__ == '__main__':
    unittest.main()

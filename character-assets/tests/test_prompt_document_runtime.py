"""Real document validation through the runtime, without model connections."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'runtime'), str(ROOT / 'scripts')]
from harness_core.engine import Executor, input_files, verify_result
from harness_core.delivery import legacy_delivery_required
from prompt_document import save_document
from test_prompt_layout import AVATAR


class PromptDocumentRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.capabilities = {c['id']: c for c in json.loads((ROOT / 'capabilities.json').read_text())['capabilities']}
        self.inputs = {'request': '林澄是图书修复师，设计并交头像提示词', 'target_stages': ['avatar']}
        self.update = {'schema_version': 'CharacterPromptDocumentUpdateV1',
                       'subject': {'name': '林澄', 'local_key': 'lin-cheng'},
                       'entries': [{'stage': 'avatar', 'state_id': 'base', 'text': AVATAR}]}
        self.document = self.folder / '角色提示词.md'

    def envelope(self, path='角色提示词.md'):
        return {'status': 'succeeded', 'result': {'status': 'done', 'artifact_path': path,
                'summary': '当前完整推荐提示词', 'questions': []}, 'artifacts': [path], 'questions': [], 'error': None}

    def test_three_entry_points_accept_actual_md_and_register_derived_files(self):
        saved = save_document(self.update, self.inputs, self.document)
        for name in ('character-assets', 'character-design', 'character-image-prompt'):
            with self.subTest(name=name):
                artifacts = verify_result(self.envelope(), self.capabilities[name], self.folder, self.inputs, ROOT)
                self.assertEqual({x['path'] for x in artifacts}, set(saved['artifacts']))

    def test_markdown_without_sidecar_cannot_claim_document_completion(self):
        self.document.write_text(AVATAR, encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Prompt document contract'):
            verify_result(self.envelope(), self.capabilities['character-design'], self.folder, self.inputs, ROOT)

    def test_formal_typed_actual_inputs_cannot_escape_by_returning_md(self):
        save_document(self.update, self.inputs, self.document)
        for extra in ({'purpose': 'formal'}, {'scope': 'identity'}, {'design_source': {'kind': 'task_text_design'}},
                      {'delivery_contract': 'legacy_typed'}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                verify_result(self.envelope(), self.capabilities['character-design'], self.folder, {**self.inputs, **extra}, ROOT)
        with self.assertRaisesRegex(ValueError, 'cannot downgrade'):
            verify_result(self.envelope(), self.capabilities['character-design'], self.folder,
                          {**self.inputs, 'delivery_contract': 'prompt_document', 'purpose': 'formal'}, ROOT)
        self.assertFalse(legacy_delivery_required({'parent_refs': {'stage-design:identity:CHR:base': '0' * 64}}))
        self.assertFalse(legacy_delivery_required({'scope': 'requested'}))

    def test_bound_absolute_document_is_allowed_random_absolute_output_is_not(self):
        inputs = {**self.inputs, 'document_path': str(self.document)}
        save_document(self.update, inputs, self.document)
        output = self.envelope(str(self.document))
        self.assertEqual(len(verify_result(output, self.capabilities['character-assets'], self.folder, inputs, ROOT)), 3)
        with self.assertRaisesRegex(ValueError, 'inputs.document_path'):
            verify_result(output, self.capabilities['character-assets'], self.folder, self.inputs, ROOT)
        with self.assertRaisesRegex(ValueError, 'inputs.document_path'):
            verify_result(output, self.capabilities['character-assets'], self.folder,
                          {**self.inputs, 'document_path': str(self.folder / 'other.md')}, ROOT)

    def test_document_is_mutable_output_sources_remain_hashed(self):
        self.document.write_text('current output', encoding='utf-8')
        source = self.folder / 'bio.txt'
        source.write_text('真实输入小传', encoding='utf-8')
        self.assertEqual(set(input_files({'document_path': str(self.document), 'sources': [str(source)]})), {str(source.resolve())})

    def test_executor_writes_actual_task_inputs_before_agent_and_exposes_path(self):
        observed = {}
        def run(skill, task, *args, **kwargs):
            observed.update(task)
            return self.envelope(), None
        executor = Executor(ROOT)
        executor.client = SimpleNamespace(run=run)
        task = {'artifact_dir': str(self.folder / 'attempt'), 'inputs': self.inputs}
        executor(self.capabilities['character-design'], task, {}, threading.Event(), None, None)
        path = Path(observed['inputs_path'])
        self.assertEqual(json.loads(path.read_text()), self.inputs)
        self.assertNotIn('inputs_path', observed['inputs'])

    def test_fileless_new_prompt_does_not_need_typed_design_source(self):
        output = self.envelope('')
        output.update(artifacts=[])
        output['result'].update(content=AVATAR, delivery_mode='text')
        inputs = {**self.inputs, 'stage': 'avatar', 'delivery_mode': 'text'}
        self.assertEqual(verify_result(output, self.capabilities['character-image-prompt'], self.folder, inputs, ROOT), [])
        output['result']['content'] = '画幅3:4。气质温和的修复师，完成。'
        with self.assertRaisesRegex(ValueError, 'layout'):
            verify_result(output, self.capabilities['character-image-prompt'], self.folder, inputs, ROOT)


if __name__ == '__main__':
    unittest.main()

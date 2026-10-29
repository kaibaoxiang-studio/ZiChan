"""Prompt-first storage regressions; fixtures test mechanics, not design quality."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
import prompt_document as store

AVATAR = ('画幅3:4竖版。林澄完整头部和双肩入画，穿白色运动背心。'
          '圆角下颌，右侧分缝，发尾停在颌角，浅棕瞳孔。')
BODY = ('画幅9:16竖版。林澄从头顶到双脚及双手完整入画，白色运动背心、黑色短裤、赤脚。'
        '全高为7.3个头高，肩峰宽与骨盆宽之比1.25:1；上段从颈根到胯点、'
        '下段从胯点到脚底，两段比例1:1.3。')
EXECUTION = ('画幅9:16竖版，精确2×2四格，上区约占总高1/3，下区约占总高2/3。'
             '左上正面头像头肩，右上45度侧脸头肩；左下正面衣装放大图，头部彻底出画。'
             '范围从颈肩以下到鞋底，完整肩部、双臂、双手、躯干、双腿和双鞋均入画；'
             '右下从头顶到鞋底的完整背面。'
             '同一位林澄，栗棕短发、浅棕瞳孔。灰绿夹克右前片压左前片，三枚暗铜扣，'
             '黑色长裤、圆头平底黑鞋，前后接缝连续，浅灰背景。')


def update(text=AVATAR, stage='avatar', state='base', revision=None):
    result = {'schema_version': store.UPDATE_SCHEMA,
              'subject': {'name': '林澄', 'local_key': 'local-lin'},
              'entries': [{'stage': stage, 'state_id': state, 'text': text}]}
    if revision is not None:
        result['expected_revision'] = revision
    return result


def inventory(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*')
            if p.is_file() and p.name != '.lock'}


class PromptDocumentTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.doc = self.root / '林澄当前提示词.md'
        self.source = self.root / '人物原文.txt'
        self.source.write_text('林澄是修书人，原文未写发色和瞳色。', encoding='utf-8')
        self.inputs = {'request': '制作林澄的基础头像提示词，单一推荐方向。',
                       'sources': [str(self.source)], 'target_stages': ['avatar']}

    def save(self, value=None, inputs=None):
        return store.save_document(value or update(), inputs or self.inputs, self.doc)

    def test_save_same_source_and_replay_without_extra_history(self):
        result = self.save()
        self.assertTrue(result['changed'])
        self.assertFalse(result['approved'])
        self.assertEqual(len(result['artifacts']), 3)
        metadata = json.loads(Path(result['metadata_path']).read_text())
        self.assertEqual(metadata['entries'][0]['text'], AVATAR)
        self.assertIn(AVATAR, self.doc.read_text())
        self.assertEqual(Path(result['text_path']).read_text(), AVATAR + '\n')
        before = inventory(self.root)
        replay = self.save()
        self.assertFalse(replay['changed'])
        self.assertEqual(inventory(self.root), before)
        self.assertFalse((Path(result['metadata_path']).parent / 'history').exists())
        self.assertEqual(store.validate_document(self.doc, self.inputs)['revision'], result['revision'])

    def test_partial_update_preserves_previous_words_and_creates_one_snapshot(self):
        first = self.save()
        inputs = {**self.inputs, 'request': '只补林澄身体模卡，原头像逐字保留。', 'target_stages': ['full_body']}
        second = self.save(update(BODY, 'full_body', revision=first['revision']), inputs)
        data = json.loads(Path(second['metadata_path']).read_text())
        self.assertEqual(data['entries'][0]['text'], AVATAR)
        self.assertEqual(data['entries'][1]['text'], BODY)
        self.assertEqual(len(list(Path(second['metadata_path']).parent.glob('history/*.json'))), 1)
        self.assertEqual(store.validate_document(self.doc, inputs)['revision'], second['revision'])
        before = inventory(self.root)
        self.assertFalse(self.save(update(BODY, 'full_body', revision=second['revision']), inputs)['changed'])
        self.assertEqual(before, inventory(self.root))

    def test_reworded_request_without_design_change_does_not_copy_a_revision(self):
        first = self.save()
        md, txt = self.doc.read_bytes(), Path(first['text_path']).read_bytes()
        inputs = {**self.inputs, 'request': '沿用当前林澄头像，内容无需改动。'}
        result = self.save(update(revision=first['revision']), inputs)
        self.assertFalse(result['changed'])
        self.assertEqual(result['revision'], first['revision'])
        self.assertEqual(self.doc.read_bytes(), md)
        self.assertEqual(Path(result['text_path']).read_bytes(), txt)
        self.assertFalse((Path(result['metadata_path']).parent / 'history').exists())
        self.assertEqual(store.validate_document(self.doc, inputs)['revision'], first['revision'])

    def test_multiple_execution_states_merge_without_erasing_other_state(self):
        inputs = {**self.inputs, 'target_stages': ['execution'], 'state_ids': ['S01']}
        first = self.save(update(EXECUTION, 'execution', 'S01'), inputs)
        next_inputs = {**inputs, 'state_ids': ['S02'], 'request': '补S02服装提示词，保留S01。'}
        second = self.save(update(EXECUTION.replace('灰绿夹克', '深蓝夹克'), 'execution', 'S02', first['revision']), next_inputs)
        state = json.loads(Path(second['metadata_path']).read_text())
        self.assertEqual([r['state_id'] for r in state['entries']], ['S01', 'S02'])
        store.validate_document(self.doc, next_inputs)

    def test_existing_document_requires_revision_and_rejects_stale_writer(self):
        first = self.save()
        before = inventory(self.root)
        with self.assertRaisesRegex(ValueError, 'expected_revision'):
            self.save(update(AVATAR.replace('浅棕', '深棕')))
        self.assertEqual(before, inventory(self.root))
        second = self.save(update(AVATAR.replace('浅棕', '深棕'), revision=first['revision']))
        before = inventory(self.root)
        with self.assertRaisesRegex(ValueError, 'expected_revision'):
            self.save(update(AVATAR.replace('浅棕', '琥珀'), revision=first['revision']))
        self.assertEqual(before, inventory(self.root))
        self.assertNotEqual(first['revision'], second['revision'])

    def test_document_txt_and_metadata_drift_rejected_without_overwrite(self):
        for target in ('document', 'text', 'metadata'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder:
                doc = Path(folder) / 'current.md'
                result = store.save_document(update(), self.inputs, doc)
                path = {'document': doc, 'text': Path(result['text_path']), 'metadata': Path(result['metadata_path'])}[target]
                if target == 'metadata':
                    data = json.loads(path.read_text())
                    data['entries'][0]['text'] += '外部插入'
                    path.write_text(json.dumps(data, ensure_ascii=False))
                else:
                    path.write_bytes(path.read_bytes() + b'\nexternal edit')
                before = inventory(Path(folder))
                with self.assertRaisesRegex(ValueError, 'drift'):
                    store.validate_document(doc, self.inputs)
                with self.assertRaisesRegex(ValueError, 'drift'):
                    store.save_document(update(revision=result['revision']), self.inputs, doc)
                self.assertEqual(inventory(Path(folder)), before)

    def test_actual_task_input_mismatch_and_source_drift_rejected(self):
        self.save()
        with self.assertRaisesRegex(ValueError, 'actual task inputs'):
            store.validate_document(self.doc, {**self.inputs, 'request': '这是另一项任务'})
        self.source.write_text('原文已改变', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'source/reference'):
            store.validate_document(self.doc, self.inputs)

    def test_reference_requires_actual_file_role_and_task_binding(self):
        image = self.root / '真实参考.png'
        image.write_bytes(b'actual reference bytes; visual validity is not asserted')
        value = update()
        value['references'] = [{'path': str(image), 'role': '仅衣料配色，不替换身份'}]
        with self.assertRaisesRegex(ValueError, 'actual task'):
            self.save(value)
        inputs = {**self.inputs, 'references': value['references']}
        result = self.save(value, inputs)
        metadata = json.loads(Path(result['metadata_path']).read_text())
        self.assertEqual(metadata['references'][0]['sha256'], hashlib.sha256(image.read_bytes()).hexdigest())
        image.write_bytes(b'changed reference')
        with self.assertRaisesRegex(ValueError, 'source/reference'):
            store.validate_document(self.doc, inputs)

    def test_actual_references_are_automatic_and_their_declared_hash_is_checked(self):
        image = self.root / 'reference.png'
        image.write_bytes(b'actual reference bytes')
        inputs = {**self.inputs, 'references': [{'path': str(image), 'role': '只借配色'}]}
        result = self.save(inputs=inputs)
        row = json.loads(Path(result['metadata_path']).read_text())['references'][0]
        self.assertEqual(row['role'], '只借配色')
        with self.assertRaisesRegex(ValueError, 'reference SHA'):
            self.save(inputs={**inputs, 'references': [{'path': str(image), 'role': '只借配色', 'sha256': '0' * 64}]})

    def test_constraints_only_bind_actual_sources_and_request(self):
        value = update()
        value['constraints'] = [{'text': '林澄是修书人', 'source_ref': str(self.source) + ':L1'}]
        self.save(value)
        value['constraints'] = [{'text': '虚构已批准设定', 'source_ref': 'request'}]
        with self.assertRaisesRegex(ValueError, 'actual request'):
            self.save(value)
        value['constraints'] = [{'text': '随意断言', 'source_ref': '/made-up/source.txt:L1'}]
        with self.assertRaisesRegex(ValueError, 'actual source'):
            self.save(value)

    def test_false_approval_duplicate_direction_and_scope_downgrade_rejected(self):
        for field in ('approval', 'approved', 'anchor_images', 'adoption_status'):
            value = update()
            value['entries'][0][field] = True
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'approval'):
                self.save(value)
        value = update()
        value['entries'] *= 2
        with self.assertRaisesRegex(ValueError, 'one integrated direction'):
            self.save(value)
        with self.assertRaisesRegex(ValueError, 'target'):
            self.save(inputs={**self.inputs, 'target_stages': ['full_body']})
        for extra in ({'purpose': 'formal'}, {'delivery_contract': 'legacy_typed'}, {'scope': 'body'}, {'design_source': {'kind': 'frozen'}}):
            with self.subTest(extra=extra), self.assertRaisesRegex(ValueError, 'original delivery'):
                self.save(inputs={**self.inputs, **extra})

    def test_actual_subject_morphology_and_document_path_cannot_be_spoofed(self):
        with self.assertRaisesRegex(ValueError, 'Subject'):
            self.save(inputs={**self.inputs, 'subject': {'name': '别人', 'local_key': 'other'}})
        value = update()
        value['morphology'] = 'nonhuman'
        with self.assertRaisesRegex(ValueError, 'morphology'):
            self.save(value)
        with self.assertRaisesRegex(ValueError, 'document_path'):
            self.save(inputs={**self.inputs, 'document_path': str(self.root / 'other.md')})
        actual = {**self.inputs, 'document_path': str(self.doc)}
        self.save(inputs=actual)
        store.validate_document(self.doc, actual)

    def test_layout_is_not_bypassed_by_valid_metadata(self):
        with self.assertRaisesRegex(ValueError, 'layout'):
            self.save(update('画幅3:4竖版。衣装执行图。', 'avatar'))

    def test_atomic_interruption_rolls_forward_and_context_recovers(self):
        original = store._atomic_write
        failed = False

        def interrupt(path, content):
            nonlocal failed
            if path.name == '提示词.txt' and not failed:
                failed = True
                raise OSError('simulated interrupted save')
            return original(path, content)

        with patch.object(store, '_atomic_write', side_effect=interrupt):
            with self.assertRaisesRegex(OSError, 'interrupted'):
                self.save()
        side = store._locations(self.doc)[1]
        self.assertTrue((side / 'transaction.json').exists())
        result = store.validate_document(self.doc, self.inputs)
        self.assertFalse((side / 'transaction.json').exists())
        self.assertEqual(Path(result['text_path']).read_text(), AVATAR + '\n')

    def test_context_before_first_save_is_read_only_and_has_no_fake_artifacts(self):
        before = inventory(self.root)
        result = store.context_document(self.doc)
        self.assertIsNone(result['revision'])
        self.assertEqual(result['artifacts'], [])
        self.assertEqual(before, inventory(self.root))
        self.assertFalse(store._locations(self.doc)[1].exists())

    def test_recovery_does_not_clobber_external_edit_after_interruption(self):
        original = store._atomic_write

        def interrupt(path, content):
            if path.name == '提示词.txt':
                raise OSError('simulated interruption')
            return original(path, content)

        with patch.object(store, '_atomic_write', side_effect=interrupt):
            with self.assertRaises(OSError):
                self.save()
        self.doc.write_text('external intervention', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'externally edited'):
            store.validate_document(self.doc, self.inputs)
        self.assertEqual(self.doc.read_text(), 'external intervention')

    def test_cli_save_validate_stdin_context_and_serialized_concurrent_writers(self):
        task = self.root / 'inputs.json'
        task.write_text(json.dumps(self.inputs, ensure_ascii=False), encoding='utf-8')
        value = self.root / 'update.json'
        value.write_text(json.dumps(update(), ensure_ascii=False), encoding='utf-8')
        cli = [sys.executable, str(ROOT / 'scripts/prompt_document.py')]
        result = subprocess.run(cli + ['save', '--update', str(value), '--inputs', str(task), '--document', str(self.doc)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        first = json.loads(result.stdout)
        validate = subprocess.run(cli + ['validate', '--document', str(self.doc)], input=json.dumps(self.inputs),
                                  capture_output=True, text=True)
        self.assertEqual(validate.returncode, 0, validate.stderr)
        context = subprocess.run(cli + ['context', '--document', str(self.doc)], capture_output=True, text=True)
        self.assertEqual(json.loads(context.stdout)['revision'], first['revision'])
        workers = []
        for index, colour in enumerate(('深棕', '琥珀')):
            file = self.root / f'update-{index}.json'
            file.write_text(json.dumps(update(AVATAR.replace('浅棕', colour), revision=first['revision']), ensure_ascii=False))
            workers.append(subprocess.Popen(cli + ['save', '--update', str(file), '--inputs', str(task), '--document', str(self.doc)],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        outputs = [worker.communicate(timeout=20) for worker in workers]
        self.assertEqual(sorted(worker.returncode for worker in workers), [0, 1], outputs)
        store.validate_document(self.doc, self.inputs)

    def test_missing_project_formal_identity_and_unmanaged_document_refused(self):
        with self.assertRaisesRegex(ValueError, 'real character project'):
            self.save(inputs={**self.inputs, 'project_root': str(self.root / 'missing'), 'character_id': 'CHR-001'})
        with self.assertRaisesRegex(ValueError, 'real project_root'):
            self.save(inputs={**self.inputs, 'character_id': 'CHR-001'})
        self.doc.write_text('user-authored unmanaged document', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'no managed sidecar'):
            self.save()
        self.assertEqual(self.doc.read_text(), 'user-authored unmanaged document')

    def test_old_approved_project_reused_read_only_and_parent_hash_checked(self):
        from prompt_fixture import make_avatar_project, cp
        project = self.root / 'legacy-project'
        state, _, _ = make_avatar_project(project)
        subject = {'name': state['roster'][0]['name'], 'local_key': 'legacy-current'}
        value = update()
        value['subject'] = subject
        parent_key = 'stage-design:identity:CHR-TEST:base'
        inputs = {**self.inputs, 'project_root': str(project), 'character_id': 'CHR-TEST',
                  'parent_refs': {parent_key: state['records'][parent_key]['sha256']}}
        before = inventory(project)
        self.save(value, inputs)
        store.validate_document(self.doc, inputs)
        self.assertEqual(before, inventory(project))
        with self.assertRaisesRegex(ValueError, 'parent'):
            self.save(value, {**inputs, 'parent_refs': {parent_key: '0' * 64}})
        with self.assertRaisesRegex(ValueError, 'morphology contradicts'):
            self.save(value, {**inputs, 'morphology': 'nonhuman'})
        with self.assertRaisesRegex(ValueError, 'Read-only legacy'):
            store.save_document(value, inputs, project / 'new-current.md')
        self.assertEqual(before, inventory(project))
        record_path = project / state['records'][parent_key]['path']
        record = cp.read_json(record_path)
        record['unresolved'] = ['externally changed']
        cp.write_json(record_path, record)
        with self.assertRaisesRegex(ValueError, 'contents changed'):
            store.validate_document(self.doc, inputs)


if __name__ == '__main__':
    unittest.main()

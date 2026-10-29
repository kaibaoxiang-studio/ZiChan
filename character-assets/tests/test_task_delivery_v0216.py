"""Deterministic journey regressions; fixtures are not model design evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'runtime'), str(ROOT / 'scripts')]
from harness_core.engine import verify_result
from prompt_fixture import cp, make_avatar_project
import verify_design_delivery as design


def fixture(folder, wanted=('face', 'hair', 'skin')):
    """Reuse concrete identity fixture, with only its requested work selected."""
    project = Path(folder) / 'fixture-project'
    state, _, _ = make_avatar_project(project)
    original = cp.read_json(project / state['records']['stage-design:identity:CHR-TEST:base']['path'])
    payload = {'morphology': 'human', 'visual_details': {
        d: copy.deepcopy(original['payload']['visual_details'][d]) for d in wanted}}
    names = {'face': 'character-face-design', 'hair': 'character-hair-design', 'skin': 'character-skin-design'}
    work = {names[d]: copy.deepcopy(original['specialist_execution'][names[d]]) for d in wanted}
    inputs = {'request': '合成回归资料：林澄修复书籍。设计当前脸发皮肤的具体结构，不能只给性格词。',
              'requested_dimensions': list(wanted)}
    value = {'schema_version': design.SCHEMA, 'kind': 'standalone', 'scope': 'requested', 'data': {
        'schema_version': design.STANDALONE, 'scope': 'requested', 'requested_dimensions': list(wanted),
        'subject': {'name': '林澄', 'local_key': 'local-lin'}, 'sources': design.source_bindings(inputs),
        'understanding': {'role_in_story': '她通过修复和归还书页照料读者，测试只核交接机制。'},
        'design_thesis': '圆角下颌与低后脑发片共同构成稳定但不僵硬的身份轮廓。',
        'payload': payload, 'specialist_execution': work, 'unresolved': [], 'deferred_dimensions': ['body', 'costume']}}
    return value, inputs, project, state


def write(folder, value):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'design-result.json'
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'design.md').write_text(design.render(value), encoding='utf-8')
    return path


def inventory(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


class CompletionGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.caps = {c['id']: c for c in cp.read_json(ROOT / 'capabilities.json')['capabilities']}
        self.output = {'status': 'succeeded', 'result': {'status': 'done', 'artifact_path': 'nonexistent.md',
                       'summary': '完成', 'questions': []}, 'artifacts': [], 'questions': [], 'error': None}

    def test_default_files_cannot_succeed_without_actual_main_file(self):
        for name in ('character-assets', 'character-costume-designer', 'character-face-design'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'artifact_path'):
                verify_result(self.output, self.caps[name], self.folder, {'request': '设计人物'}, ROOT)

    def test_declared_real_file_is_required_even_when_another_file_exists(self):
        (self.folder / 'other.md').write_text('真实但不是所声明的主文件。', encoding='utf-8')
        self.output['artifacts'] = ['other.md']
        with self.assertRaisesRegex(ValueError, 'artifact_path'):
            verify_result(self.output, self.caps['character-assets'], self.folder, {'request': '设计人物'}, ROOT)

    def test_empty_or_whitespace_main_document_is_not_delivery(self):
        self.output['result']['artifact_path'] = 'design.md'
        self.output['artifacts'] = ['design.md']
        for content in ('', '  \n\t\r\n'):
            with self.subTest(content=repr(content)):
                (self.folder / 'design.md').write_text(content, encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'empty|blank'):
                    verify_result(self.output, self.caps['character-assets'], self.folder, {'request': '设计人物'}, ROOT)

    def test_explicit_text_has_actual_content_without_forced_files(self):
        self.output['result'].update(artifact_path='', content='人物把照料行为藏在工作流程里。偏长圆角方脸的颧点停在外眼角下方，下颌以短平弧收住；右侧短发收到耳后，后脑低层次贴合颅形。')
        self.assertEqual(verify_result(self.output, self.caps['character-design'], self.folder,
                                      {'request': '本轮只在对话交设计，不要文件', 'delivery_mode': 'text'}, ROOT), [])

    def test_text_cannot_only_claim_done(self):
        self.output['result'].update(artifact_path='', content='已完成。')
        with self.assertRaisesRegex(ValueError, 'acknowledgement'):
            verify_result(self.output, self.caps['character-assets'], self.folder,
                          {'request': '交设计文字', 'delivery_mode': 'text'}, ROOT)

    def test_no_agent_self_downgrade(self):
        self.output['result'].update(delivery_mode='text', content='只有讨论，没有交文件。', artifact_path='')
        with self.assertRaisesRegex(ValueError, 'downgrade'):
            verify_result(self.output, self.caps['character-assets'], self.folder, {'request': '交设计文件'}, ROOT)

    def test_task_kind_prevents_design_becoming_discussion(self):
        self.output['result'].update(artifact_path='', content='我建议先看方向。')
        with self.assertRaisesRegex(ValueError, 'discussion'):
            verify_result(self.output, self.caps['character-assets'], self.folder,
                          {'request': '完整设计', 'delivery_mode': 'discussion', 'task_kind': 'design'}, ROOT)

    def test_bad_project_root_does_not_become_text_escape(self):
        self.output['result'].update(artifact_path='', content='这里是完整角色设计正文。')
        with self.assertRaisesRegex(ValueError, 'real character project'):
            verify_result(self.output, self.caps['character-assets'], self.folder,
                          {'request': '设计', 'delivery_mode': 'text', 'project_root': str(self.folder)}, ROOT)

    def test_prompt_text_still_checks_real_frozen_design(self):
        value, inputs, _, _ = fixture(self.folder / 'prompt-text')
        path = write(self.folder / 'prompt-text/delivery', value)
        task = self.folder / 'prompt-text/task.json'
        task.write_text(json.dumps(inputs, ensure_ascii=False), encoding='utf-8')
        source = cp.cmd_freeze_design(SimpleNamespace(file=str(path), inputs=str(task),
            output=str(self.folder / 'prompt-text/frozen')))['design_source']
        text = '3:4竖版完整头肩头像。' + '；'.join(v for group in value['data']['payload']['visual_details'].values() for v in group.values())
        self.output['result'].update(artifact_path='', content=text)
        actual = {'request': '本轮仅在对话给完整提示词，不要文件。', 'delivery_mode': 'text',
                  'stage': 'avatar', 'purpose': 'candidate', 'design_source': source}
        self.assertEqual(verify_result(self.output, self.caps['character-image-prompt'], self.folder, actual, ROOT), [])
        source['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Frozen path changed'):
            verify_result(self.output, self.caps['character-image-prompt'], self.folder, actual, ROOT)

    def test_dialogue_only_design_can_compile_text_without_creating_frozen_files(self):
        original = ('当前完整设计稿：圆角方脸，颧部向短平颏端连续缓收；眉眼中距，鼻背平直、鼻尖圆钝，'
                    '上唇略薄、下唇中央稍厚。人物自身左侧偏分，前发顺人物右侧贴耳，后脑低层次贴合颅形。'
                    '皮肤为中性浅麦色，面颊略暖、自然哑光。身体约7.4头身但本次头像不入画；故事原因不需写进词。')
        source = {'kind': 'task_text_design', 'text': original, 'source_ref': '当前对话已给设计稿v1，非虚构消息ID',
                  'text_sha256': hashlib.sha256(original.encode('utf-8')).hexdigest(),
                  'preserve': ['人物自身左侧偏分，前发顺人物右侧贴耳，后脑低层次贴合颅形']}
        content = ('3:4竖版单人正面头像，完整头顶双肩，圆角方脸，颧部向短平颏端连续缓收；'
                   '眉眼中距，鼻背平直、鼻尖圆钝，上唇略薄、下唇中央稍厚。人物自身左侧偏分，'
                   '前发顺人物右侧贴耳，后脑低层次贴合颅形。中性浅麦肤色、面颊略暖、自然哑光，浅灰中性背景。')
        self.output['result'].update(artifact_path='', content=content)
        actual = {'request': '本次明确只在对话交词，不要创建任何设计或冻结文件。', 'delivery_mode': 'text',
                  'task_kind': 'prompt', 'stage': 'avatar', 'purpose': 'candidate', 'design_source': source}
        before = inventory(self.folder)
        self.assertEqual(verify_result(self.output, self.caps['character-image-prompt'], self.folder, actual, ROOT), [])
        self.assertEqual(inventory(self.folder), before)
        self.assertNotIn('7.4', content)
        actual['design_source']['text_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            verify_result(self.output, self.caps['character-image-prompt'], self.folder, actual, ROOT)

    def test_dialogue_source_cannot_escape_defaults_formal_ids_or_unknown_kind(self):
        source = {'kind': 'task_text_design', 'text': '圆角方脸，额颧颌颏连续，深棕侧分短发后脑贴合。', 'source_ref': '当前稿v1'}
        self.output['result'].update(artifact_path='', content='3:4竖版完整头像，圆角方脸，深棕侧分短发后脑贴合。')
        actual = {'request': '仅对话词', 'delivery_mode': 'text', 'stage': 'avatar',
                  'purpose': 'candidate', 'design_source': source, 'character_id': 'CHR-FAKE'}
        with self.assertRaises(ValueError):
            verify_result(self.output, self.caps['character-image-prompt'], self.folder, actual, ROOT)
        del actual['character_id']
        source['kind'] = 'unknown_design_source'
        with self.assertRaises(ValueError):
            verify_result(self.output, self.caps['character-image-prompt'], self.folder, actual, ROOT)
        source['kind'] = 'task_text_design'
        actual.pop('delivery_mode')
        with self.assertRaisesRegex(ValueError, 'artifact_path'):
            verify_result(self.output, self.caps['character-image-prompt'], self.folder, actual, ROOT)


class RequestedDeliveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.value, self.inputs, self.project, self.state = fixture(self.root)
        self.folder = self.root / 'delivery'

    def validate(self):
        return design.validate(write(self.folder, self.value), self.inputs)

    def test_cross_dimensions_valid_without_asset_table_or_project(self):
        before = inventory(self.project)
        result = self.validate()
        self.assertEqual(result['scope'], 'requested')
        self.assertFalse(result['approved'])
        self.assertEqual(inventory(self.project), before)

    def test_scope_and_dimension_downgrades_are_rejected(self):
        self.inputs['scope'] = 'body'
        with self.assertRaisesRegex(ValueError, 'downgrade'):
            self.validate()
        del self.inputs['scope']
        self.value['data']['requested_dimensions'] = ['hair']
        with self.assertRaisesRegex(ValueError, 'dimensions differ'):
            self.validate()

    def test_method_name_without_adopted_results_is_not_work(self):
        self.value['data']['specialist_execution']['character-hair-design']['results'] = []
        with self.assertRaisesRegex(ValueError, 'visible results'):
            self.validate()

    def test_mature_provided_design_needs_actual_source_not_invented_history(self):
        original = self.root / 'provided.md'
        original.write_text('当前具体脸发肤质原稿，源于合成测试。', encoding='utf-8')
        self.inputs.update(design_origin='provided', sources=[str(original)])
        self.value['data'].update(provenance={'kind': 'provided', 'source_path': str(original)},
                                  specialist_execution={}, sources=design.source_bindings(self.inputs))
        self.assertTrue(self.validate()['valid'])
        self.value['data']['provenance']['source_path'] = str(self.root / 'imagined.md')
        with self.assertRaisesRegex(ValueError, 'actual original'):
            self.validate()

    def test_domain_view_is_complete_and_legacy_view_still_accepted_for_old_contract(self):
        text = design.render(self.value)
        self.assertLess(text.index('## 当前完整设计'), text.index('schema_version'))
        for domain in self.value['data']['payload']['visual_details'].values():
            for concrete in domain.values():
                self.assertIn(concrete, text[:text.index('<details>')])

    def test_freeze_trial_isolated_and_parent_changes_rejected(self):
        # A hair-only delta reads the approved identity without replacing it.
        self.value, self.inputs, self.project, self.state = fixture(self.root / 'hair', ('hair',))
        key = 'stage-design:identity:CHR-TEST:base'
        refs = {key: self.state['records'][key]['sha256']}
        self.inputs.update(project_root=str(self.project), character_id='CHR-TEST', purpose='candidate', parent_refs=refs)
        self.value['data'].update(parent_refs=refs, sources=design.source_bindings(self.inputs))
        path = write(self.folder, self.value)
        task = self.root / 'inputs.json'
        task.write_text(json.dumps(self.inputs, ensure_ascii=False), encoding='utf-8')
        before = inventory(self.project)
        frozen = cp.cmd_freeze_design(SimpleNamespace(file=str(path), inputs=str(task), output=str(self.root / 'isolated')))
        self.assertFalse(frozen['approved'])
        self.assertEqual(inventory(self.project), before)
        self.assertTrue(design.validate_frozen(frozen['design_source'])['validation']['valid'])
        resolved = design.validate_frozen(frozen['design_source'])['resolved_delivery']
        self.assertIn('face', resolved['data']['payload']['visual_details'])
        self.assertEqual(resolved['data']['payload']['visual_details']['hair'], self.value['data']['payload']['visual_details']['hair'])
        retained = resolved['data']['payload'].get('prompt_detail_contract', {}).get('items', [])
        self.assertFalse(any(item['kind'] == 'hair' for item in retained))
        self.assertTrue(any(item['kind'] == 'face' for item in retained))
        with self.assertRaisesRegex(ValueError, 'active project records'):
            cp.cmd_freeze_design(SimpleNamespace(file=str(path), inputs=str(task), output=str(self.project / 'records/trial')))
        original = self.project / self.state['records'][key]['path']
        original.write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            design.validate_frozen(frozen['design_source'])

    def test_candidate_cannot_be_submitted_as_formal_prompt(self):
        candidate = self.root / 'prompt.json'
        candidate.write_text(json.dumps({'purpose': 'candidate', 'design_source': {'kind': 'task_frozen_delivery'}}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'candidates stay in drafts'):
            cp.cmd_submit(SimpleNamespace(project_root=str(self.project), kind='prompt-package', file=str(candidate),
                character_id='CHR-TEST', variant_id='base', stage='avatar', scope=None))

    def test_fresh_project_has_work_frontier_not_approval_for_missing_records(self):
        project = self.root / 'fresh'
        parser = cp.build_parser()
        cp.cmd_init(parser.parse_args(['init', '--project-root', str(project), '--project-id', 'synthetic',
            '--screenplay', str(ROOT / 'examples/sample-screenplay.json'), '--asset-table', str(ROOT / 'examples/sample-assets.json')]))
        plan = cp.cmd_plan(parser.parse_args(['plan', '--project-root', str(project), '--stage', 'avatar']))
        first = plan['next_actions'][0]
        self.assertEqual((first['record_key'], first['action'], first['category']),
                         ('script-context', 'read_or_reuse_context', 'work'))
        self.assertFalse(first['requires_user_decision'])

    def test_single_user_document_contains_current_exact_prompt(self):
        package = {'schema_version': 'CharacterPromptPackageV1', 'prompts': [{'id': 'main',
            'text': '3:4竖版，完整头像；人物右侧头发收到耳后，左侧贴耳，后脑低层次发片沿分缝连续汇入。'}]}
        text = design.render(self.value, package, include_internal=False)
        self.assertIn('## 当前可复制提示词', text)
        self.assertIn(package['prompts'][0]['text'], text)
        self.assertNotIn('schema_version', text)
        self.assertNotIn('knowledge_refs', text)

    def test_candidate_document_preserves_base_and_labels_trial(self):
        base = copy.deepcopy(self.value)
        delta = copy.deepcopy(self.value)
        delta['data']['requested_dimensions'] = ['hair']
        delta['data']['payload']['visual_details'] = {'hair': copy.deepcopy(base['data']['payload']['visual_details']['hair'])}
        delta['data']['payload']['visual_details']['hair']['volume_flow'] = '后脑体积向枕骨下方轻移，后颈发片顺着头型收拢，正面分缝保持。'
        merged = design.merged_view(delta, [base])
        text = design.render(merged, include_internal=False)
        self.assertIn(base['data']['payload']['visual_details']['face']['contour'], text)
        self.assertIn(delta['data']['payload']['visual_details']['hair']['volume_flow'], text)
        self.assertIn('尚未替换正式批准', text)
        self.assertNotEqual(base['data']['payload']['visual_details']['hair']['volume_flow'],
                            merged['data']['payload']['visual_details']['hair']['volume_flow'])

    def test_project_free_local_base_is_frozen_for_complete_candidate_inventory(self):
        from prompt_fidelity import design_inventory
        base = copy.deepcopy(self.value)
        base_path = write(self.root / 'local-base', base)
        self.inputs['requested_dimensions'] = ['hair']
        self.inputs['request'] = '仅调整同一人物后脑与后颈，脸部保持；本轮不建立正式工程。'
        self.value['data']['requested_dimensions'] = ['hair']
        self.value['data']['payload']['visual_details'] = {'hair': copy.deepcopy(base['data']['payload']['visual_details']['hair'])}
        new = '后脑体积向下移到枕骨下缘，后颈发片顺头型贴收，正面分缝不改。'
        self.value['data']['payload']['visual_details']['hair']['volume_flow'] = new
        work = copy.deepcopy(base['data']['specialist_execution']['character-hair-design'])
        work['results'][0]['visible_result'] = new
        self.value['data']['specialist_execution'] = {'character-hair-design': work}
        self.value['data']['sources'] = design.source_bindings(self.inputs)
        path = write(self.folder, self.value)
        task = path.with_name('actual-inputs.json')
        cp.write_json(task, self.inputs)
        frozen = cp.cmd_freeze_design(SimpleNamespace(file=str(path), inputs=str(task),
            output=str(self.root / 'local-frozen'), base_design=[str(base_path)]))
        checked = design.validate_frozen(frozen['design_source'])
        self.assertEqual(checked['inputs']['base_designs'], [{'path': str(base_path.resolve()), 'sha256': cp.digest(base_path)}])
        self.assertNotIn('project_root', checked['inputs'])
        resolved = checked['resolved_delivery']
        self.assertEqual(resolved['data']['payload']['visual_details']['face'], base['data']['payload']['visual_details']['face'])
        self.assertEqual(resolved['data']['payload']['visual_details']['hair']['volume_flow'], new)
        items = design_inventory(resolved, 'avatar')
        self.assertTrue(any('face' in key for key in items))
        self.assertIn(new, items['visual_details.hair.volume_flow'])
        base_path.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Local base design changed'):
            design.validate_frozen(frozen['design_source'])

    def test_local_base_cannot_mix_subjects_or_override_project_parents(self):
        base = copy.deepcopy(self.value)
        base['data']['subject']['local_key'] = 'another-person'
        path = write(self.root / 'other-person', base)
        refs = [{'path': str(path), 'sha256': cp.digest(path)}]
        with self.assertRaisesRegex(ValueError, 'another subject'):
            design.read_base_designs({'base_designs': refs}, self.value['data']['subject'])
        with self.assertRaisesRegex(ValueError, 'project-free only'):
            design.read_base_designs({'base_designs': refs, 'project_root': str(self.project)}, base['data']['subject'])

    def test_freeze_named_revision_does_not_bind_an_unrelated_neighbor_design_md(self):
        path = write(self.folder, self.value)
        revision = path.with_name('hair-revision-result.json')
        path.rename(revision)
        (self.folder / 'design.md').write_text('这是同目录其他版本的可读稿。', encoding='utf-8')
        task = path.with_name('actual-inputs.json')
        cp.write_json(task, self.inputs)
        frozen = cp.cmd_freeze_design(SimpleNamespace(file=str(revision), inputs=str(task), output=str(self.root / 'named-frozen')))
        self.assertTrue(design.validate_frozen(frozen['design_source'])['validation']['valid'])
        with self.assertRaisesRegex(ValueError, 'exact deterministic export'):
            cp.cmd_freeze_design(SimpleNamespace(file=str(revision), inputs=str(task), output=str(self.root / 'wrong-view'),
                                                 markdown=str(self.folder / 'design.md')))

    def test_body_view_keeps_part_and_view_associations(self):
        from test_design_delivery_gate import body_payload
        value = copy.deepcopy(self.value)
        value['data']['payload'] = body_payload()
        text = design.render(value, include_internal=False)
        self.assertIn('体块 / 胸腔：', text)
        self.assertIn('视角 / 正面：', text)
        self.assertIn('测量锚点 / 肩胯关系 / 关系：', text)

    def test_trial_replaces_all_legacy_and_stage_hair_views_without_losing_face(self):
        from prompt_fidelity import design_inventory
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                value, inputs, project, state = fixture(self.root / ('legacy' if legacy else 'stage'), ('hair',))
                identity_key = 'stage-design:identity:CHR-TEST:base'
                parent = cp.read_json(project / state['records'][identity_key]['path'])
                old = '人物左侧三七分缝，平缓发际线从前额延至耳侧'
                new = '正中分缝，平缓发际线向两侧对称连接，前额露出窄三角'
                parent['payload']['visual_details']['hair']['hairline_part'] = old
                parent['payload']['appearance']['hair'] = old
                parent['payload']['recognition_axes'] = {'hair_structure': old, 'face_structure': '圆角方脸下颌与短平颏端'}
                parent['payload']['identity_invariants'] = ['圆角方脸下颌与短平颏端', old]
                for item in parent['payload']['prompt_detail_contract']['items']:
                    if item['kind'] == 'hair':
                        item['cues']['hairline_part'] = old
                if legacy:
                    state['design_progression'] = 'complete'
                    key = 'design-card:CHR-TEST:base'
                    data = {'schema_version': 'CharacterDesignCardV1', 'character_id': 'CHR-TEST',
                            'variant_id': 'base', **parent['payload']}
                else:
                    key, data = identity_key, parent
                record_path = project / 'records/test-parent.json'
                cp.write_json(record_path, data)
                digest = cp.digest(data)
                state['records'][key] = {'path': 'records/test-parent.json', 'sha256': digest, 'stale': False,
                                        'approval': {'operator': 'test:synthetic-only', 'sha256': digest}}
                cp.write_json(project / 'project.json', state)
                value['data']['payload']['visual_details']['hair']['hairline_part'] = new
                inputs.update(project_root=str(project), character_id='CHR-TEST', purpose='candidate', parent_refs={key: digest})
                value['data'].update(parent_refs={key: digest}, sources=design.source_bindings(inputs))
                path = write(self.folder / ('legacy' if legacy else 'stage'), value)
                task = path.with_name('actual-inputs.json')
                cp.write_json(task, inputs)
                before = inventory(project)
                source = cp.cmd_freeze_design(SimpleNamespace(file=str(path), inputs=str(task),
                    output=str(path.parent / 'frozen')))['design_source']
                resolved = design.validate_frozen(source)['resolved_delivery']
                payload = resolved['data']['payload']
                document = design.render(resolved, include_internal=False)
                self.assertNotIn('左侧三七分缝', json.dumps(payload, ensure_ascii=False))
                self.assertIn(new, payload['appearance']['hair'])
                self.assertIn(new, payload['recognition_axes']['hair_structure'])
                self.assertIn('圆角方脸下颌与短平颏端', payload['identity_invariants'])
                self.assertIn(parent['payload']['visual_details']['face']['contour'], document)
                self.assertNotIn('左侧三七分缝', document)
                prompt_items = design_inventory(resolved, 'avatar')
                self.assertIn(new, prompt_items['visual_details.hair.hairline_part'])
                self.assertTrue(any('face' in name for name in prompt_items))
                self.assertNotIn('左侧三七分缝', '\n'.join(prompt_items.values()))
                self.assertEqual(inventory(project), before)

    def test_unseparable_mixed_invariant_is_a_real_conflict_not_a_silent_face_deletion(self):
        base = copy.deepcopy(self.value)
        base['data']['payload']['identity_invariants'] = ['贴耳短发勾出下颌线']
        delta = copy.deepcopy(self.value)
        delta['data']['requested_dimensions'] = ['hair']
        delta['data']['payload']['visual_details'] = {'hair': delta['data']['payload']['visual_details']['hair']}
        with self.assertRaisesRegex(ValueError, 'mixed-domain'):
            design.merged_view(delta, [base])


if __name__ == '__main__':
    unittest.main()

"""Synthetic design deliveries exercise real validators, not model creativity."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
sys.path.insert(0, str(ROOT / 'scripts'))
from harness_core.engine import Engine, verify_result
from prompt_fixture import cp, make_avatar_project
import test_design_execution_gate as execution_fixture
from test_design_execution_gate import current_identity
import verify_design_delivery as design


def inventory(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def body_payload():
    relations = {
        'head_body': (['头顶', '脚底'], '头顶至脚底全高采用7.5头身，头长为站立全高的1:7.5。'),
        'shoulder_hip': (['肩峰', '髋骨'], '两侧肩峰间宽度略宽于髋骨外缘宽度，宽度比约1.08倍。'),
        'torso_legs': (['臀纹', '脚底'], '臀纹至脚底的下身长于上身，约占自然站立全高53%。'),
        'arm_segments': (['肘点', '腕点'], '肩峰至肘点长接近肘点至腕点，前后两段长度约1:1。'),
        'leg_segments': (['膝点', '踝点'], '臀纹至膝点长接近膝点至踝点，小腿长约为大腿的1:1。'),
    }
    anchors = {'measurement_frame': '正面自然站立，头顶至脚底为全高，以臀纹、肘腕膝踝为测量端点。'}
    for key, (points, relation) in relations.items():
        anchors[key] = {'mode': 'numeric', 'reference_points': points, 'relation': relation,
                        'basis': '合成协议测试中的明确设计选择，非剧本测量事实。'}
    frame = '；'.join(relations[key][1] for key in ('head_body', 'shoulder_hip', 'torso_legs'))
    return {'morphology': 'human', 'visual_details': {'body': {
                'frame_proportions': frame, 'weight_posture': '胸腔轴线微向前倾，盆腔保持中正，双膝松开且重心落在足弓。'}},
            'body_form': {'proportion_anchors': anchors,
                'proportions': {key: relations[key][1] for key in ('torso_legs', 'arm_segments', 'leg_segments')},
                'masses': {'head': '头部为窄长圆角块体，后枕略饱满。', 'ribcage': '胸腔呈窄纵卵形，前后厚度适中。',
                           'pelvis': '盆腔宽度略窄于肩，前倾角较轻。', 'relationships': '头颈中线位于胸腔上方，胸盆轴线前后错开少许。'},
                'views': {'front': '正面肩胯轴线近水平，左右肢体长度保持一致。',
                          'side': '侧面胸骨略向前，腹壁与盆腔自然衔接。', 'back': '背面肩胛不翼状突出，脊柱曲线自然。'},
                'action_check': {'stance': '双足自然落地，双臂垂落。', 'script_action': '弯腰取书后转身交给读者。',
                                 'mobility_result': '腰髋和膝踝可顺序屈伸，不改变骨段比例。', 'test_status': 'not_tested'}}}


def body_execution(payload):
    knowledge = next(row for row in cp.read_json(ROOT / 'knowledge-lock.json')['snapshots']
                     if 'character-body-design' in row['capability_ids'])
    return {'character-body-design': {'mode': 'inline',
        'decision': '合成测试采用7.5头身与轻微前倾重心，仅验证具体数据交接。',
        'knowledge_refs': [{'path': knowledge['path'], 'sha256': knowledge['rules_sha256']}],
        'rules_applied': ['同时描述头身、肩胯、上下身、臂段与腿段的测量端点和比例。'],
        'results': [{'field': 'visual_details.body.frame_proportions',
                     'visible_result': payload['visual_details']['body']['frame_proportions'],
                     'basis': '合成测试的体型创作选择。', 'evidence_status': 'creative_choice'}]}}


def body_design(state):
    payload = body_payload()
    return {'schema_version': 'CharacterStageDesignV1.2', 'execution_contract_version': 2,
        'character_id': 'CHR-TEST', 'variant_id': 'base', 'scope': 'body',
        'parent_refs': {key: state['records'][key]['sha256'] for key in
                        ('design-brief:CHR-TEST:base', 'stage-design:identity:CHR-TEST:base')},
        'payload': payload, 'specialist_execution': body_execution(payload),
        'deferred_dimensions': [], 'unresolved': []}


def write_delivery(folder, delivery):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'design-result.json'
    path.write_text(json.dumps(delivery, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (folder / 'design.md').write_bytes(design.render(delivery).encode('utf-8'))
    return path


def envelope():
    return {'status': 'succeeded', 'result': {'status': 'done', 'artifact_path': 'design-result.json',
        'summary': 'Synthetic design contract fixture only', 'questions': []},
        'artifacts': ['design-result.json', 'design.md'], 'questions': [], 'error': None}


class DesignDeliveryGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.state, _, _ = make_avatar_project(self.project)
        self.delivery = {'schema_version': design.SCHEMA, 'kind': 'stage', 'scope': 'body',
                         'data': body_design(self.state)}
        self.inputs = {'request': '深化给定人物的身体比例，不制作提示词，不更改身份。',
                       'project_root': str(self.project), 'character_id': 'CHR-TEST', 'scope': 'body'}
        self.folder = self.root / 'delivery'
        self.cap = next(row for row in cp.read_json(ROOT / 'capabilities.json')['capabilities']
                        if row['id'] == 'character-design')

    def check(self, delivery=None, inputs=None):
        write_delivery(self.folder, delivery or self.delivery)
        return verify_result(envelope(), self.cap, self.folder, inputs or self.inputs, ROOT)

    def test_real_stage_and_actual_parents_are_validated_without_project_writes(self):
        before = inventory(self.project)
        self.assertEqual(len(self.check()), 2)
        self.assertEqual(inventory(self.project), before)
        self.assertFalse((self.project / 'knowledge-snapshots').exists())

    def test_validation_does_not_copy_unrelated_images_or_artifact_files(self):
        (self.project / 'huge-unrelated-image.png').write_bytes(b'image-placeholder')
        self.folder.mkdir()
        (self.folder / 'unrelated-output.bin').write_bytes(b'unrelated')
        original = design._copy_resource
        copied = []
        def tracked(source, target, relative):
            copied.append(str(relative))
            return original(source, target, relative)
        path = write_delivery(self.folder, self.delivery)
        with mock.patch.object(design, '_copy_resource', tracked):
            design.validate(path, self.inputs)
        self.assertNotIn('huge-unrelated-image.png', copied)
        self.assertNotIn('unrelated-output.bin', copied)

    def test_referenced_symlink_is_not_followed(self):
        source = self.project / 'inputs/script.json'
        real = self.project / 'inputs/real-source.json'
        source.rename(real)
        source.symlink_to(real.name)
        with self.assertRaisesRegex(ValueError, 'must not follow symlinks'):
            self.check()

    def test_unrelated_symlink_is_ignored_instead_of_followed(self):
        (self.project / 'irrelevant-link').symlink_to(self.root / 'not-present')
        self.assertEqual(len(self.check()), 2)

    def test_new_independent_proposal_is_validated_from_artifacts_without_project_import(self):
        self.state, data = current_identity(self.project)
        execution_fixture.ExecutionGateTest.independent(SimpleNamespace(data=data, root=self.folder))
        inputs = dict(self.inputs, scope='identity')
        value = {'schema_version': design.SCHEMA, 'kind': 'stage', 'scope': 'identity', 'data': data}
        before = inventory(self.project)
        self.assertEqual(len(self.check(value, inputs)), 2)
        self.assertEqual(inventory(self.project), before)
        self.assertFalse((self.project / 'drafts/specialists/face.json').exists())

    def test_default_identity_requires_and_accepts_true_deepening(self):
        self.state, data = current_identity(self.project)
        value = {'schema_version': design.SCHEMA, 'kind': 'stage', 'scope': 'identity', 'data': data}
        inputs = dict(self.inputs)
        inputs.pop('scope')
        self.assertEqual(len(self.check(value, inputs)), 2)
        value['data']['payload']['prompt_detail_contract']['items'][0]['source_refs'] = ['script:bio']
        with self.assertRaisesRegex(ValueError, 'Unresolved detail source'):
            self.check(value, inputs)

    def test_direction_scope_returns_a_brief_without_claiming_completed_stage(self):
        context_record = self.state['records']['script-context']
        context = cp.read_json(self.project / context_record['path'])
        context.update(character_index=[{'character_id': 'CHR-TEST'}], read_units=[{'unit_id': 'unit-1'}])
        (self.project / context_record['path']).write_text(json.dumps(context, ensure_ascii=False), encoding='utf-8')
        context_record['sha256'] = cp.digest(context)
        context_record['approval']['sha256'] = context_record['sha256']
        (self.project / 'project.json').write_text(json.dumps(self.state, ensure_ascii=False), encoding='utf-8')
        task = {'objective': '形成安静修复师的身份结构方向。', 'character_context': '修复师在柜台与读者交流。',
                'constraints': ['不改变小传身份'], 'expected_result': '脸发皮肤的任务分工与可画方向。'}
        brief = {'schema_version': 'DesignDirectionBriefV1', 'asset_domain': 'character',
                 'character_id': 'CHR-TEST', 'variant_id': 'base', 'context_sha256': context_record['sha256'],
                 'understanding': {'schema_version': 'CharacterUnderstandingV1',
                    **{name: '专注修复书籍且不愿浪费材料，外形为创作选择。' for name in cp.phased.UNDERSTANDING_FIELDS},
                    'evidence_unit_ids': ['unit-1']},
                 'design_thesis': '用圆角骨点和贴头发片表达克制、稳定。', 'visual_strategy': 'direct',
                 'recommended_direction': '偏长圆角方脸与贴头齐颌短波波头。', 'alternatives': [],
                 'delegated_dimensions': ['身份'], 'parent_refs': {}, 'unresolved': [],
                 'specialist_plan': {name: {'status': 'inline', 'reason': '为当前阶段设计实际可画结构。',
                                            'task': copy.deepcopy(task)} for name in cp.SPECIALIST_DOMAINS_V24}}
        value = {'schema_version': design.SCHEMA, 'kind': 'direction', 'scope': 'direction', 'data': brief}
        self.assertEqual(len(self.check(value, dict(self.inputs, scope='direction'))), 2)

    def test_markdown_only_summary_cannot_complete_design_capability(self):
        self.folder.mkdir()
        (self.folder / 'design.md').write_text('冷静、修长、偏长方脸。', encoding='utf-8')
        result = envelope()
        result.update(artifacts=['design.md'])
        result['result']['artifact_path'] = 'design.md'
        with self.assertRaisesRegex(ValueError, 'Required artifact'):
            verify_result(result, self.cap, self.folder, self.inputs, ROOT)

    def test_direction_is_not_a_successful_body_stage(self):
        value = copy.deepcopy(self.delivery)
        value['kind'] = 'direction'
        with self.assertRaisesRegex(ValueError, 'Stage task cannot be satisfied'):
            self.check(value)

    def test_self_reported_task_cannot_replace_real_task(self):
        value = copy.deepcopy(self.delivery)
        value['scope'] = 'direction'
        value['kind'] = 'direction'
        with self.assertRaisesRegex(ValueError, 'differs from actual task scope'):
            self.check(value)

    def test_omitted_scope_really_means_identity_not_any_returned_scope(self):
        inputs = dict(self.inputs)
        del inputs['scope']
        with self.assertRaisesRegex(ValueError, 'differs from actual task scope'):
            self.check(inputs=inputs)

    def test_missing_actual_inputs_cannot_validate_design(self):
        write_delivery(self.folder, self.delivery)
        with self.assertRaisesRegex(ValueError, 'actual task inputs'):
            verify_result(envelope(), self.cap, self.folder, plugin_root=ROOT)

    def test_wrong_main_artifact_is_rejected(self):
        write_delivery(self.folder, self.delivery)
        result = envelope()
        result['result']['artifact_path'] = 'design.md'
        with self.assertRaisesRegex(ValueError, 'artifact_path'):
            verify_result(result, self.cap, self.folder, self.inputs, ROOT)

    def test_new_stage_cannot_use_legacy_schema(self):
        value = copy.deepcopy(self.delivery)
        value['data']['schema_version'] = 'CharacterStageDesignV1.1'
        with self.assertRaisesRegex(ValueError, 'needs CharacterStageDesignV1.2'):
            self.check(value)

    def test_stage_marker_is_required(self):
        value = copy.deepcopy(self.delivery)
        del value['data']['execution_contract_version']
        with self.assertRaisesRegex(ValueError, 'execution_contract_version'):
            self.check(value)

    def test_wrong_character_or_parent_hash_is_rejected(self):
        value = copy.deepcopy(self.delivery)
        value['data']['character_id'] = 'CHR-OTHER'
        with self.assertRaisesRegex(ValueError, 'target mismatch'):
            self.check(value)
        value = copy.deepcopy(self.delivery)
        value['data']['parent_refs']['design-brief:CHR-TEST:base'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Parent version changed'):
            self.check(value)

    def test_changed_actual_source_is_rejected(self):
        (self.project / 'inputs/script.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Project source changed'):
            self.check()

    def test_specialist_name_without_results_is_rejected(self):
        value = copy.deepcopy(self.delivery)
        value['data']['specialist_execution']['character-body-design'].pop('results')
        with self.assertRaisesRegex(ValueError, 'needs visible results'):
            self.check(value)

    def test_mapped_result_must_exist_in_concrete_payload(self):
        value = copy.deepcopy(self.delivery)
        value['data']['specialist_execution']['character-body-design']['results'][0]['visible_result'] = '英俊挺拔。'
        with self.assertRaisesRegex(ValueError, 'actually occur'):
            self.check(value)

    def test_readable_markdown_cannot_be_handwritten_summary(self):
        write_delivery(self.folder, self.delivery)
        (self.folder / 'design.md').write_text('只是长腿人物。', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'exact deterministic export'):
            verify_result(envelope(), self.cap, self.folder, self.inputs, ROOT)

    def standalone(self):
        inputs = {'request': '人物小传：林澄27岁图书修复师，习惯躬身检视书页。仅深化身体比例。', 'scope': 'body'}
        payload = body_payload()
        understanding = {key: '小传只描述修复师的安静与细心，外观结构为本次明确的设计选择。'
                         for key in cp.phased.UNDERSTANDING_FIELDS}
        data = {'schema_version': design.STANDALONE, 'execution_contract_version': 2, 'scope': 'body',
                'subject': {'name': '林澄', 'local_key': 'local-lin'}, 'sources': design.source_bindings(inputs),
                'understanding': understanding, 'design_thesis': '用稍前倾的胸盆关系表达专注，保持可信长腿比例。',
                'payload': payload, 'specialist_execution': body_execution(payload),
                'deferred_dimensions': [], 'unresolved': []}
        return {'schema_version': design.SCHEMA, 'kind': 'standalone', 'scope': 'body', 'data': data}, inputs

    def test_request_only_standalone_biography_retains_real_deepening(self):
        value, inputs = self.standalone()
        self.assertEqual(len(self.check(value, inputs)), 2)
        self.assertFalse((self.folder / 'knowledge-snapshots').exists())

    def test_standalone_identity_reuses_strict_cue_and_execution_validation(self):
        _, identity = current_identity(self.root / 'identity-fixture')
        value, inputs = self.standalone()
        inputs['scope'] = 'identity'
        value['scope'] = value['data']['scope'] = 'identity'
        value['data']['payload'] = identity['payload']
        value['data']['specialist_execution'] = identity['specialist_execution']
        value['data']['sources'] = design.source_bindings(inputs)
        self.assertEqual(len(self.check(value, inputs)), 2)
        value['data']['specialist_execution']['character-hair-design'] = {'mode': 'not_needed', 'decision': '只用方向稿'}
        with self.assertRaisesRegex(ValueError, 'actual character-hair-design'):
            self.check(value, inputs)

    def test_standalone_request_and_file_hashes_are_bound_to_actual_inputs(self):
        value, inputs = self.standalone()
        inputs['request'] += '更换职业环境。'
        with self.assertRaisesRegex(ValueError, 'sources must match'):
            self.check(value, inputs)
        value, inputs = self.standalone()
        source = self.root / 'bio.txt'
        source.write_text('林澄人物小传', encoding='utf-8')
        inputs['sources'] = [str(source)]
        value['data']['sources'] = design.source_bindings(inputs)
        self.assertEqual(len(self.check(value, inputs)), 2)
        source.write_text('人物小传已改变', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'sources must match'):
            self.check(value, inputs)

    def test_standalone_cannot_manufacture_formal_asset_id(self):
        value, inputs = self.standalone()
        value['data']['subject']['local_key'] = 'CHR-FAKE'
        with self.assertRaisesRegex(ValueError, 'impersonate a formal'):
            self.check(value, inputs)

    def test_broken_project_path_does_not_silently_downgrade_to_standalone(self):
        value, inputs = self.standalone()
        inputs['project_root'] = str(self.root / 'missing-project')
        with self.assertRaisesRegex(ValueError, 'real character project'):
            self.check(value, inputs)

    def legacy(self, morphology='nonhuman'):
        self.state.update(pipeline_version=1, design_progression='complete')
        self.state['records'] = {key: value for key, value in self.state['records'].items()
                                 if key in {'visual-bible', 'cast-plan'}}
        (self.project / 'project.json').write_text(json.dumps(self.state, ensure_ascii=False), encoding='utf-8')
        card = {'schema_version': 'CharacterDesignCardV1', 'character_id': 'CHR-TEST', 'variant_id': 'base',
                'morphology': morphology, 'facts': [], 'inferences': [], 'approved_choices': [],
                'identity_invariants': ['三枚错位的石质圆环与独立悬浮内核。'],
                'appearance': {'body': '三枚石质圆环前后错位悬浮，外环直径约为内核直径四倍。'},
                'costume': {'construction': '不穿人类服装，表面磨蚀集中在圆环外侧转折处。'},
                'unresolved': []}
        value = {'schema_version': design.SCHEMA, 'kind': 'legacy_card', 'scope': 'complete', 'data': card}
        inputs = {key: value for key, value in self.inputs.items() if key != 'scope'}
        return value, inputs

    def test_legacy_complete_defaults_to_a_full_v1_nonhuman_card_and_stays_readonly(self):
        value, inputs = self.legacy()
        before = inventory(self.project)
        self.assertEqual(len(self.check(value, inputs)), 2)
        self.assertEqual(inventory(self.project), before)
        self.assertEqual(cp.read_json(self.project / 'project.json')['design_progression'], 'complete')
        self.assertEqual(len(self.check(value, dict(inputs, scope='complete'))), 2)

    def test_legacy_card_must_retain_full_v1_required_fields(self):
        value, inputs = self.legacy()
        del value['data']['costume']
        with self.assertRaisesRegex(ValueError, 'costume must be an object'):
            self.check(value, inputs)

    def test_legacy_card_wrong_character_and_wrong_scope_are_rejected(self):
        value, inputs = self.legacy()
        value['data']['character_id'] = 'CHR-OTHER'
        with self.assertRaisesRegex(ValueError, 'Wrong character_id'):
            self.check(value, inputs)
        value, inputs = self.legacy()
        inputs['scope'] = value['scope'] = 'identity'
        with self.assertRaisesRegex(ValueError, 'only accept scope complete'):
            self.check(value, inputs)

    def test_phased_project_cannot_use_legacy_complete_branch(self):
        value = {'schema_version': design.SCHEMA, 'kind': 'legacy_card', 'scope': 'complete',
                 'data': {'schema_version': 'CharacterDesignCardV1'}}
        with self.assertRaisesRegex(ValueError, 'only to legacy complete'):
            self.check(value, dict(self.inputs, scope='complete'))

    def test_new_legacy_lead_human_cannot_submit_low_card_version(self):
        value, inputs = self.legacy(morphology='human')
        with self.assertRaisesRegex(ValueError, 'require CharacterDesignCardV2.2'):
            self.check(value, inputs)
        self.state['pipeline_version'] = 2
        (self.project / 'project.json').write_text(json.dumps(self.state, ensure_ascii=False), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'require CharacterDesignCardV2.4'):
            self.check(value, inputs)

    def test_unchanged_approved_legacy_card_can_be_read_but_changes_need_current_contract(self):
        value, inputs = self.legacy(morphology='human')
        path = self.project / 'records/legacy-card.json'
        path.write_text(json.dumps(value['data'], ensure_ascii=False), encoding='utf-8')
        sha = cp.digest(value['data'])
        self.state['records']['design-card:CHR-TEST:base'] = {'path': 'records/legacy-card.json', 'sha256': sha,
            'stale': False, 'approval': {'operator': 'test:synthetic-old-approval', 'sha256': sha}}
        (self.project / 'project.json').write_text(json.dumps(self.state, ensure_ascii=False), encoding='utf-8')
        before = inventory(self.project)
        self.assertEqual(len(self.check(value, inputs)), 2)
        self.assertEqual(inventory(self.project), before)
        value['data']['appearance']['body'] += '新增形体选择。'
        with self.assertRaisesRegex(ValueError, 'require CharacterDesignCardV2.2'):
            self.check(value, inputs)

    def test_legacy_complete_still_requires_real_approved_global_basis(self):
        value, inputs = self.legacy()
        self.state['records']['cast-plan']['approval'] = None
        (self.project / 'project.json').write_text(json.dumps(self.state, ensure_ascii=False), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Required approved record'):
            self.check(value, inputs)

    def test_engine_rechecks_real_design_basis_on_recovery(self):
        def execute(capability, task, *args):
            write_delivery(task['artifact_dir'], self.delivery)
            return envelope(), None
        engine = Engine(ROOT, self.root / 'workspace', executor=execute)
        workflow = {'id': 'design-delivery', 'nodes': [{'id': 'design', 'capability': 'character-design',
            'depends_on': [], 'bindings': {key: {'from': 'inputs.' + key} for key in self.inputs},
            'idempotent': False, 'retries': 0}]}
        run_id = engine.create(workflow, self.inputs)
        self.assertEqual(engine.execute(run_id)['status'], 'completed')
        (self.project / 'inputs/script.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Project source changed'):
            engine.execute(run_id)


if __name__ == '__main__':
    unittest.main()

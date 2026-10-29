"""Contract tests: provenance, adoption, fresh-vs-approved compatibility.

These synthetic fixtures test enforcement, never production design quality.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import character_project as cp
import phased_design as phased
from prompt_fixture import CUES, make_avatar_project


def current_identity(root):
    state, _, _ = make_avatar_project(root)
    record = state['records']['stage-design:identity:CHR-TEST:base']
    data = cp.read_json(root / record['path'])
    data['execution_contract_version'] = 2
    data['deferred_dimensions'] = ['body', 'costume']
    payload = data['payload']
    payload['world_influences'].update(technology='当代日常生产技术', resources_and_access='普通稳定生活资源',
                                       appearance_effects=[])
    payload['facial_surface'] = {'stable_marks': [], 'applied_decoration': [], 'temporary_effects': [],
                                'absence_or_focus_decision': '无新增痣疤或妆饰，识别由骨相和发片承担'}
    payload['feature_focus'] = {
        'core_sentence': '圆角方脸下颌与贴头短波波头形成安静、稳定的可识别轮廓',
        'primary_anchors': [{'part': '下颌', 'geometry': CUES['face']['jaw_chin'],
                             'basis': '创作选择', 'visible_views': ['front', 'side']},
                            {'part': '侧发片', 'geometry': CUES['hair']['left_right'],
                             'basis': '创作选择', 'visible_views': ['front', 'side']}],
        'quiet_features': [], 'imperfection_policy': {'status': 'none', 'detail': '不新增疤痕', 'basis': '不靠伤痕区分人物'},
        'view_checks': {name: {'status': 'not_tested', 'evidence': '未生成或查看图片'}
                        for name in ['silhouette', 'occlusion']}}
    payload['differentiation_review'] = {'status': 'not_tested', 'basis': '只验证交接合同'}
    payload['identity_invariants'] = ['圆角方脸下颌与侧发片位置']
    payload['execution_layout'] = copy.deepcopy(CUES['framing'])
    work = data['specialist_execution']
    for specialist, field, kinds in [
        ('character-face-design', 'visual_details.face.contour', ['face', 'brow', 'eye', 'ear', 'nose', 'lip']),
        ('character-hair-design', 'visual_details.hair.volume_flow', ['hair']),
        ('character-skin-design', 'visual_details.skin.tone_variation', ['skin'])]:
        text = '；'.join(value for kind in kinds for value in CUES[kind].values())
        section = payload
        parts = field.split('.')
        for part in parts[:-1]:
            section = section[part]
        section[parts[-1]] = text
        work[specialist]['results'] = [{'field': field, 'visible_result': text,
                                       'basis': '合成设计结构选择，非实际能力调用', 'evidence_status': 'creative_choice'}]
    work['character-feature-focus']['results'][0].update(field='feature_focus.core_sentence',
                                                        visible_result=payload['feature_focus']['core_sentence'])
    for specialist in ['character-face-signature-design', 'character-face-decoration-design']:
        work[specialist] = {'mode': 'not_needed', 'decision': '当前基础身份不添加饰物或妆饰',
                            'execution_change_reason': '基础识别交给已设计的下颌和发片',
                            'not_applicable_reason': '此阶段无饰物或施加妆面需求'}
    for item in payload['prompt_detail_contract']['items']:
        kind = item['kind']
        owner = ('character-hair-design' if kind == 'hair' else 'character-skin-design' if kind == 'skin'
                 else 'character-face-design')
        item['source_refs'] = (['payload.execution_layout'] if kind == 'framing' else
                               [f'specialist_execution.{owner}.results.0'])
    return state, data


class ExecutionGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state, self.data = current_identity(self.root)

    def validate(self, data=None):
        phased.validate_stage(cp, self.root, self.state, data or self.data,
                              'CHR-TEST', 'base', 'identity')

    def test_complete_inline_stage_with_drawable_cues_is_valid(self):
        self.validate()

    def test_all_planned_inline_cannot_be_silently_skipped(self):
        self.data['specialist_execution'] = {name: {'mode': 'not_needed', 'decision': '沿用方向稿'}
                                             for name in phased.SCOPE_SPECIALISTS['identity']}
        with self.assertRaisesRegex(ValueError, 'actual|execution_change_reason'):
            self.validate()

    def test_legitimate_no_adornment_and_no_makeup_are_valid(self):
        self.validate()
        self.data['specialist_execution']['character-face-signature-design'].pop('execution_change_reason')
        with self.assertRaisesRegex(ValueError, 'execution_change_reason'):
            self.validate()

    def test_baldness_is_an_active_hair_result_not_a_skip(self):
        work = self.data['specialist_execution']['character-hair-design']
        work.update(mode='not_needed', decision='无头发', execution_change_reason='剃光头',
                    not_applicable_reason='没有毛发')
        with self.assertRaisesRegex(ValueError, 'actual character-hair-design'):
            self.validate()

    def test_unrelated_knowledge_fails_even_when_sha_is_cached(self):
        row = next(row for row in cp.read_json(ROOT / 'knowledge-lock.json')['snapshots']
                   if 'character-body-design' in row['capability_ids'] and
                   'character-face-design' not in row['capability_ids'])
        snapshot = self.root / 'knowledge-snapshots' / row['rules_sha256']
        snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_bytes((ROOT / row['path']).read_bytes())
        self.data['specialist_execution']['character-face-design']['knowledge_refs'] = [
            {'path': row['path'], 'sha256': row['rules_sha256']}]
        with self.assertRaisesRegex(ValueError, 'not locked for specialist'):
            self.validate()

    def test_arbitrary_source_label_does_not_prove_deepening(self):
        self.data['payload']['prompt_detail_contract']['items'][0]['source_refs'] = ['script:bio']
        with self.assertRaisesRegex(ValueError, 'Unresolved detail source'):
            self.validate()

    def test_new_unadopted_cue_fails_even_with_valid_specialist_ref(self):
        item = next(item for item in self.data['payload']['prompt_detail_contract']['items'] if item['kind'] == 'nose')
        item['cues']['bridge_tip_wings'] = '高而弯曲的鹰钩鼻骨，鼻尖向下明显收尖'
        with self.assertRaisesRegex(ValueError, 'absent from its adopted'):
            self.validate()

    def test_evidence_or_prompt_metadata_cannot_replace_an_adopted_design_field(self):
        result = self.data['specialist_execution']['character-face-design']['results'][0]
        self.data['payload']['facts'] = [{'text': result['visible_result'], 'source_refs': ['synthetic:fact']}]
        result['field'] = 'facts'
        with self.assertRaisesRegex(ValueError, 'owned design field'):
            self.validate()

    def test_wrong_specialist_or_layout_cannot_supply_face_cues(self):
        item = next(item for item in self.data['payload']['prompt_detail_contract']['items'] if item['kind'] == 'face')
        for ref in ['specialist_execution.character-hair-design.results.0', 'payload.execution_layout']:
            item['source_refs'] = [ref]
            with self.assertRaisesRegex(ValueError, 'another specialist|Layout may only'):
                self.validate()

    def independent(self):
        specialist = 'character-face-design'
        work = self.data['specialist_execution'][specialist]
        proposal = {'schema_version': 'CharacterSpecialistProposalV1.2', 'specialist': specialist,
                    'character_id': 'CHR-TEST', 'variant_id': 'base', 'scope': 'identity',
                    'execution_mode': 'independent',
                    'task': {'objective': '解决骨点与发片遮挡冲突', 'character_context': '修复师的稳定身份',
                             'constraints': ['保留已定年龄'], 'expected_result': '正面与45度一致的面部结构'},
                    'knowledge_refs': work['knowledge_refs'], 'facts': [], 'unresolved': [],
                    'not_applicable_reason': None, 'recommended_option_id': 'one',
                    'options': [{'id': 'one', 'visible_design': work['results'][0]['visible_result'],
                                 'rationale': '保留骨点', 'comparison_difference': '短宽颏端',
                                 'production_check': '尚待审图', 'design_elements': [
                                     {'part': '脸', 'visible_feature': CUES['face']['type'],
                                      'placement_or_structure': CUES['face']['jaw_chin'],
                                      'basis': '创作选择', 'evidence_status': 'creative_choice'},
                                     {'part': '眼', 'visible_feature': CUES['eye']['shape_placement'],
                                      'placement_or_structure': CUES['eye']['lid_iris'],
                                      'basis': '创作选择', 'evidence_status': 'creative_choice'}]}]}
        path = self.root / 'drafts/specialists/face.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(proposal, ensure_ascii=False), encoding='utf-8')
        self.data['specialist_execution'][specialist] = {
            'mode': 'independent', 'decision': '采用骨点稳定方案', 'execution_change_reason': '由独立会诊处理遮挡',
            'proposal_ref': 'drafts/specialists/face.json', 'proposal_sha256': cp.digest(path),
            'selected_option_id': 'one', 'applied_elements': [{'field': 'visual_details.face.contour', 'element_index': 0}]}
        for item in self.data['payload']['prompt_detail_contract']['items']:
            if item['kind'] in ['face', 'brow', 'eye', 'ear', 'nose', 'lip']:
                item['source_refs'] = [f'specialist_execution.{specialist}.applied_elements.0']

    def test_real_independent_adoption_and_bound_cues_are_valid(self):
        self.independent()
        self.validate()

    def test_independent_index_alone_is_not_adoption(self):
        self.independent()
        self.data['payload']['visual_details']['face']['contour'] = '另一张完整且可画的脸，未采用返回的骨点结构'
        with self.assertRaisesRegex(ValueError, 'selected feature and structure'):
            self.validate()

    def test_independent_proposal_from_another_scope_is_not_adoptable(self):
        self.independent()
        work = self.data['specialist_execution']['character-face-design']
        path = self.root / work['proposal_ref']
        proposal = cp.read_json(path)
        proposal['scope'] = 'body'
        cp.write_json(path, proposal)
        work['proposal_sha256'] = cp.digest(path)
        with self.assertRaisesRegex(ValueError, 'current stage scope'):
            self.validate()

    def test_nonhuman_can_exclude_human_features_with_explicit_change(self):
        payload = self.data['payload']
        payload.update(morphology='nonhuman', morphology_details={'identity': {'shape': '悬浮的三面石质几何体'}},
                       visual_details={})
        payload.pop('prompt_detail_contract')
        self.data['specialist_execution'] = {
            name: {'mode': 'not_needed', 'decision': '非人石体不具人脸、皮肤和毛发',
                   'execution_change_reason': '本轮明确形态为非人石质几何体',
                   'not_applicable_reason': '该领域的人类局部结构不适用'}
            for name in phased.SCOPE_SPECIALISTS['identity']}
        self.validate()

    def test_new_stage_without_contract_marker_is_rejected(self):
        self.data.pop('execution_contract_version')
        with self.assertRaisesRegex(ValueError, 'execution_contract_version'):
            self.validate()

    def test_body_requires_actual_body_design_but_allows_explicit_nonhuman_exclusion(self):
        data = {'scope': 'body', 'character_id': 'LOCAL-TEST', 'payload': {'morphology': 'human'},
                'specialist_execution': {'character-body-design': {'mode': 'not_needed', 'decision': '已有身高体重'}}}
        with self.assertRaisesRegex(ValueError, 'actual character-body-design'):
            phased.validate_execution(cp, self.root, data)
        row = next(row for row in cp.read_json(ROOT / 'knowledge-lock.json')['snapshots']
                   if 'character-body-design' in row['capability_ids'])
        text = '头顶至足底为7.5头身；髋关节至足底略长于头顶至髋关节，膝盖在髋踝连线中点上方'
        data['payload']['visual_details'] = {'body': {'frame_proportions': text}}
        data['specialist_execution']['character-body-design'] = {
            'mode': 'inline', 'decision': '在可信范围延长下肢并检查行动余量',
            'rules_applied': ['以头顶、髋、膝、踝和足底检查分段比例'],
            'knowledge_refs': [{'path': row['path'], 'sha256': row['rules_sha256']}],
            'results': [{'field': 'visual_details.body.frame_proportions', 'visible_result': text,
                         'basis': '明确标为创作比例选择', 'evidence_status': 'creative_choice'}]}
        phased.validate_execution(cp, self.root, data)
        data['payload']['morphology'] = 'nonhuman'
        data['specialist_execution']['character-body-design'] = {'mode': 'not_needed', 'decision': '纯能量体不适用人类分段比例'}
        phased.validate_execution(cp, self.root, data)

    def test_execution_inheritance_is_limited_to_real_approved_parent_and_sha(self):
        parent_key = 'stage-design:identity:CHR-TEST:base'
        data = {'scope': 'costume', 'character_id': 'CHR-TEST',
                'parent_refs': {parent_key: self.state['records'][parent_key]['sha256']}}
        ref = f'approved_parent:{parent_key}#payload.visual_details.hair'
        self.assertIn(CUES['hair']['hairline_part'],
                      phased._detail_source(cp, self.root, self.state, data, 'hair', ref))
        data['parent_refs'][parent_key] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'current stage parent SHA'):
            phased._detail_source(cp, self.root, self.state, data, 'hair', ref)
        data['parent_refs'][parent_key] = self.state['records'][parent_key]['sha256']
        with self.assertRaisesRegex(ValueError, 'another|belong'):
            phased._detail_source(cp, self.root, self.state, data, 'hair',
                                  f'approved_parent:{parent_key}#payload.visual_details.face')

    def test_approved_legacy_read_and_identical_submit_remain_valid(self):
        state, _, _ = make_avatar_project(self.root / 'legacy')
        root = self.root / 'legacy'
        key = 'stage-design:identity:CHR-TEST:base'
        record = cp._checked_record(root, state, key)
        args = SimpleNamespace(kind='stage-design', character_id='CHR-TEST', variant_id='base',
                               scope='identity', file=root / record['path'])
        self.assertEqual(phased.submit(cp, args, root, state)['status'], 'unchanged')

    def test_modified_legacy_stage_must_meet_current_contract(self):
        state, _, _ = make_avatar_project(self.root / 'legacy')
        root = self.root / 'legacy'
        old = cp.read_json(root / state['records']['stage-design:identity:CHR-TEST:base']['path'])
        old['unresolved'] = ['修改旧稿需重新深化']
        path = root / 'changed.json'
        path.write_text(json.dumps(old, ensure_ascii=False), encoding='utf-8')
        args = SimpleNamespace(kind='stage-design', character_id='CHR-TEST', variant_id='base',
                               scope='identity', file=path)
        with self.assertRaisesRegex(ValueError, 'execution_contract_version'):
            phased.submit(cp, args, root, state)

    def test_avatar_and_execution_metadata_compose_without_overwriting_identity(self):
        identity = {'morphology': 'human', 'appearance': {'face': '已批脸型'},
                    'prompt_detail_contract': {'stage': 'avatar', 'items': [{'id': 'face'}]},
                    'execution_layout': {'canvas_crop': '3:4头像'}}
        costume = {'costume': {'name': 'S03婚纱'},
                   'prompt_detail_contract': {'stage': 'execution', 'items': [{'id': 'garment'}]},
                   'execution_layout': {'canvas_crop': '9:16执行四格'}}
        merged = phased.merge_payloads(cp, [identity, {'body_form': {'ratio': '7.5头身'}}, costume])
        self.assertEqual(set(merged['prompt_detail_contracts']), {'avatar', 'execution'})
        self.assertEqual(merged['prompt_detail_contracts']['avatar'], identity['prompt_detail_contract'])
        self.assertEqual(merged['stage_execution_layouts']['identity'], identity['execution_layout'])
        self.assertEqual(merged['execution_layout'], costume['execution_layout'])
        self.assertEqual(merged['appearance'], identity['appearance'])
        self.assertEqual(identity['execution_layout']['canvas_crop'], '3:4头像')

    def test_legacy_execution_receipt_read_does_not_require_new_morphology_parent(self):
        root = self.root / 'receipt-only'
        root.mkdir()
        brief = {'specialist_plan': {name: {'status': 'not_needed'} for name in cp.SPECIALIST_DOMAINS_V24}}
        cp.write_json(root / 'brief.json', brief)
        state = {'records': {'design-brief:LOCAL:base': {'path': 'brief.json', 'sha256': cp.digest(brief)}}}
        data = {'scope': 'body', 'character_id': 'LOCAL', 'payload': {},
                'specialist_execution': {'character-body-design': {'mode': 'not_needed', 'decision': '历史协议夹具'}}}
        phased.validate_execution(cp, root, data, state, strict=False)

    def test_plan_and_stage_validation_are_read_only_and_submit_archives(self):
        before = {str(path.relative_to(self.root)): path.read_bytes()
                  for path in self.root.rglob('*') if path.is_file()}
        args = SimpleNamespace(project_root=str(self.root), character_id='CHR-TEST',
                               variant_id=None, stage=None)
        cp.cmd_plan(args)
        self.validate()
        after = {str(path.relative_to(self.root)): path.read_bytes()
                 for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(before, after)
        path = self.root / 'new-identity.json'
        cp.write_json(path, self.data)
        result = phased.submit(cp, SimpleNamespace(kind='stage-design', character_id='CHR-TEST',
                              variant_id='base', scope='identity', file=path), self.root, self.state)
        self.assertEqual(result['status'], 'awaiting-approval')
        self.assertTrue(list((self.root / 'knowledge-snapshots').iterdir()))


if __name__ == '__main__':
    unittest.main()

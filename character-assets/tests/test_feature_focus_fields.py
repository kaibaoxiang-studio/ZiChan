"""Synthetic focus/adoption regressions; no production screenplay material."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from prompt_fixture import cp
from test_design_delivery_gate import body_execution, body_payload
from test_design_execution_gate import current_identity
from test_task_delivery_v0216 import fixture, write
import verify_design_delivery as design


FOCUS = 'character-feature-focus'


class RequestedFocusFieldTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.value, self.inputs, _, _ = fixture(self.root)
        knowledge = next(row for row in cp.read_json(ROOT / 'knowledge-lock.json')['snapshots']
                         if FOCUS in row['capability_ids'])
        self.work = {
            'mode': 'inline', 'decision': '合成测试选择现有结构承担主锚点，其余结构保留。',
            'rules_applied': ['在当前可见结构内选择主锚点与安静区；不替代各域的具体设计。'],
            'knowledge_refs': [{'path': knowledge['path'], 'sha256': knowledge['rules_sha256']}],
            'results': []}
        self.value['data']['specialist_execution'][FOCUS] = self.work
        self.result('visual_details.face.nose_mouth')

    def result(self, field, visible=None):
        self.work['results'] = [{
            'field': field,
            'visible_result': (cp.phased._get(self.value['data']['payload'], field)
                               if visible is None else visible),
            'basis': '合成回归中的结构选择，不是真实剧本外貌事实。',
            'evidence_status': 'creative_choice'}]

    def validate(self):
        return design.validate(write(self.root / 'delivery', self.value), self.inputs)

    def independent(self, field='visual_details.face.contour', scope='identity'):
        """Write a real, hash-bound synthetic consultation and adopt element 0."""
        visible = cp.phased._get(self.value['data']['payload'], field)
        feature, _, placement = visible.partition('；')
        element = {'part': '当前可见结构', 'visible_feature': feature,
                   'placement_or_structure': placement or feature,
                   'basis': '合成回归的具体结构选择。', 'evidence_status': 'creative_choice'}
        proposal = {
            'schema_version': 'CharacterSpecialistProposalV1.2', 'specialist': FOCUS,
            'character_id': self.value['data']['subject']['local_key'], 'variant_id': 'base',
            'scope': scope, 'execution_mode': 'independent',
            'task': {'objective': '选择当前可见结构的主锚点', 'character_context': '合成角色的身份辨识',
                     'constraints': ['保留当前任务之外的结构'], 'expected_result': '可落实到当前设计的结构'},
            'knowledge_refs': copy.deepcopy(self.work['knowledge_refs']), 'facts': [], 'unresolved': [],
            'not_applicable_reason': None, 'recommended_option_id': 'one',
            'options': [{'id': 'one', 'visible_design': visible, 'rationale': '主锚点与安静区并存。',
                         'comparison_difference': '保留当前结构，通过主次安排区分。',
                         'production_check': '未生成或查看图片。',
                         'design_elements': [element, {**element, 'part': '次级结构保留'}]}]}
        relative = 'drafts/specialists/focus-proposal.json'
        path = self.root / 'delivery' / relative
        cp.write_json(path, proposal)
        self.work.clear()
        self.work.update(mode='independent', decision='采用经独立提案落实的当前结构。',
                         proposal_ref=relative, proposal_sha256=cp.digest(path),
                         selected_option_id='one', applied_elements=[{'field': field, 'element_index': 0}])
        return path, proposal

    def save_proposal(self, path, proposal):
        cp.write_json(path, proposal)
        self.work['proposal_sha256'] = cp.digest(path)

    def test_adopted_visible_focus_passes_with_required_methods_retained(self):
        before = copy.deepcopy(self.value['data']['specialist_execution'])
        for field in ('visual_details.face.nose_mouth', 'visual_details.hair.volume_flow',
                      'visual_details.skin.surface_distribution'):
            with self.subTest(field=field):
                self.result(field)
                self.assertTrue(self.validate()['valid'])
        for specialist in ('character-face-design', 'character-hair-design', 'character-skin-design'):
            self.assertEqual(self.value['data']['specialist_execution'][specialist], before[specialist])

    def test_focus_cannot_replace_required_same_domain_work(self):
        self.result('visual_details.hair.volume_flow')
        self.value['data']['specialist_execution'].pop('character-hair-design')
        with self.assertRaisesRegex(ValueError, 'Current hair design needs actual method results'):
            self.validate()

    def test_focus_cannot_adopt_an_unrequested_domain(self):
        self.inputs['requested_dimensions'] = self.value['data']['requested_dimensions'] = ['hair']
        self.value['data']['payload']['visual_details'] = {
            'hair': self.value['data']['payload']['visual_details']['hair']}
        self.value['data']['specialist_execution'] = {
            FOCUS: self.work,
            'character-hair-design': self.value['data']['specialist_execution']['character-hair-design']}
        with self.assertRaisesRegex(ValueError, 'another domain'):
            self.validate()

    def test_metadata_and_unknown_domains_cannot_substitute_for_visible_structure(self):
        payload = self.value['data']['payload']
        payload['feature_focus'] = {'core': '合成回归的主锚点说明'}
        payload['facts'] = {'anchor': '合成回归的事实标签'}
        for field in ('feature_focus.core', 'facts.anchor', 'visual_details.unknown.anchor'):
            with self.subTest(field=field):
                self.result(field, '合成回归的标签')
                with self.assertRaisesRegex(ValueError, 'another domain'):
                    self.validate()

    def test_missing_or_nonleaf_structure_fails_with_controlled_error(self):
        for field in ('visual_details.face.missing', 'visual_details.face.contour.missing'):
            with self.subTest(field=field):
                self.result(field, '合成回归中没有采用的结构')
                with self.assertRaisesRegex(ValueError, 'Applied design field missing'):
                    self.validate()

    def test_unadopted_focus_result_is_rejected(self):
        self.result('visual_details.face.nose_mouth', '尖细鼻尖与窄口是本稿没有采用的结构')
        with self.assertRaisesRegex(ValueError, 'actually occur in its adopted design field'):
            self.validate()

    def test_focus_needs_actual_results_and_applicable_locked_knowledge(self):
        self.work['results'] = []
        with self.assertRaisesRegex(ValueError, 'visible results'):
            self.validate()
        self.result('visual_details.face.nose_mouth')
        self.work['knowledge_refs'] = copy.deepcopy(
            self.value['data']['specialist_execution']['character-hair-design']['knowledge_refs'])
        with self.assertRaisesRegex(ValueError, 'not locked for specialist'):
            self.validate()

    def test_nonhuman_focus_can_adopt_current_visible_structure(self):
        data = self.value['data']
        data['requested_dimensions'] = self.inputs['requested_dimensions'] = ['hair']
        data['payload'] = {'morphology': 'nonhuman', 'visual_details': {},
                           'morphology_details': {'hair': {'crest': '头顶三片平行薄翅向后贴拢'}}}
        self.result('morphology_details.hair.crest')
        hair = copy.deepcopy(self.work)
        hair['knowledge_refs'] = copy.deepcopy(
            data['specialist_execution']['character-hair-design']['knowledge_refs'])
        data['specialist_execution'] = {FOCUS: self.work, 'character-hair-design': hair}
        self.assertTrue(self.validate()['valid'])
        text = data['payload']['morphology_details']['hair']['crest']
        data['payload']['morphology_details']['hair']['crest'] = {'label': text}
        hair['results'][0]['field'] += '.label'
        with self.assertRaisesRegex(ValueError, 'concrete visible leaf field'):
            self.validate()

    def test_independent_identity_focus_adopts_real_proposal(self):
        self.independent()
        self.assertTrue(self.validate()['valid'])

    def test_independent_body_focus_keeps_body_method_required(self):
        data = self.value['data']
        data['requested_dimensions'] = self.inputs['requested_dimensions'] = ['body']
        data['payload'] = body_payload()
        data['specialist_execution'] = {**body_execution(data['payload']), FOCUS: self.work}
        self.independent('visual_details.body.frame_proportions', 'body')
        self.assertTrue(self.validate()['valid'])
        data['specialist_execution'].pop('character-body-design')
        with self.assertRaisesRegex(ValueError, 'Current body design needs actual method results'):
            self.validate()

    def test_independent_costume_focus_respects_adornment_ownership(self):
        data = self.value['data']
        data['requested_dimensions'] = self.inputs['requested_dimensions'] = ['adornments']
        data['payload']['visual_details'] = {'adornments': {
            'body_hands': '窄皮腕带沿手腕外侧单圈贴合；接头固定于腕背并向内收住',
            'head_neck': '颈后细带贴合发际下缘；接头藏于后颈中央'}}
        accessory = copy.deepcopy(self.work)
        row = next(row for row in cp.read_json(ROOT / 'knowledge-lock.json')['snapshots']
                   if 'character-costume-accessory-design' in row['capability_ids'])
        accessory.update(knowledge_refs=[{'path': row['path'], 'sha256': row['rules_sha256']}],
                         results=[{**self.work['results'][0], 'field': 'visual_details.adornments.body_hands',
                                   'visible_result': data['payload']['visual_details']['adornments']['body_hands']}])
        data['specialist_execution'] = {FOCUS: self.work, 'character-costume-accessory-design': accessory}
        path, proposal = self.independent('visual_details.adornments.body_hands', 'costume')
        self.assertTrue(self.validate()['valid'])
        proposal['scope'] = 'identity'
        self.save_proposal(path, proposal)
        with self.assertRaisesRegex(ValueError, 'another scope or domain'):
            self.validate()

    def test_independent_focus_cannot_use_unknown_or_unrequested_scope(self):
        path, proposal = self.independent()
        for scope, message in (('requested', 'concrete identity/body/costume scope'),
                               ('body', 'scope is outside the current task')):
            with self.subTest(scope=scope):
                proposal['scope'] = scope
                self.save_proposal(path, proposal)
                with self.assertRaisesRegex(ValueError, message):
                    self.validate()

    def test_independent_focus_checks_each_mapping_against_scope_and_requested_domains(self):
        self.independent()
        for field in ('visual_details.costume.neckline', 'visual_details.unknown.anchor', 'feature_focus.core'):
            with self.subTest(field=field):
                self.work['applied_elements'].append({'field': field, 'element_index': 1})
                with self.assertRaisesRegex(ValueError, 'another scope or domain'):
                    self.validate()
                self.work['applied_elements'].pop()
        # Even an identity-owned domain is outside this hair-only request.
        self.inputs['requested_dimensions'] = self.value['data']['requested_dimensions'] = ['hair']
        self.value['data']['payload']['visual_details'] = {
            'hair': self.value['data']['payload']['visual_details']['hair']}
        self.value['data']['specialist_execution'] = {
            FOCUS: self.work,
            'character-hair-design': self.value['data']['specialist_execution']['character-hair-design']}
        with self.assertRaisesRegex(ValueError, 'another scope or domain'):
            self.validate()

    def test_independent_focus_rejects_missing_leaf_and_missing_adoption(self):
        self.independent()
        mapping = self.work['applied_elements'][0]
        mapping['field'] = 'visual_details.face.missing'
        with self.assertRaisesRegex(ValueError, 'Applied design field missing'):
            self.validate()
        mapping['field'] = 'visual_details.face.contour'
        self.value['data']['payload']['visual_details']['face']['contour'] = '替换后的方脸，未采用原提案结构。'
        # Retain the ordinary face method's adopted result so focus is the
        # actual reason for rejection in this regression.
        self.value['data']['specialist_execution']['character-face-design']['results'][0]['visible_result'] = (
            self.value['data']['payload']['visual_details']['face']['contour'])
        with self.assertRaisesRegex(ValueError, 'Independent result is not adopted'):
            self.validate()

    def test_independent_focus_does_not_accept_container_as_leaf(self):
        data = self.value['data']
        data['requested_dimensions'] = self.inputs['requested_dimensions'] = ['hair']
        data['payload'] = {'morphology': 'nonhuman', 'visual_details': {},
                           'morphology_details': {'hair': {'crest': '头顶三片平行薄翅；向后沿头顶贴拢'}}}
        hair = copy.deepcopy(self.work)
        hair['knowledge_refs'] = copy.deepcopy(
            data['specialist_execution']['character-hair-design']['knowledge_refs'])
        hair['results'] = [{**hair['results'][0], 'field': 'morphology_details.hair.crest',
                            'visible_result': data['payload']['morphology_details']['hair']['crest']}]
        data['specialist_execution'] = {FOCUS: self.work, 'character-hair-design': hair}
        self.independent('morphology_details.hair.crest')
        self.assertTrue(self.validate()['valid'])
        text = data['payload']['morphology_details']['hair']['crest']
        data['payload']['morphology_details']['hair']['crest'] = {'label': text}
        data['specialist_execution']['character-hair-design']['results'][0]['field'] += '.label'
        with self.assertRaisesRegex(ValueError, 'concrete visible leaf field'):
            self.validate()

    def test_independent_focus_still_requires_bound_proposal_target(self):
        path, proposal = self.independent()
        self.work['proposal_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'SHA'):
            self.validate()
        for key, value in (('character_id', 'another-local-character'), ('specialist', 'character-face-design'),
                           ('variant_id', 'another-variant'), ('execution_mode', 'inline')):
            with self.subTest(key=key):
                original = proposal[key]
                proposal[key] = value
                self.save_proposal(path, proposal)
                with self.assertRaisesRegex(ValueError, 'proposal target mismatch'):
                    self.validate()
                proposal[key] = original

    def test_focus_consultation_does_not_enable_unrelated_independent_specialists(self):
        self.independent()
        self.value['data']['specialist_execution']['character-world-appearance-design'] = (
            self.value['data']['specialist_execution'].pop(FOCUS))
        with self.assertRaisesRegex(ValueError, 'Independent specialist is outside the current task'):
            self.validate()


class PhasedFocusFieldTest(unittest.TestCase):
    def test_existing_focus_metadata_and_adopted_visible_field_both_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state, data = current_identity(root)
            cp.phased.validate_stage(cp._runtime(), root, state, data,
                                     'CHR-TEST', 'base', 'identity')
            result = data['specialist_execution'][FOCUS]['results'][0]
            result.update(field='visual_details.face.nose_mouth',
                          visible_result=data['payload']['visual_details']['face']['nose_mouth'])
            cp.phased.validate_stage(cp._runtime(), root, state, data,
                                     'CHR-TEST', 'base', 'identity')
            result['visible_result'] = '本稿没有采用的尖细鼻尖'
            with self.assertRaisesRegex(ValueError, 'actually occur in its mapped payload field'):
                cp.phased.validate_stage(cp._runtime(), root, state, data,
                                         'CHR-TEST', 'base', 'identity')


if __name__ == '__main__':
    unittest.main()

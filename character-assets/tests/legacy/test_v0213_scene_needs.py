"""Synthetic function-level state and execution handoff checks; no images or model."""
from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN / 'scripts'))
import character_project as cp
import phased_design as phased

CUES = {
    'makeup': '低饱和暖棕唇色', 'hair': '左侧收束低发髻',
    'head_ear_neck': '耳垂小型银环', 'wearable_accessories': '左腕一条细银链',
    'garment': '右肩单层斜裁衣片',
}
FIELDS = {
    'makeup': 'state_makeup', 'hair': 'state_hair',
    'head_ear_neck': 'head_ear_neck', 'wearable_accessories': 'wearable_accessories',
}


def stage():
    direction = {field: CUES[name] for name, field in FIELDS.items()}
    direction.update(front_structure=CUES['garment'], back_structure='背缝连续连接至裙片内侧',
                     cut_and_fastening='斜裁缝线藏在肩带下缘', color_placement='暖灰白主衣配极少暗银',
                     material_behavior='细密哑光织物形成软褶')
    direction['scene_needs'] = {
        'occasion': '1-1公开婚礼仪式', 'shot_and_action': '近景见头肩、全身及背面，人物步行入场',
        'constraint_scope': '批准脸型肤色不变，只深化本仪式的临时妆发与服饰',
        'requirements': {name: {'decision': 'design', 'reason': '当前公开仪式与近景呈现需要本项设计，与既有身份保持连续。',
                               'source_refs': ['1-1'], 'prompt_cues': [cue]} for name, cue in CUES.items()}}
    mapped = {
        'character-costume-style-design': 'front_structure',
        'character-costume-cut-design': 'cut_and_fastening',
        'character-costume-color-design': 'color_placement',
        'character-costume-material-design': 'material_behavior',
    }
    mapped.update({spec: field.rsplit('.', 1)[-1] for _, (spec, field) in phased.STATE_STYLING_SPECIALISTS.items()})
    knowledge = cp.read_json(PLUGIN / 'knowledge-lock.json')['snapshots']
    execution = {}
    for specialist, field in mapped.items():
        item = next(x for x in knowledge if specialist in x['capability_ids'])
        execution[specialist] = {
            'mode': 'inline', 'decision': '落实当前场次可见细节，不变更已批准脸型。',
            'rules_applied': ['执行所载入专项的结构、连接和可见性规则。'],
            'knowledge_refs': [{'path': item['path'], 'sha256': item['rules_sha256']}],
            'results': [{'field': 'costume_direction.' + field, 'visible_result': direction[field],
                         'basis': '本场近景与仪式呈现的待审创作选择。', 'evidence_status': 'creative_choice'}],
        }
    return {'schema_version': 'CharacterStageDesignV1.1', 'character_id': 'CHR-001',
            'variant_id': 'S03', 'scope': 'costume', 'payload': {'costume_direction': direction},
            'specialist_execution': execution}


def package():
    text = '；'.join(CUES.values())
    return {'prompts': [{'id': 'main', 'text': text}], 'acceptance_checks': [text]}


class SceneNeedsContract(unittest.TestCase):
    def test_complete_state_visible_design_is_valid(self):
        phased.validate_scene_needs(cp, stage())

    def test_reasoned_empty_visible_zone_is_valid(self):
        data = stage()
        req = data['payload']['costume_direction']['scene_needs']['requirements']['head_ear_neck']
        req.clear(); req.update(decision='explicit_none', reason='该场颈耳被批准的高领与面纱遮挡，构图没有展示首饰的需要。', source_refs=['1-1'])
        data['specialist_execution']['character-face-signature-design'] = {'mode': 'not_needed', 'decision': '该场画外留空'}
        phased.validate_scene_needs(cp, data)

    def test_missing_scene_need_is_not_complete(self):
        data = stage(); del data['payload']['costume_direction']['scene_needs']['requirements']['makeup']
        with self.assertRaisesRegex(ValueError, 'must decide'):
            phased.validate_scene_needs(cp, data)

    def test_designed_need_requires_active_specialist(self):
        data = stage(); data['specialist_execution']['character-face-signature-design']['mode'] = 'not_needed'
        with self.assertRaisesRegex(ValueError, 'requires active'):
            phased.validate_scene_needs(cp, data)

    def test_cue_must_come_from_visible_design_field(self):
        data = stage(); data['payload']['costume_direction']['scene_needs']['requirements']['head_ear_neck']['prompt_cues'] = ['并未设计的金皇冠']
        with self.assertRaisesRegex(ValueError, 'must come from mapped'):
            phased.validate_scene_needs(cp, data)

    def test_package_metadata_matches_installed_version(self):
        self.assertEqual(cp.PLUGIN_VERSION, '0.2.15')


class PromptCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.data = stage()
        cp.write_json(self.root / 'stage.json', self.data)
        self.api = SimpleNamespace(ensure=cp.ensure, read_json=cp.read_json,
                                   _checked_record=lambda *args: {'path': 'stage.json'})

    def check(self, value):
        phased.validate_scene_prompt_coverage(self.api, self.root, {}, value, 'CHR-001', 'S03')

    def test_all_cues_and_checks_survive_handoff(self):
        self.check(package())

    def test_selected_jewelry_cannot_disappear_from_prompt(self):
        value = package(); value['prompts'][0]['text'] = value['prompts'][0]['text'].replace(CUES['head_ear_neck'], '')
        with self.assertRaisesRegex(ValueError, 'dropped head_ear_neck cue'):
            self.check(value)

    def test_selected_jewelry_requires_acceptance_check(self):
        value = package(); value['acceptance_checks'] = [value['acceptance_checks'][0].replace(CUES['head_ear_neck'], '')]
        with self.assertRaisesRegex(ValueError, 'do not inspect designed head_ear_neck'):
            self.check(value)

    def test_every_prompt_alternative_must_keep_selected_details(self):
        value = package(); value['prompts'].append({'id': 'alternate', 'text': '省略了妆发饰的笼统婚纱'})
        with self.assertRaisesRegex(ValueError, 'dropped'):
            self.check(value)

    def test_old_v1_record_remains_readable_without_new_need_fields(self):
        cp.write_json(self.root / 'stage.json', {'schema_version': 'CharacterStageDesignV1'})
        self.check({'prompts': [], 'acceptance_checks': []})


class StateActivation(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root = Path(self.tmp.name)
        self.data = stage()
        planned = {name: {'status': 'inline'} for name in self.data['specialist_execution']}
        for _, (name, _) in phased.STATE_STYLING_SPECIALISTS.items():
            planned[name]['status'] = 'not_needed'
            self.data['specialist_execution'][name].update(
                task={'objective': '深化仪式状态可见细节', 'character_context': '已有批准身份，本场公开入场。',
                      'expected_result': '交付该部位明确的结构和可见提示词。', 'constraints': ['不更改批准脸型。']},
                state_activation_reason='基础身份阶段留空不代表当前婚礼仪式同样留空，本场需重新判断。')
        brief = {'specialist_plan': planned}; cp.write_json(self.root / 'brief.json', brief)
        self.state = {'records': {phased.key('design-brief', 'CHR-001'):
                      {'path': 'brief.json', 'sha256': cp.digest(brief)}}}

    def test_state_can_activate_base_not_needed_specialists(self):
        phased.validate_execution(cp, self.root, self.data, self.state, strict=False)

    def test_activation_requires_explicit_state_reason(self):
        del self.data['specialist_execution']['character-face-signature-design']['state_activation_reason']
        with self.assertRaisesRegex(ValueError, 'state_activation_reason'):
            phased.validate_execution(cp, self.root, self.data, self.state, strict=False)


if __name__ == '__main__':
    unittest.main()

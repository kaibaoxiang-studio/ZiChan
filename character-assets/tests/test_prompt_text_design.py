"""Actual no-file text-source boundary checks, not design-quality assertions."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_prompt_delivery as prompt


class FilelessTextDesign(unittest.TestCase):
    def setUp(self):
        self.design = ('梁砚当前设计第2稿。脸为长窄骨相，颧弓平缓，下颌略收；'
                       '发际平直，人物左侧分缝；后脑三层发片叠压，头顶长三厘米。'
                       '全身约七头身，肩髋比1.40。理由：46岁夜班维修工，话少而待人耐心。')
        self.inputs = {'request': '沿用当前第2稿，只给头像候选词。本次明确不要落任何文件，画幅必须1:1。',
                       'stage': 'avatar', 'delivery_mode': 'text', 'purpose': 'candidate',
                       'design_source': {'kind': 'task_text_design', 'text': self.design,
                                         'source_ref': '当前对话上一条：梁砚设计第2稿'}}
        self.content = ('1:1 单人头像，纪录片式真人写实。长窄脸，颧弓平缓，下颌略收；'
                        '发际平直，人物左边分缝，后脑以3层发片叠压，头顶长3厘米。')

    def test_actual_text_source_needs_no_file_or_project_and_does_not_claim_semantics(self):
        # The helper must not even read a nominal source file or project ledger.
        with (mock.patch.object(prompt.cp, 'read_json', side_effect=AssertionError('file read')),
              mock.patch.object(Path, 'write_text', side_effect=AssertionError('file write'))):
            result = prompt.validate_text(self.content, self.inputs)
        self.assertTrue(result['valid'])
        self.assertEqual(result['basis']['text_design_sha256'], hashlib.sha256(self.design.encode('utf-8')).hexdigest())
        self.assertEqual(result['basis']['source_ref'], self.inputs['design_source']['source_ref'])
        self.assertEqual(result['verification_scope'], 'current-text-design-binding-and-canvas')
        self.assertTrue(result['controller_semantic_review_required'])
        self.assertFalse(result['semantic_equivalence_proven_by_code'])
        self.assertFalse(result['design_maturity_proven_by_code'])
        self.assertFalse(result['source_locator_authenticated_by_code'])
        self.assertFalse(result['project_write_performed'])

    def test_story_age_and_body_outside_avatar_are_not_compelled_into_prompt(self):
        result = prompt.validate_text(self.content, self.inputs)
        self.assertTrue(result['valid'])
        self.assertNotIn('46', self.content)
        self.assertNotIn('1.40', self.content)
        self.assertEqual(result['selected_hard_guard_count'], 0)

    def test_stated_source_hash_is_checked_in_memory_on_exact_utf8_text(self):
        source = self.inputs['design_source']
        source['text_sha256'] = hashlib.sha256(self.design.encode('utf-8')).hexdigest()
        self.assertTrue(prompt.validate_text(self.content, self.inputs)['valid'])
        source['text'] += '\n改成中分。'
        with self.assertRaisesRegex(ValueError, 'SHA changed'):
            prompt.validate_text(self.content, self.inputs)

    def test_source_and_locator_must_be_actual_nonempty_text(self):
        for key in ('text', 'source_ref'):
            for value in (None, '', '  '):
                with self.subTest(key=key, value=value):
                    inputs = copy.deepcopy(self.inputs)
                    inputs['design_source'][key] = value
                    with self.assertRaises(ValueError):
                        prompt.validate_text(self.content, inputs)

    def test_only_explicit_text_mode_can_use_the_source(self):
        for mode in (None, 'files', 'discussion'):
            inputs = copy.deepcopy(self.inputs)
            if mode is None:
                inputs.pop('delivery_mode')
            else:
                inputs['delivery_mode'] = mode
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'explicit actual task exception'):
                prompt.validate_text(self.content, inputs)
        # Even a mode:text task cannot pass this source to the file validator.
        with self.assertRaisesRegex(ValueError, 'task_frozen_delivery'):
            prompt.validate(Path('/this-file-must-not-be-read.json'), self.inputs)

    def test_no_formal_project_id_parent_or_anchor_can_enter_this_branch(self):
        patches = ({'purpose': 'formal'}, {'purpose': 'production'}, {'project_root': '/missing-project'},
                   {'character_id': 'CHR-001'}, {'variant_id': 'base'}, {'project_id': 'P-001'},
                   {'parent_refs': {}}, {'anchor_images': {}}, {'design_basis': {}}, {'approved': True})
        for patch in patches:
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    prompt.validate_text(self.content, dict(self.inputs, **patch))
        for field in ('project_root', 'parent_refs', 'character_id', 'anchor_images', 'path', 'sha256'):
            inputs = copy.deepcopy(self.inputs)
            inputs['design_source'][field] = '/not-a-source-file'
            with self.subTest(source_field=field), self.assertRaisesRegex(ValueError, 'only accepts current prose'):
                prompt.validate_text(self.content, inputs)

    def test_explicit_canvas_still_rejects_default_or_inconsistent_text(self):
        with self.assertRaisesRegex(ValueError, 'must be 1:1'):
            prompt.validate_text(self.content.replace('1:1', '3:4'), self.inputs)
        inputs = copy.deepcopy(self.inputs)
        inputs['aspect_ratio'] = '3:4'
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            prompt.validate_text(self.content, inputs)

    def test_optional_visible_guards_protect_real_numeric_side_and_quantity_markers(self):
        inputs = copy.deepcopy(self.inputs)
        inputs['design_source']['preserve'] = ['人物左侧分缝', '后脑三层发片叠压，头顶长三厘米']
        result = prompt.validate_text(self.content, inputs)
        self.assertEqual(result['selected_hard_guard_count'], 2)
        self.assertEqual(result['verification_scope'], 'current-text-design-binding-canvas-and-selected-hard-markers')
        for before, after in (('人物左边', '人物右边'), ('3层', '2层'), ('3厘米', '2厘米')):
            with self.subTest(change=after), self.assertRaisesRegex(ValueError, 'hard'):
                prompt.validate_text(self.content.replace(before, after), inputs)

    def test_optional_guards_cannot_invent_source_or_claim_semantic_coverage(self):
        for preserve in ('发际平直', ['人物右侧分缝'], [''], [None]):
            inputs = copy.deepcopy(self.inputs)
            inputs['design_source']['preserve'] = preserve
            with self.subTest(preserve=preserve), self.assertRaisesRegex(ValueError, 'actual nonempty source excerpts'):
                prompt.validate_text(self.content, inputs)
        inputs = copy.deepcopy(self.inputs)
        inputs['design_source']['preserve'] = ['发际平直']
        # This known limitation is explicit: unmarked prose needs the controller's
        # actual meaning review. A code pass does not claim it retained this shape.
        report = prompt.validate_text(self.content.replace('发际平直', '弧形发际'), inputs)
        self.assertFalse(report['semantic_equivalence_proven_by_code'])
        self.assertTrue(report['controller_semantic_review_required'])


if __name__ == '__main__':
    unittest.main()

"""Frame requirements are actual task constraints, not stage-default suggestions."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
import character_project as cp
import verify_design_delivery as design
import verify_prompt_delivery as prompt
from export_prompt_text import write_prompt_text
from prompt_canvas import (canonical_ratio, explicit_canvas_ratio, resolve_canvas,
                           validate_canvas_text)
from prompt_fidelity import design_inventory
from test_prompt_frozen_fidelity import attach_review, make_frozen


class CanvasParsingBoundary(unittest.TestCase):
    def test_only_single_explicit_canvas_targets_are_parsed(self):
        for request in ('画幅必须1:1正方形', '画布宽高比设为 1：1。', 'aspect ratio must be 1:1',
                        '画幅1:1；画幅必须1:1正方形。', '特别指定画幅1:1且不生图'):
            with self.subTest(request=request):
                self.assertEqual(explicit_canvas_ratio(request), {'status': 'explicit', 'aspect_ratio': '1:1'})

    def test_body_measurements_are_not_frame_constraints(self):
        request = '身体约七头身，肩髋比要1.40，44.8/32.0＝1.40；上臂和前臂1:1。'
        self.assertEqual(explicit_canvas_ratio(request), {'status': 'absent'})
        self.assertEqual(resolve_canvas({'request': request}, 'avatar')['aspect_ratio'], '3:4')
        self.assertEqual(resolve_canvas({'request': request}, 'full_body')['aspect_ratio'], '9:16')
        self.assertEqual(resolve_canvas({'request': '画幅1:1；上臂前臂1:2'}, 'avatar')['aspect_ratio'], '1:1')

    def test_negative_or_conflicting_canvas_choices_require_controller_resolution(self):
        for request in ('画幅不要3:4', '不要用画幅3:4', '画幅不是1:1', '不要求画幅1:1',
                        '画幅1:1或3:4', '画幅1:1，画布3:4', 'aspect ratio must not be 3:4',
                        'do not use aspect ratio 3:4'):
            with self.subTest(request=request):
                self.assertEqual(explicit_canvas_ratio(request), {'status': 'needs_resolution'})
                with self.assertRaisesRegex(ValueError, 'controller-resolved'):
                    resolve_canvas({'request': request}, 'avatar')
                # A real task's controller-parsed field resolves ambiguity; the
                # helper does not claim to prove that interpretation itself.
                self.assertEqual(resolve_canvas({'request': request, 'aspect_ratio': '1:1'}, 'avatar')['aspect_ratio'], '1:1')

    def test_structured_constraint_is_binding_and_cannot_contradict_clear_raw_request(self):
        self.assertEqual(resolve_canvas({'request': '先交头像', 'aspect_ratio': '1:1'}, 'avatar')['aspect_ratio'], '1:1')
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            resolve_canvas({'request': '画幅必须1:1', 'aspect_ratio': '3:4'}, 'avatar')
        with self.assertRaisesRegex(ValueError, 'positive integer'):
            canonical_ratio('0:4')

    def test_current_actual_frame_wins_and_frozen_frame_only_fills_missing_constraint(self):
        frozen = {'request': '画幅必须1:1正方形'}
        self.assertEqual(resolve_canvas({'request': '按冻结稿给词'}, 'avatar', frozen)['aspect_ratio'], '1:1')
        current = {'request': '本次画幅改为3:4', 'aspect_ratio': '3:4'}
        self.assertEqual(resolve_canvas(current, 'avatar', frozen)['aspect_ratio'], '3:4')

    def test_body_ratio_cannot_mask_wrong_rendered_canvas(self):
        constraint = {'aspect_ratio': '1:1', 'source': 'task.aspect_ratio'}
        for wrong in ('3:4 单人头像，左右上臂比例1:1。', '画幅3:4。肩髋宽度1:1。',
                      '3:4竖版，另外画幅1:1正方形。', '人物肩髋1:1，但画布3:4。'):
            with self.subTest(wrong=wrong):
                with self.assertRaisesRegex(ValueError, 'Prompt canvas'):
                    validate_canvas_text(wrong, constraint)
        validate_canvas_text('画幅1:1正方形，身体约七头身，肩髋1.40。', constraint)
        validate_canvas_text('1:1 单人头像，前臂比为1:2。', constraint)


class FrozenCanvasContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.delivery, self.source = make_frozen(self.root / 'design')
        self.items = design_inventory(self.delivery, 'avatar')
        self.inputs = {'request': '按实际冻结稿给候选词', 'stage': 'avatar', 'design_source': self.source}
        self.package = {'schema_version': 'CharacterPromptPackageV1', 'purpose': 'candidate',
                        'stage': 'avatar', 'target_model': 'gpt-image-2.5', 'design_source': self.source,
                        'aspect_ratio': '3:4', 'reference_images': [], 'anchor_images': {},
                        'prompts': [{'id': 'main', 'text': '3:4 单人头像。' + '。'.join(self.items.values())}],
                        'acceptance_checks': ['核对真实设计的分缝、层数和长度。']}
        self.path = self.root / 'prompt-package.json'

    def write(self, package=None):
        package = package or self.package
        attach_review(package, self.items, self.source['sha256'])
        self.path.write_text(json.dumps(package, ensure_ascii=False), encoding='utf-8')
        write_prompt_text(package, self.root / '提示词.txt')

    def with_frame(self, ratio):
        package = copy.deepcopy(self.package)
        package['aspect_ratio'] = ratio
        package['prompts'][0]['text'] = package['prompts'][0]['text'].replace('3:4 单人头像', ratio + ' 单人头像')
        return package

    def update_frozen_frame(self, *, raw_request=None, aspect_ratio=None):
        inputs_path = Path(self.source['inputs_path'])
        frozen_inputs = cp.read_json(inputs_path)
        if raw_request is not None:
            frozen_inputs['request'] += '\n' + raw_request
        if aspect_ratio is not None:
            frozen_inputs['aspect_ratio'] = aspect_ratio
        self.delivery['data']['sources'] = design.source_bindings(frozen_inputs)
        path = Path(self.source['path'])
        path.write_text(json.dumps(self.delivery, ensure_ascii=False), encoding='utf-8')
        path.with_name('design.md').write_text(design.render(self.delivery), encoding='utf-8')
        inputs_path.write_text(json.dumps(frozen_inputs, ensure_ascii=False), encoding='utf-8')
        self.source.update(sha256=cp.digest(path), inputs_sha256=cp.digest(inputs_path))

    def test_raw_explicit_square_rejects_default_in_both_file_and_text_paths(self):
        self.inputs['request'] = '画幅必须1:1正方形'
        self.update_frozen_frame(raw_request='把已有稿生成头像提示词，画幅必须1:1正方形。')
        self.write()
        with self.assertRaisesRegex(ValueError, 'aspect_ratio must be 1:1'):
            prompt.validate(self.path, self.inputs)
        with self.assertRaisesRegex(ValueError, 'Prompt canvas must be 1:1'):
            prompt.validate_text(self.package['prompts'][0]['text'], dict(self.inputs, delivery_mode='text'))
        correct = self.with_frame('1:1')
        self.write(correct)
        self.assertTrue(prompt.validate(self.path, self.inputs)['valid'])
        self.assertTrue(prompt.validate_text(correct['prompts'][0]['text'], dict(self.inputs, delivery_mode='text'))['valid'])

    def test_structured_square_rejects_default_even_without_raw_canvas_words(self):
        self.inputs['aspect_ratio'] = '1:1'
        self.write()
        with self.assertRaisesRegex(ValueError, 'task.aspect_ratio'):
            prompt.validate(self.path, self.inputs)
        with self.assertRaisesRegex(ValueError, 'task.aspect_ratio'):
            prompt.validate_text(self.package['prompts'][0]['text'], dict(self.inputs, delivery_mode='text'))
        self.write(self.with_frame('1:1'))
        self.assertTrue(prompt.validate(self.path, self.inputs)['valid'])

    def test_frozen_design_task_frame_is_inherited_when_prompt_task_omits_it(self):
        self.update_frozen_frame(aspect_ratio='1:1')
        self.write()
        with self.assertRaisesRegex(ValueError, 'frozen_design.task.aspect_ratio'):
            prompt.validate(self.path, self.inputs)
        self.write(self.with_frame('1:1'))
        self.assertTrue(prompt.validate(self.path, self.inputs)['valid'])

    def test_package_square_cannot_hide_wrong_canvas_behind_incidental_body_ratio(self):
        self.inputs['aspect_ratio'] = '1:1'
        package = self.with_frame('1:1')
        package['prompts'][0]['text'] = package['prompts'][0]['text'].replace('1:1 单人头像', '3:4 单人头像') + '。前臂比例1:1。'
        self.write(package)
        with self.assertRaisesRegex(ValueError, 'Prompt canvas must be 1:1'):
            prompt.validate(self.path, self.inputs)

    def test_body_ratio_does_not_authorize_nondefault_avatar_canvas(self):
        self.inputs['request'] = '上臂前臂1:1，肩髋1.40，44.8/32.0=1.40，身体约七头身。'
        self.write(self.with_frame('1:1'))
        with self.assertRaisesRegex(ValueError, 'aspect_ratio must be 3:4'):
            prompt.validate(self.path, self.inputs)

    def test_ordinary_request_preserves_default_canvas(self):
        self.write()
        result = prompt.validate(self.path, self.inputs)
        self.assertEqual(result['aspect_ratio'], '3:4')
        self.assertEqual(result['aspect_ratio_source'], 'stage_default')
        self.assertTrue(prompt.validate_text(self.package['prompts'][0]['text'], dict(self.inputs, delivery_mode='text'))['valid'])


if __name__ == '__main__':
    unittest.main()

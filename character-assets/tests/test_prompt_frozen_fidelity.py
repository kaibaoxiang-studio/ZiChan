"""Real frozen-design validation and fidelity checks; no model or visual claims."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import character_project as cp
import verify_design_delivery as design
import verify_prompt_delivery as prompt
from export_prompt_text import render_prompt_text, write_prompt_text
from prompt_fidelity import content_hash, design_inventory, validate_fidelity
from prompt_fixture import make_avatar_project


def inventory(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()}


def attach_review(package, source_inventory, source_sha, spans=None):
    """Synthetic receipt only. It never represents a model's actual review."""
    spans = spans or {}
    package['fidelity_review'] = {
        'schema_version': 'PromptFidelityReviewV1', 'source_sha256': source_sha,
        'prompt_sha256': content_hash(package['prompts']),
        'semantic_review': {'reviewer': 'controller', 'verdict': 'pass', 'unresolved': [],
                            'notes': 'Synthetic review receipt: compare source mappings and objective markers; not evidence of design quality.'},
        'coverage': [{'prompt_id': p['id'], 'detail_id': key, 'span': spans.get(key, value)}
                     for p in package['prompts'] for key, value in source_inventory.items()]}


def make_frozen(folder, project=None):
    folder.mkdir(parents=True, exist_ok=True)
    original = '梁砚的已给发型：平直发际，人物左侧分缝；右前发片贴颅，后脑三层发片叠压；头顶长三厘米，黑发混少量灰发。'
    inputs = {'request': '只依据这份成熟发型稿试改候选，不声称全剧设计。原稿：' + original,
              'requested_dimensions': ['hair'], 'design_origin': 'provided', 'purpose': 'candidate'}
    refs = None
    if project:
        state = cp.read_json(project / 'project.json')
        key = 'stage-design:identity:CHR-TEST:base'
        refs = {key: state['records'][key]['sha256']}
        inputs.update(project_root=str(project), character_id='CHR-TEST', parent_refs=refs)
    delivery = {'schema_version': 'CharacterDesignDeliveryV1', 'kind': 'standalone', 'scope': 'requested',
                'data': {'schema_version': 'StandaloneCharacterDesignV1', 'scope': 'requested',
                    'requested_dimensions': ['hair'], 'subject': {'name': '梁砚', 'local_key': 'liang-yan-draft'},
                    'sources': design.source_bindings(inputs), 'understanding': {'material_scope': 'Only the supplied biography and mature hair design.'},
                    'design_thesis': '保留原脸，只压低后脑与后颈，维护普通中年人物的完整发型。',
                    'provenance': {'kind': 'provided', 'original_text': original},
                    'payload': {'morphology': 'human', 'visual_details': {'hair': {
                        'hairline_part': '平直发际，人物左侧分缝',
                        'volume_flow': '右前发片贴颅，后脑三层发片叠压',
                        'length_texture_color': '头顶长三厘米，黑发混少量灰发'}}},
                    'specialist_execution': {}, 'unresolved': [], 'deferred_dimensions': []}}
    if refs:
        delivery['data']['parent_refs'] = refs
    path = folder / 'design-result.json'
    path.write_text(json.dumps(delivery, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (folder / 'design.md').write_text(design.render(delivery), encoding='utf-8')
    input_path = folder / 'design-inputs.json'
    input_path.write_text(json.dumps(inputs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    source = {'kind': 'task_frozen_delivery', 'path': str(path), 'sha256': cp.digest(path),
              'inputs_path': str(input_path), 'inputs_sha256': cp.digest(input_path)}
    if refs:
        source.update(project_root=str(project), parent_refs=refs)
    return delivery, source


class FrozenPromptDelivery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.delivery, self.source = make_frozen(self.root / 'design')
        self.items = design_inventory(self.delivery, 'avatar')
        self.package = {'schema_version': 'CharacterPromptPackageV1', 'purpose': 'candidate',
                        'stage': 'avatar', 'target_model': 'gpt-image-2.5', 'design_source': self.source,
                        'reference_images': [], 'anchor_images': {}, 'aspect_ratio': '3:4',
                        'prompts': [{'id': 'main', 'text': '3:4 单人头像。' + '。'.join(self.items.values())}],
                        'acceptance_checks': ['核左分缝、右前发片、后脑三层与头顶三厘米。']}
        attach_review(self.package, self.items, self.source['sha256'])
        self.inputs = {'request': '按实际冻结的发型候选交JSON与TXT，不生图、不改变正式工程。',
                       'stage': 'avatar', 'design_source': copy.deepcopy(self.source)}
        self.package_path = self.root / 'prompt-package.json'

    def write(self, package=None):
        package = package or self.package
        self.package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        write_prompt_text(package, self.root / '提示词.txt')

    def test_real_independent_candidate_needs_no_project_or_formal_id(self):
        self.write()
        before = inventory(self.root)
        result = prompt.validate(self.package_path, self.inputs)
        self.assertTrue(result['valid'])
        self.assertFalse(result['approved'])
        self.assertFalse(result['semantic_equivalence_proven_by_code'])
        self.assertEqual(inventory(self.root), before)
        self.assertFalse((self.root / 'project.json').exists())

    def test_synonym_join_and_chinese_numeric_equivalence_are_allowed(self):
        package = copy.deepcopy(self.package)
        spans = {'visual_details.hair.hairline_part': '发际呈平直形，分缝在人物左边',
                 'visual_details.hair.volume_flow': '右前发片贴着头形，后脑以3层发片叠压',
                 'visual_details.hair.length_texture_color': '头顶长度3厘米，黑发中只混少量灰发'}
        # Keep an objectively recognisable side+part pair while allowing prose order.
        spans['visual_details.hair.hairline_part'] = '发际呈平直形，人物左边分缝'
        package['prompts'][0]['text'] = '3:4 单人头像。' + '，'.join(spans.values())
        attach_review(package, self.items, self.source['sha256'], spans)
        self.write(package)
        self.assertTrue(prompt.validate(self.package_path, self.inputs)['valid'])

    def test_missing_selected_structure_is_rejected_even_with_pass_receipt(self):
        package = copy.deepcopy(self.package)
        removed = package['fidelity_review']['coverage'].pop()
        package['prompts'][0]['text'] = package['prompts'][0]['text'].replace(removed['span'], '')
        package['fidelity_review']['prompt_sha256'] = content_hash(package['prompts'])
        self.write(package)
        with self.assertRaisesRegex(ValueError, 'dropped selected'):
            prompt.validate(self.package_path, self.inputs)

    def test_unknown_mapping_cannot_redefine_inventory(self):
        package = copy.deepcopy(self.package)
        package['fidelity_review']['coverage'][0]['detail_id'] = 'generic-nice-hair'
        self.write(package)
        with self.assertRaisesRegex(ValueError, 'unknown or duplicate'):
            prompt.validate(self.package_path, self.inputs)

    def test_changed_prompt_invalidates_prior_semantic_review(self):
        package = copy.deepcopy(self.package)
        package['prompts'][0]['text'] += '换成右分缝。'
        self.write(package)
        with self.assertRaisesRegex(ValueError, 'prompt content changed'):
            prompt.validate(self.package_path, self.inputs)

    def test_changed_frozen_design_or_actual_inputs_are_rejected(self):
        self.write()
        Path(self.source['inputs_path']).write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Frozen inputs_path changed'):
            prompt.validate(self.package_path, self.inputs)

    def test_package_cannot_swap_frozen_source(self):
        package = copy.deepcopy(self.package)
        package['design_source']['sha256'] = '0' * 64
        self.write(package)
        with self.assertRaisesRegex(ValueError, 'design_source differs'):
            prompt.validate(self.package_path, self.inputs)

    def test_false_project_root_never_falls_back_to_standalone(self):
        self.write()
        with self.assertRaisesRegex(ValueError, 'real character project'):
            prompt.validate(self.package_path, dict(self.inputs, project_root=str(self.root / 'missing')))

    def test_standalone_cannot_invent_chr_id_or_approved_status(self):
        for patch in ({'character_id': 'CHR-001'}, {'approved': True}, {'purpose': 'production'}):
            with self.subTest(patch=patch):
                package = copy.deepcopy(self.package)
                package.update(patch)
                self.write(package)
                with self.assertRaises(ValueError):
                    prompt.validate(self.package_path, self.inputs)

    def test_default_files_require_exact_internal_txt_and_text_exception_is_explicit(self):
        self.write()
        (self.root / '提示词.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'real same-source'):
            prompt.validate(self.package_path, self.inputs)
        self.assertTrue(prompt.validate(self.package_path, dict(self.inputs, delivery_mode='text'))['valid'])
        (self.root / '提示词.txt').write_text('短发普通人', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'exact UTF-8 export'):
            prompt.validate(self.package_path, self.inputs)

    def test_dialogue_only_prompt_checks_real_frozen_source_and_does_not_forge_semantic_receipt(self):
        content = self.package['prompts'][0]['text']
        inputs = dict(self.inputs, delivery_mode='text')
        report = prompt.validate_text(content, inputs)
        self.assertTrue(report['valid'])
        self.assertTrue(report['controller_semantic_review_required'])
        self.assertFalse(report['semantic_equivalence_proven_by_code'])
        with self.assertRaisesRegex(ValueError, 'explicit actual task exception'):
            prompt.validate_text(content, self.inputs)
        with self.assertRaisesRegex(ValueError, 'real character project'):
            prompt.validate_text(content, dict(inputs, project_root=str(self.root / 'bad-project')))
        with self.assertRaisesRegex(ValueError, 'hard'):
            prompt.validate_text(content.replace('三层', '两层'), inputs)
        Path(self.source['path']).write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Frozen path changed'):
            prompt.validate_text(content, inputs)

    def test_explicit_source_cannot_hide_failed_design_validation(self):
        value = json.loads(Path(self.source['path']).read_text())
        del value['data']['payload']['visual_details']['hair']['volume_flow']
        Path(self.source['path']).write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        Path(self.source['path']).with_name('design.md').write_text(design.render(value), encoding='utf-8')
        self.source['sha256'] = cp.digest(Path(self.source['path']))
        self.package['design_source'] = self.source
        self.inputs['design_source'] = copy.deepcopy(self.source)
        self.write()
        with self.assertRaisesRegex(ValueError, 'volume_flow'):
            prompt.validate(self.package_path, self.inputs)

    def test_trial_does_not_mutate_active_and_parent_changes_invalidate_candidate(self):
        project = self.root / 'project'
        state, _, _ = make_avatar_project(project)
        delivery, source = make_frozen(self.root / 'trial', project)
        items = prompt.frozen_inventory(delivery, 'avatar', source)
        package = copy.deepcopy(self.package)
        package['design_source'] = source
        package['prompts'][0]['text'] = '3:4 单人头像。' + '。'.join(items.values())
        attach_review(package, items, source['sha256'])
        self.write(package)
        inputs = dict(self.inputs, design_source=source, project_root=str(project))
        before = inventory(project)
        self.assertTrue(prompt.validate(self.package_path, inputs)['valid'])
        self.assertEqual(inventory(project), before)
        # Source-bound trial must also carry unchanged face/skin parent structure.
        self.assertTrue(any(key.startswith('visual_details.face.') for key in items))
        bad = copy.deepcopy(package)
        bad['fidelity_review']['coverage'] = [row for row in bad['fidelity_review']['coverage']
                                              if not row['detail_id'].startswith('visual_details.face.')]
        for key, value in items.items():
            if key.startswith('visual_details.face.'):
                bad['prompts'][0]['text'] = bad['prompts'][0]['text'].replace(value, '')
        bad['fidelity_review']['coverage'] = [row for row in bad['fidelity_review']['coverage']
                                              if row['span'] in bad['prompts'][0]['text']]
        bad['fidelity_review']['prompt_sha256'] = content_hash(bad['prompts'])
        self.write(bad)
        with self.assertRaisesRegex(ValueError, 'dropped selected'):
            prompt.validate(self.package_path, inputs)
        self.write(package)
        key = 'stage-design:identity:CHR-TEST:base'
        state['records'][key]['sha256'] = 'f' * 64
        (project / 'project.json').write_text(json.dumps(state), encoding='utf-8')
        with self.assertRaises(ValueError):
            prompt.validate(self.package_path, inputs)


class HardMarkerFidelity(unittest.TestCase):
    def check(self, original, rewritten):
        package = {'prompts': [{'id': 'main', 'text': rewritten}]}
        attach_review(package, {'detail': original}, 'd' * 64, {'detail': rewritten})
        return validate_fidelity(package, {'detail': original}, 'd' * 64)

    def test_numeric_left_right_quantity_and_removed_state_cannot_change(self):
        pairs = [('肩髋宽度比为1.40倍', '肩髋宽度比为1.08倍'),
                 ('人物左耳一枚耳钉', '人物右耳一枚耳钉'),
                 ('三片叠压衣片', '两片叠压衣片'),
                 ('项链已取下', '佩戴项链')]
        for source, text in pairs:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, 'hard|state'):
                    self.check(source, text)

    def test_selected_present_object_cannot_be_removed(self):
        with self.assertRaisesRegex(ValueError, 'hard|state'):
            self.check('人物左耳一枚耳钉', '人物左耳一枚耳钉已取下')

    def test_unknown_state_paraphrase_is_left_to_real_semantic_review_not_guessed_positive(self):
        self.assertFalse(self.check('不加可卸妆面', '素面朝天，保留原生肤色')['semantic_equivalence_proven_by_code'])
        self.assertFalse(self.check('不添加妆面', '没有可卸妆面')['semantic_equivalence_proven_by_code'])

    def test_exact_phrase_inside_explicit_removal_is_not_automatic_fidelity(self):
        package = {'prompts': [{'id': 'main', 'text': '避免圆钝下颌。'}]}
        attach_review(package, {'face': '圆钝下颌'}, 'd' * 64, {'face': '避免圆钝下颌。'})
        package['fidelity_review']['coverage'] = []
        with self.assertRaisesRegex(ValueError, 'dropped selected'):
            validate_fidelity(package, {'face': '圆钝下颌'}, 'd' * 64)
        package['fidelity_review']['coverage'] = [{'prompt_id': 'main', 'detail_id': 'face', 'span': '避免圆钝下颌。'}]
        with self.assertRaisesRegex(ValueError, 'negates'):
            validate_fidelity(package, {'face': '圆钝下颌'}, 'd' * 64)

    def test_code_only_review_receipt_and_fabricated_spans_are_rejected(self):
        package = {'prompts': [{'id': 'main', 'text': '圆钝下颌'}]}
        attach_review(package, {'face': '圆钝下颌'}, 'd' * 64)
        package['fidelity_review']['semantic_review']['reviewer'] = 'schema-validator'
        with self.assertRaisesRegex(ValueError, 'controller semantic review'):
            validate_fidelity(package, {'face': '圆钝下颌'}, 'd' * 64)
        package['fidelity_review']['semantic_review']['reviewer'] = 'controller'
        package['fidelity_review']['coverage'][0]['span'] = '正文根本没有这个片段'
        with self.assertRaisesRegex(ValueError, 'actual prompt text span'):
            validate_fidelity(package, {'face': '圆钝下颌'}, 'd' * 64)

    def test_source_inventory_keeps_body_masses_views_and_costume_construction(self):
        payload = {'visual_details': {'body': {'frame': '七头身，身体结构。'}},
                   'body_form': {'masses': {'ribcage': '胸廓为前后较厚的卵形体块', 'basis': 'irrelevant reason'},
                                 'views': {'side': '侧面胸骨略前于腹壁'},
                                 'action_check': {'stance': '双膝松开，重心落在足弓',
                                                  'script_action': '冲向公交并拥抱女儿', 'test_status': 'not_tested'}},
                   'costume_direction': {'front_structure': '三片前衣片在右腰叠压',
                                         'back_structure': '后中一道纵褶连向腰线',
                                         'cut_and_fastening': '左腰两枚小扁扣闭合',
                                         'material_behavior': '外层薄呢布自然垂落',
                                         'narrative_function': 'explanatory story metadata'}}
        body = design_inventory({'payload': payload}, 'full_body')
        self.assertEqual(body['body_form.masses.ribcage'], '胸廓为前后较厚的卵形体块')
        self.assertIn('body_form.views.side', body)
        self.assertIn('body_form.action_check.stance', body)
        self.assertIn('costume_direction.front_structure', body)
        self.assertFalse(any('test_status' in key or 'script_action' in key or 'basis' in key for key in body))
        clothes = design_inventory({'payload': payload}, 'execution')
        self.assertIn('costume_direction.back_structure', clothes)
        self.assertIn('costume_direction.cut_and_fastening', clothes)
        self.assertIn('costume_direction.material_behavior', clothes)
        self.assertFalse(any('narrative_function' in key for key in clothes))
        package = {'prompts': [{'id': 'main', 'text': '；'.join(clothes.values())}]}
        attach_review(package, clothes, 'd' * 64)
        package['fidelity_review']['coverage'] = [row for row in package['fidelity_review']['coverage']
                                                 if row['detail_id'] != 'costume_direction.cut_and_fastening']
        package['prompts'][0]['text'] = package['prompts'][0]['text'].replace(clothes['costume_direction.cut_and_fastening'], '')
        package['fidelity_review']['prompt_sha256'] = content_hash(package['prompts'])
        with self.assertRaisesRegex(ValueError, 'dropped selected'):
            validate_fidelity(package, clothes, 'd' * 64)


class FormalFidelityCompatibility(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.state, self.package, self.inputs = make_avatar_project(self.project)
        record = self.state['records']['stage-design:identity:CHR-TEST:base']
        self.design = cp.read_json(self.project / record['path'])
        self.sha = record['sha256']
        self.items = design_inventory(self.design, 'avatar')

    def write(self, package):
        path = self.root / 'prompt-package.json'
        path.write_text(json.dumps(package, ensure_ascii=False), encoding='utf-8')
        write_prompt_text(package, self.root / '提示词.txt')
        return path

    def rewritten(self):
        package = copy.deepcopy(self.package)
        old = '偏长的圆角方脸'
        new = '脸为偏长圆角方形'
        package['prompts'][0]['text'] = package['prompts'][0]['text'].replace(old, new)
        spans = {}
        for key, value in self.items.items():
            rewritten = value.replace(old, new)
            if rewritten not in package['prompts'][0]['text']:
                package['prompts'][0]['text'] += '\n' + rewritten
            spans[key] = rewritten
        attach_review(package, self.items, self.sha, spans)
        return package

    def test_explicit_new_formal_review_allows_synonym_without_changing_approved_source(self):
        package = self.rewritten()
        before = inventory(self.project)
        self.assertTrue(prompt.validate(self.write(package), self.inputs)['valid'])
        self.assertEqual(inventory(self.project), before)

    def test_without_new_review_legacy_contract_still_requires_original_cues(self):
        package = self.rewritten()
        package.pop('fidelity_review')
        with self.assertRaisesRegex(ValueError, 'dropped'):
            prompt.validate(self.write(package), self.inputs)

    def test_formal_text_exception_resolves_approved_basis_and_rejects_lost_approval(self):
        inputs = dict(self.inputs, delivery_mode='text')
        content = self.package['prompts'][0]['text']
        before = inventory(self.project)
        result = prompt.validate_text(content, inputs)
        self.assertTrue(result['valid'])
        self.assertTrue(result['controller_semantic_review_required'])
        self.assertEqual(inventory(self.project), before)
        self.state['records']['stage-design:identity:CHR-TEST:base']['approval'] = None
        (self.project / 'project.json').write_text(json.dumps(self.state), encoding='utf-8')
        with self.assertRaises(ValueError):
            prompt.validate_text(content, inputs)

    def test_review_does_not_allow_unmapped_rewritten_formal_detail(self):
        package = self.rewritten()
        package['fidelity_review']['coverage'] = [row for row in package['fidelity_review']['coverage']
                                                 if row['detail_id'] != 'prompt_detail_contract.face.type']
        with self.assertRaisesRegex(ValueError, 'dropped selected'):
            prompt.validate(self.write(package), self.inputs)

    def test_exact_retained_details_need_no_repeated_receipt_but_rewrites_still_need_mapping(self):
        package = self.rewritten()
        body = package['prompts'][0]['text']
        package['fidelity_review']['coverage'] = [row for row in package['fidelity_review']['coverage']
                                                 if self.items[row['detail_id']] not in body]
        self.assertLess(len(package['fidelity_review']['coverage']), len(self.items))
        report = prompt.validate(self.write(package), self.inputs)
        self.assertTrue(report['valid'])
        # This is still the synonym, rather than an accidental literal fallback.
        self.assertNotIn('偏长的圆角方脸', body)
        package['fidelity_review']['coverage'] = []
        with self.assertRaisesRegex(ValueError, 'dropped selected'):
            prompt.validate(self.write(package), self.inputs)


if __name__ == '__main__':
    unittest.main()

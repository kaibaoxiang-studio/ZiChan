"""Synthetic route/coverage/legacy-pack tests; never production approvals."""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import character_project as cp
import ensemble_assets as ensemble

STYLE = '当代真人影视写实风格，冷灰环境与自然材料分层'
FIELDS = ('face_and_hair', 'body_and_posture', 'costume_front', 'costume_back',
          'color_and_material', 'prop_and_action')
LAYOUT = {'top_left': 'front_face', 'top_right': 'three_quarter_face_45',
          'bottom_left': 'headless_enlarged_front_costume',
          'bottom_right': 'complete_back_head_to_shoes'}


def human_design():
    return {'world_style_translation': STYLE,
            'face_and_hair': '低颧宽下颌，前发从人物右额向左后收束',
            'body_and_posture': '略宽的胸腔与窄胯，重心稳在右脚中部',
            'costume_front': '立领前中双排斜扣，右肩拼片跨到后背',
            'costume_back': '后中箱褶收在腰线上方，袖口双层返折',
            'color_and_material': '藏蓝细斜纹棉布与哑光金属暗扣分区',
            'prop_and_action': '仅左手托登记板，右手垂下，登记板不转给他人'}


def visible_cues(design):
    if design.get('morphology', 'human') in {'human', 'humanoid'}:
        return [design[field] for field in FIELDS]
    return [design[field] for field in ('body_and_posture', 'color_and_material', 'prop_and_action')] + [
        *design['morphology_details'].values(), design['execution_layout']['description']]


def extra_prompt(design):
    human = design.get('morphology', 'human') in {'human', 'humanoid'}
    cues = visible_cues(design)
    return {'schema_version': 'CharacterPromptPackageV1', 'character_id': 'CHR-EXTRA',
            'variant_id': 'S01', 'variant_name': '执勤', 'stage': 'execution',
            'target_model': 'gpt-image-2.5', 'morphology': design.get('morphology', 'human'),
            'anchor_images': {}, 'reference_images': [], 'aspect_ratio': '9:16',
            'layout': copy.deepcopy(LAYOUT if human else design['execution_layout']),
            'design_basis': {'records': {}},
            'prompts': [{'id': 'main', 'text': '9:16，' + ('正脸、45°、无头服装、背面。' if human else '真实非人形态单图。') +
                         STYLE + '。' + '。'.join(cues)}],
            'acceptance_checks': ['9:16，核项目风格。' + ('核正脸、45°、无头服装、背面与服饰。' if human else '核实际形体、结构与附着。'), *cues]}


def group_design():
    return {'member_count': 2, 'world_style_translation': STYLE, 'members': [
        {'slot': '左一', 'body_and_posture': '宽胸直立、左脚略前的方形体块',
         'face_and_hair': '低颧方脸与灰白贴头短发', 'costume_structure': '右肩双层护片扣在前中领座',
         'color_and_material': '浅灰粗棉和暗铜肩扣分层', 'action_or_prop': '仅左手拿红纸卷'},
        {'slot': '右一', 'body_and_posture': '窄胸微前倾、双脚并列的长条体块',
         'face_and_hair': '长椭圆脸与深色微卷短发', 'costume_structure': '腰带在人物左侧交叠斜扣',
         'color_and_material': '深蓝短绒织物和哑黑腰带', 'action_or_prop': '双手共同托住一只铜盘'}]}


def group_prompt(design):
    cues = [member[field] for member in design['members'] for field in
            ('body_and_posture', 'face_and_hair', 'costume_structure', 'color_and_material', 'action_or_prop')]
    return {'morphology': 'group', 'anchor_images': {}, 'aspect_ratio': '16:9',
            'aspect_ratio_basis': '双人并排保持全身可辨',
            'layout': {'type': 'ensemble_lineup', 'single_canvas': True, 'full_body': True,
                       'member_count': 2, 'ordered_slots': ['左一', '右一']},
            'prompts': [{'id': 'main', 'text': '16:9，2人全身，从左一到右一。风格：' + STYLE + '。' + '。'.join(cues)}],
            'acceptance_checks': ['核16:9人数全身顺序风格', *cues]}


def make_project(root, morphology='human'):
    root.mkdir(parents=True)
    screenplay = {'episodes': [{'scenes': [{'blocks': [
        {'type': 'dialogue', 'speaker': '执勤者', 'text': '请登记。', 'source_refs': ['S1:B1']}]}]}]}
    source = root / 'inputs/screenplay.json'
    source.parent.mkdir()
    cp.write_json(source, screenplay)
    state = {'schema_version': cp.SCHEMA, 'project_id': 'SYNTHETIC-EXTRA-TEST',
             'pipeline_version': 3, 'design_progression': 'phased', 'revision': 1,
             'pending_impact': None, 'inputs': {'screenplay': {'path': 'inputs/screenplay.json', 'sha256': cp.digest(source)}},
             'roster': [{'id': 'CHR-EXTRA', 'name': '执勤者', 'aliases': [], 'tier': '群演',
                         'states': [{'id': 'S01', 'name': '执勤', 'evidence': [{'text': '执勤者说请登记。', 'source_refs': ['S1:B1']}]}]}],
             'records': {}, 'images': [], 'reviews': {}, 'references': [], 'decisions': []}

    def store(key, data):
        path = root / 'records' / (key.replace(':', '_') + '.json')
        cp.write_json(path, data)
        sha = cp.digest(data)
        state['records'][key] = {'path': str(path.relative_to(root)), 'sha256': sha, 'stale': False,
            'approval': {'operator': 'test:synthetic-only', 'sha256': sha}}
        return sha

    store('script-context', {'schema_version': 'ScriptContextV1', 'source_sha256': cp.digest(source)})
    store('visual-bible', {'schema_version': 'ProjectVisualBibleV1', 'style': {'medium': STYLE}})
    store('cast-plan', {'schema_version': 'CastPlanV1', 'characters': [{'id': 'CHR-EXTRA', 'design_distinction': '测试专用'}]})
    design = human_design()
    design.update(schema_version='SpeakingExtraDesignV1', character_id='CHR-EXTRA', variant_id='S01',
                  narrative_function='在门岗说一句话的测试群演', spoken_line='请登记。',
                  parent_refs={key: state['records'][key]['sha256'] for key in ('script-context', 'visual-bible', 'cast-plan')},
                  source_refs=['S1:B1'], evidence_status='creative_choice', new_lore_policy='none', unresolved=[])
    if morphology != 'human':
        design['morphology'] = morphology
    if morphology == 'nonhuman':
        for field in ('face_and_hair', 'costume_front', 'costume_back'):
            design.pop(field)
        design.update(morphology_details={'identity_structure': '低矮椭圆机身与单个矩形摄像头沿中轴连接',
                                          'front_back_structure': '前方双传感器接入侧护壳，后盖沿中线开合'},
                      body_and_posture='四轮接地，前轮外展半轮宽，机身保持水平',
                      color_and_material='灰色磨砂金属护壳配黑色橡胶轮胎',
                      prop_and_action='正面托架平放一块登记板，摄像头朝向来访者',
                      execution_layout={'type': 'single_canvas_views',
                                        'description': '同一张竖版画布展示机器的正面全形与完整背面，不加入人类脸部或衣装格'})
    ensemble.validate_extra(cp, root, state, design, 'CHR-EXTRA', 'S01')
    sha = store('extra-design:CHR-EXTRA:S01', design)
    cp.write_json(root / 'project.json', state)
    return state, design, sha, store


def add_approved_image(root, state, package, store):
    prompt_sha = store('prompt-package:execution:CHR-EXTRA:S01', package)
    def chunk(tag, payload):
        return struct.pack('!I', len(payload)) + tag + payload + struct.pack('!I', zlib.crc32(tag + payload) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 9, 16, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress((b'\x00' + b'\x88' * 27) * 16)) + chunk(b'IEND', b'')
    image_path = root / 'images/synthetic-extra.png'
    image_path.parent.mkdir()
    image_path.write_bytes(png)
    review_path = root / 'reviews/synthetic-extra.json'
    review = {'schema_version': 'CharacterImageReviewV1', 'stage': 'execution', 'verdict': 'pass',
              'synthetic_test_only': True, 'image_sha256': cp.digest(image_path)}
    cp.write_json(review_path, review)
    state['reviews']['synthetic-extra'] = {'path': str(review_path.relative_to(root)), 'sha256': cp.digest(review)}
    state['images'].append({'id': 'synthetic-extra', 'character_id': 'CHR-EXTRA', 'variant_id': 'S01',
        'stage': 'execution', 'purpose': 'production', 'path': str(image_path.relative_to(root)),
        'sha256': cp.digest(image_path), 'prompt_sha256': prompt_sha, 'stale': False,
        'approval': {'operator': 'test:synthetic-only', 'image_sha256': cp.digest(image_path), 'review_sha256': cp.digest(review)}})
    cp.write_json(root / 'project.json', state)


class EnsembleCoverageTests(unittest.TestCase):
    def test_extra_keeps_every_design_field_in_every_candidate(self):
        design = human_design()
        ensemble.validate_extra_prompt(cp, extra_prompt(design), design)
        for cue in visible_cues(design):
            with self.subTest(cue=cue):
                package = extra_prompt(design)
                package['prompts'].append({'id': 'short', 'text': package['prompts'][0]['text'].replace(cue, '')})
                with self.assertRaisesRegex(ValueError, 'dropped approved'):
                    ensemble.validate_extra_prompt(cp, package, design)

    def test_extra_checks_must_cover_the_selected_design(self):
        design = human_design()
        package = extra_prompt(design)
        package['acceptance_checks'].remove(design['costume_back'])
        with self.assertRaisesRegex(ValueError, 'do not inspect approved costume_back'):
            ensemble.validate_extra_prompt(cp, package, design)

    def test_group_keeps_each_members_design_and_prop_owner(self):
        design = group_design()
        ensemble.validate_prompt(cp, group_prompt(design), design)
        for member in design['members']:
            for field in ('body_and_posture', 'face_and_hair', 'costume_structure', 'color_and_material', 'action_or_prop'):
                with self.subTest(slot=member['slot'], field=field):
                    package = group_prompt(design)
                    package['prompts'][0]['text'] = package['prompts'][0]['text'].replace(member[field], '')
                    with self.assertRaisesRegex(ValueError, 'dropped approved'):
                        ensemble.validate_prompt(cp, package, design)

    def test_group_style_and_checks_apply_to_all_candidates(self):
        design = group_design()
        package = group_prompt(design)
        package['prompts'].append({'id': 'wrong-style', 'text': package['prompts'][0]['text'].replace(STYLE, '通用卡通风格')})
        with self.assertRaisesRegex(ValueError, 'Each group prompt'):
            ensemble.validate_prompt(cp, package, design)
        package = group_prompt(design)
        package['acceptance_checks'].remove(design['members'][1]['action_or_prop'])
        with self.assertRaisesRegex(ValueError, 'do not inspect approved'):
            ensemble.validate_prompt(cp, package, design)

    def test_script_count_inside_display_name_and_suffix(self):
        for name, text, count in [('三个小纸人', '三个小纸人围着桌上的五张罚款单。', 3),
                                  ('武士群像', '十二名武士站在殿门外。', 12),
                                  ('执勤者群演', '执勤者共有2名，旁边有7个箱子。', 2)]:
            with self.subTest(name=name):
                row = {'name': name, 'states': [{'id': 'S01', 'evidence': [{'text': text}]}]}
                self.assertEqual(ensemble._script_count(row, variant='S01'), count)

    def test_count_conflict_is_not_replaced_by_representative_choice(self):
        row = {'name': '三个小纸人', 'states': [{'id': 'S01', 'evidence': [{'text': '三个小纸人坐下。'}, {'text': '四个小纸人站起。'}]}]}
        with self.assertRaisesRegex(ValueError, 'Conflicting explicit group counts'):
            ensemble._script_count(row, variant='S01')

    def test_full_chinese_quantity_is_not_read_as_its_suffix(self):
        for token, expected in [('一百二十', 120), ('一百零三', 103), ('三千', 3000),
                                ('一万零三', 10003), ('两万三千', 23000)]:
            with self.subTest(token=token):
                row = {'name': '武士群像', 'states': [{'evidence': [{'text': token + '名武士站在宫门前，旁边有7只箱子。'}]}]}
                self.assertEqual(ensemble._script_count(row), expected)

    def test_approximate_or_bounded_quantity_is_not_script_explicit(self):
        for text in ('约三名武士等在门前。', '大约有三名武士。', '武士三名左右。',
                     '三名武士左右。', '三名左右的武士。', '数千名武士。', '至少三名武士。'):
            with self.subTest(text=text):
                row = {'name': '武士群像', 'states': [{'evidence': [{'text': text}]}]}
                self.assertIsNone(ensemble._script_count(row))
        row = {'name': '三个小纸人', 'states': [{'evidence': [{'text': '约三个小纸人。'}]}]}
        self.assertIsNone(ensemble._script_count(row))

    def test_count_uses_alias_and_selected_state_not_unrelated_numbers(self):
        row = {'name': '宫门执勤组', 'aliases': ['武士'], 'states': [
            {'id': 'S01', 'evidence': [{'text': '三名武士拿着8只碗。'}]},
            {'id': 'S02', 'evidence': [{'text': '两名武士持剑。'}]}]}
        self.assertEqual(ensemble._script_count(row, variant='S01'), 3)
        self.assertEqual(ensemble._script_count(row, variant='S02'), 2)
        self.assertIsNone(ensemble._script_count({'name': '武士群像', 'states': [{'evidence': [{'text': '武士旁有8只碗。'}]}]}))

    def test_nonhuman_robot_and_animal_submit_without_human_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            for label in ('robot', 'animal'):
                root = Path(folder) / label
                state, design, sha, _ = make_project(root, 'nonhuman')
                if label == 'animal':
                    design['morphology_details'] = {'identity_structure': '短吻犬科头连接宽厚颈肩，左耳尖有一撮黑毛',
                                                    'front_back_structure': '四足胸腹弧线自然衔接，背面保留同一条蓬松尾巴'}
                    design.update(body_and_posture='中型犬四足平稳着地，胸腔略深、腹线自然上收',
                                  color_and_material='白色短毛与左耳尖黑毛分区，鼻端为低光泽黑色',
                                  prop_and_action='不穿衣服也不持人类道具，抬头朝来访者发言')
                    design['execution_layout']['description'] = '同一张竖版画布展示白犬正面四足全身、侧面全身及尾部背形，不加入人类脸部或无头衣装格'
                    ensemble.validate_extra(cp, root, state, design, 'CHR-EXTRA', 'S01')
                    record = state['records']['extra-design:CHR-EXTRA:S01']
                    cp.write_json(root / record['path'], design)
                    sha = cp.digest(design)
                    record.update(sha256=sha, approval={'operator': 'test:synthetic-only', 'sha256': sha})
                    cp.write_json(root / 'project.json', state)
                package = extra_prompt(design)
                package['design_basis']['records'] = {'extra-design:CHR-EXTRA:S01': sha}
                path = root / 'new-prompt.json'
                cp.write_json(path, package)
                result = cp.cmd_submit(SimpleNamespace(project_root=str(root), kind='prompt-package',
                    character_id='CHR-EXTRA', variant_id='S01', stage='execution', file=str(path)))
                self.assertTrue(result['sha256'])
                self.assertNotIn('face_and_hair', design)
                broken = copy.deepcopy(package)
                broken['layout'] = copy.deepcopy(LAYOUT)
                with self.assertRaisesRegex(ValueError, 'layout must match'):
                    ensemble.validate_extra_prompt(cp, broken, design)

    def test_legacy_approved_prompt_remains_readable_and_pack_derives_txt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'project'
            state, design, sha, store = make_project(root)
            package = extra_prompt(design)
            package['design_basis']['records'] = {'extra-design:CHR-EXTRA:S01': sha}
            package['prompts'][0]['text'] = '9:16 正脸、45、无头、背面。' + STYLE + '，普通制服。'
            add_approved_image(root, state, package, store)
            before = (root / 'project.json').read_bytes()
            with patch.object(ensemble, 'validate_extra_prompt', side_effect=AssertionError('new gate must not rejudge legacy approval')):
                cp._checked_image(root, state, 'execution', 'CHR-EXTRA', 'S01')
                output = Path(folder) / 'pack'
                result = cp.cmd_package(SimpleNamespace(project_root=str(root), character_id='CHR-EXTRA',
                                                        variant_id='S01', output=str(output)))
            self.assertTrue(result['asset_pack'])
            txt = list(output.rglob('*.txt'))
            self.assertEqual(len(txt), 1)
            self.assertEqual(txt[0].read_text(encoding='utf-8'), package['prompts'][0]['text'] + '\n')
            self.assertEqual((root / 'project.json').read_bytes(), before)
            manifest = cp.read_json(output / 'manifest.json')
            text_rows = [row for row in manifest['files'] if row['path'].endswith('.txt')]
            self.assertEqual(len(text_rows), 1)
            self.assertTrue(text_rows[0]['derived_from'].endswith('.json'))
            for row in manifest['files']:
                self.assertEqual(cp.digest(output / row['path']), row['sha256'])

    def test_pack_copies_current_txt_and_rejects_missing_or_tampered_text(self):
        with tempfile.TemporaryDirectory() as folder:
            for scenario in ('valid', 'missing-file', 'missing-hash', 'changed-text'):
                with self.subTest(scenario=scenario):
                    root = Path(folder) / scenario
                    state, design, sha, store = make_project(root)
                    package = extra_prompt(design)
                    package['design_basis']['records'] = {'extra-design:CHR-EXTRA:S01': sha}
                    add_approved_image(root, state, package, store)
                    record = state['records']['prompt-package:execution:CHR-EXTRA:S01']
                    text_path = root / '提示词/执勤者_执勤_执行图.txt'
                    text_path.parent.mkdir()
                    text_path.write_bytes((package['prompts'][0]['text'] + '\n').encode('utf-8'))
                    record.update(text_path=str(text_path.relative_to(root)), text_sha256=cp.digest(text_path))
                    if scenario == 'missing-file':
                        text_path.unlink()
                    elif scenario == 'missing-hash':
                        record.pop('text_sha256')
                    elif scenario == 'changed-text':
                        text_path.write_text('更短的另一份提示词\n', encoding='utf-8')
                    cp.write_json(root / 'project.json', state)
                    output = Path(folder) / (scenario + '-pack')
                    args = SimpleNamespace(project_root=str(root), character_id='CHR-EXTRA', variant_id='S01', output=str(output))
                    if scenario != 'valid':
                        with self.assertRaisesRegex(ValueError, 'Prompt TXT'):
                            cp.cmd_package(args)
                        continue
                    cp.cmd_package(args)
                    copied_path = output / record['text_path']
                    self.assertEqual(copied_path.read_bytes(), text_path.read_bytes())
                    manifest = cp.read_json(output / 'manifest.json')
                    row = next(row for row in manifest['files'] if row['path'] == record['text_path'])
                    self.assertEqual(cp.digest(copied_path), row['sha256'])


if __name__ == '__main__':
    unittest.main()

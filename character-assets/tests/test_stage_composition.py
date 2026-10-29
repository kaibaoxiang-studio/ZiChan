"""Synthetic approved stage snapshots exercise real execution/compile composition."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from test_design_execution_gate import cp, phased, ROOT, current_identity, CUES
from test_design_delivery_gate import body_design


class StageCompositionTest(unittest.TestCase):
    def test_execution_resolution_and_compile_keep_separate_stage_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state, identity = current_identity(root)
            identity['payload']['recognition_axes'] = {'face_structure': '短宽圆颏端', 'hair_structure': '右侧前发片收耳后'}
            identity['payload']['differentiation_review'] = {
                'closest_character_ids': [], 'shared_features': [], 'distinct_features': [],
                'realism_check': '仅合成结构测试，尚未生成或审查图片'}

            def approved(record_key, data):
                value = phased._store(cp, root, state, record_key, data)
                value['approval'] = {'operator': 'test:synthetic-composition-fixture-only', 'sha256': value['sha256']}
                return value

            approved('stage-design:identity:CHR-TEST:base', identity)
            body = body_design(state)
            body['payload']['recognition_axes'] = {'silhouette': '7.5头身的自然修长轮廓', 'body_posture': '胸腔轻微前倾但盆腔中正'}
            phased.validate_stage(cp, root, state, body, 'CHR-TEST', 'base', 'body')
            approved('stage-design:body:CHR-TEST:base', body)
            bible = {'schema_version': 'CostumeStyleBibleV1', 'character_id': 'CHR-TEST', 'variant_id': 'base',
                     'parent_refs': {key: state['records'][key]['sha256'] for key in [
                         'design-brief:CHR-TEST:base', 'stage-design:identity:CHR-TEST:base', 'stage-design:body:CHR-TEST:base']},
                     'tier': 'full', 'new_lore_policy': 'none', 'unresolved': [],
                     'state_matrix': [{'variant_id': 'base', 'narrative_function': '安静的日常工作',
                                       'silhouette_shift': '肩臂留出修复操作空间', 'anchor_continuity': '窄圆领和右侧短开衩'}]}
            for field in ('wearing_thesis', 'world_translation', 'signature_silhouette', 'cut_grammar',
                          'palette_grammar', 'material_grammar', 'recognition_anchor', 'wearing_habits',
                          'state_logic', 'physical_and_camera_rules'):
                bible[field] = '修复台旁的日常工作服采用窄圆领、柔软肩线和右侧短开衩，袖口避免挂住纸页。'
            phased.validate_bible(cp, root, state, bible, 'CHR-TEST')
            approved('costume-bible:CHR-TEST:base', bible)
            garment = {'name_silhouette': '米灰窄圆领直筒工作裙，衣摆停在膝盖下方两指',
                       'placement_scale': '肩线贴近肩峰，腰部保留一掌的活动松量',
                       'panels': '前身两片以纵向分割线连接，后背一整片中缝留褶',
                       'overlap_fastening': '右肩布包扣闭合，后腰以两段织带连接',
                       'material_color': '灰米色中等厚度斜纹棉，袖口为低饱和墨蓝织边',
                       'front_side_back': '正面窄圆领，右侧短开衩，背面中缝倒褶延至腰下',
                       'mobility': '抬臂时腋下三角插片展开，蹲下时后背倒褶打开'}
            footwear = {'toe_opening': '圆头浅口包覆足趾，鞋口停在踝骨下方',
                        'upper_fastening': '鞋面两片柔软牛皮以脚背窄带和暗扣闭合',
                        'heel_sole': '平底外缘微厚，鞋跟高约一厘米且落地面完整',
                        'material_color': '低反光深棕皮革鞋面，灰褐色橡胶鞋底',
                        'front_back': '正面窄带横跨脚背，背面后帮连续贴合足跟'}
            garment_text, shoe_text = '；'.join(garment.values()), '；'.join(footwear.values())
            direction = {name: garment_text for name in ('script_requirement', 'narrative_function', 'front_structure',
                'back_structure', 'cut_and_fastening', 'layering', 'color_placement', 'material_behavior',
                'recognition_focus', 'mobility_and_camera', 'state_continuity', 'makeup_and_hair')}
            direction['cut_and_fastening'] += '；' + shoe_text
            direction.update(evidence_status='creative_choice', script_refs=['synthetic:work-scene'], scene_needs={
                'occasion': '修复台日常工作', 'shot_and_action': '站起递书与蹲下取纸', 'constraint_scope': '保留已批准脸发身体',
                'requirements': {name: {'decision': 'inherit', 'reason': '本状态复用已批准基础身份，不新增妆发或饰物以免干扰纸页操作。',
                                         'source_refs': ['synthetic:work-scene']} for name in phased.SCENE_NEED_NAMES}})
            direction['scene_needs']['requirements']['garment'].update(decision='design', prompt_cues=[garment['name_silhouette']])
            execution = {}
            mapping = {'character-costume-style-design': 'front_structure', 'character-costume-cut-design': 'cut_and_fastening',
                       'character-costume-color-design': 'color_placement', 'character-costume-material-design': 'material_behavior'}
            for specialist, field in mapping.items():
                row = next(row for row in cp.read_json(ROOT / 'knowledge-lock.json')['snapshots'] if specialist in row['capability_ids'])
                execution[specialist] = {'mode': 'inline', 'decision': '合成测试明确落实当前衣片结构',
                    'rules_applied': ['用可见部位和连接方式描述当前设计，非实际能力调用'],
                    'knowledge_refs': [{'path': row['path'], 'sha256': row['rules_sha256']}],
                    'results': [{'field': f'costume_direction.{field}', 'visible_result': direction[field],
                                 'basis': '合成测试服饰创作选择', 'evidence_status': 'creative_choice'}]}
            execution['character-costume-accessory-design'] = {
                'mode': 'not_needed', 'decision': '不戴工作时易挂纸页的饰物', 'execution_change_reason': '当前工作状态留空',
                'not_applicable_reason': '使用袖口和分割线完成识别，不新增配饰'}
            framing = {'canvas_crop': '9:16竖版四格执行图，底部两格保持身体比例',
                       'attire_or_panels': '上排正脸与45度脸，下排无头放大服装正面与完整背面',
                       'background_light': '浅灰无纹理背景，柔和漫射光核对衣片连接'}
            identity_layout = {'reference_roles': '头像固定脸，模卡固定身体，当前状态只改变服饰',
                               'cross_panel': '四格使用同一张已批准面孔并维持身体比例'}
            items = []
            for kind, cues in [('identity', {'face_body_anchor': identity['payload']['appearance']['face'], **identity_layout}),
                               ('hair', CUES['hair']), ('skin', CUES['skin']), ('garment', garment),
                               ('footwear', footwear), ('framing', framing)]:
                refs = {'identity': ['approved_parent:stage-design:identity:CHR-TEST:base#payload.appearance',
                                     'payload.execution_layout.identity'],
                        'hair': ['approved_parent:stage-design:identity:CHR-TEST:base#payload.visual_details.hair'],
                        'skin': ['approved_parent:stage-design:identity:CHR-TEST:base#payload.visual_details.skin'],
                        'garment': ['specialist_execution.character-costume-style-design.results.0'],
                        'footwear': ['specialist_execution.character-costume-cut-design.results.0'],
                        'framing': ['payload.execution_layout.framing']}[kind]
                items.append({'id': kind, 'kind': kind, 'source_refs': refs, 'cues': copy.deepcopy(cues)})
            costume = {'schema_version': 'CharacterStageDesignV1.2', 'execution_contract_version': 2,
                'character_id': 'CHR-TEST', 'variant_id': 'base', 'scope': 'costume', 'unresolved': [], 'deferred_dimensions': [],
                'parent_refs': {key: state['records'][key]['sha256'] for key in phased.required_parents(state, 'CHR-TEST', 'costume', 'base')},
                'specialist_execution': execution, 'payload': {'costume': {'name': '修复师日常工作裙'},
                    'recognition_axes': {'costume_color': '灰米主衣与墨蓝袖口'}, 'costume_direction': direction,
                    'visual_details': {'costume': {field: field + '：' + garment_text for field in cp.DETAIL_FIELDS['costume']},
                                       'adornments': {'body_hands': '腰部手部不佩饰物，避免操作时挂住纸页'}},
                    'execution_layout': {'framing': framing, 'identity': identity_layout},
                    'prompt_detail_contract': {'schema_version': 'PromptDetailContractV1', 'stage': 'execution',
                                               'complexity': 'ordinary', 'items': items}}}
            phased.validate_stage(cp, root, state, costume, 'CHR-TEST', 'base', 'costume')
            approved('stage-design:costume:CHR-TEST:base', costume)
            cp.write_json(root / 'project.json', state)
            result = phased.compile_card(cp, SimpleNamespace(project_root=root, character_id='CHR-TEST', variant_id='base'))
            state = cp.read_json(root / 'project.json')
            card = cp.read_json(root / state['records'][result['key']]['path'])
            self.assertEqual(set(card['prompt_detail_contracts']), {'avatar', 'execution'})
            self.assertEqual(card['stage_execution_layouts']['identity'], identity['payload']['execution_layout'])
            self.assertEqual(card['execution_layout'], costume['payload']['execution_layout'])
            package = {'design_basis': {'records': {key: state['records'][key]['sha256'] for key in
                           phased.basis_keys('CHR-TEST', 'base', 'execution', state)}}}
            resolved = phased.resolve_basis(cp, root, state, package, 'CHR-TEST', 'base', 'execution')
            self.assertEqual(resolved['prompt_detail_contracts'], card['prompt_detail_contracts'])
            self.assertEqual(resolved['appearance'], identity['payload']['appearance'])


if __name__ == '__main__':
    unittest.main()

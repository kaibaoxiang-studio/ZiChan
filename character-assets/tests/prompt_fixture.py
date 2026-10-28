"""Synthetic approved-project fixture, only for contract and adapter tests.

Approvals are visibly test-driver records; they are never a user's approval or
evidence that a designer/model actually performed a production design session.
"""
import copy
import json
from pathlib import Path
import sys

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / 'scripts'))
import character_project as cp

CUES = {
    'face': {'type': '偏长的圆角方脸', 'forehead_cheekbone': '前额与颧部接近等宽，颧点位于外眼角下方',
             'jaw_chin': '下颌角圆钝可辨，短宽颏端以浅平弧收住', 'turning': '额颧颌颏转面连续，约45°时保留同一组骨点'},
    'hair': {'type_length': '深栗棕齐下颌短波波头，发尾停在下颌下方两指',
             'hairline_part': '平缓弧形发际线，中央分缝从额中延至头顶',
             'left_right': '人物右侧前发收到耳后，左侧发片遮住左耳上缘',
             'back_flow': '后脑低层次发片贴合颅形，发根沿分缝汇入连续发束',
             'surface_control': '发际边缘整洁，不出现无根浮丝或额前交叉刻痕'},
    'brow': {'shape_placement': '中等宽平直柔弧眉，眉头位于内眼角上方，眉尾细收'},
    'eye': {'shape_placement': '偏窄长杏眼，外眼角略高于内眼角，双眼间距约一眼宽',
            'lid_iris': '上睑外半部有窄褶线，下睑柔缓，虹膜为深棕色'},
    'ear': {'shape_visibility': '耳廓中等贴头，耳轮圆顺，右耳露出，左耳上缘被发片遮挡'},
    'nose': {'bridge_tip_wings': '鼻根中等高度，鼻背基本平直，圆鼻尖，鼻翼宽近两内眼角间距'},
    'lip': {'width_shape_corners': '口宽略大于鼻翼宽，上唇偏薄下唇中央稍厚，唇峰圆钝嘴角平直'},
    'skin': {'tone_distribution': '浅中性偏暖肤色，面颊有轻微血色，脸颈上胸色调连续',
             'finish_artifact_control': '自然哑光与柔和漫反射，无成片油亮、蜡感和重复压印纹'},
    'framing': {'canvas_crop': '3:4竖版单人正面，完整头顶双肩上胸入画，闭唇中性表情',
                'attire_or_panels': '白色运动背心，纯色无图案，不穿剧情服装，不戴首饰',
                'background_light': '浅灰米色无纹理中性背景，柔和均匀摄影棚布光，无文字与拼图'},
}


def make_avatar_project(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    state = {'schema_version': cp.SCHEMA, 'pipeline_version': 3, 'design_progression': 'phased',
             'project_id': 'SYNTHETIC-PROMPT-CONTRACT', 'revision': 1, 'pending_impact': None,
             'inputs': {}, 'roster': [{'id': 'CHR-TEST', 'name': '林澄', 'tier': '主角',
                                      'priority': 'deep', 'aliases': [], 'states': []}],
             'records': {}, 'images': [], 'reviews': {}, 'references': [], 'decisions': []}
    source = root / 'inputs/script.json'
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps({'synthetic_test_data': True, 'text': '林澄，27岁城市图书修复师。她把修好的书交还读者，安静地指出缺页。'}, ensure_ascii=False), encoding='utf-8')
    state['inputs']['screenplay'] = {'path': 'inputs/script.json', 'sha256': cp.digest(source)}

    def store(key, value):
        path = root / 'records' / (key.replace(':', '_') + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        sha = cp.digest(value)
        state['records'][key] = {'path': str(path.relative_to(root)), 'sha256': sha, 'stale': False,
            'approval': {'operator': 'test:synthetic-fixture-only', 'sha256': sha,
                         'scope': 'synthetic protocol fixture, not production approval'}}
        return sha

    context_sha = store('script-context', {'schema_version': 'ScriptContextV1',
                         'source_sha256': cp.digest(source), 'synthetic_test_data': True})
    store('visual-bible', {'schema_version': 'VisualBibleV1', 'project_id': state['project_id'],
                          'world_rules': [], 'style': {'medium': '当代真人影视写实'}, 'evidence': [], 'unresolved': []})
    store('cast-plan', {'schema_version': 'CastPlanV1', 'characters': [
        {'id': 'CHR-TEST', 'design_distinction': '修长圆角方脸与贴头短波波头形成低调、稳定的轮廓。'}], 'unresolved': []})
    plan = {name: {'status': 'inline', 'reason': '合成测试中固定给定设计，验证交接机制，不代表真实专项调用。'} for name in cp.SPECIALIST_DOMAINS_V24}
    brief_sha = store('design-brief:CHR-TEST:base', {'schema_version': 'DesignDirectionBriefV1',
        'character_id': 'CHR-TEST', 'context_sha256': context_sha, 'parent_refs': {}, 'specialist_plan': plan})
    face = '；'.join(CUES['face'].values())
    hair = CUES['hair']
    skin = CUES['skin']
    payload = {'morphology': 'human', 'appearance': {'face': face},
        'feature_focus': {'core': '圆角方脸下颌与短波波头侧发片作为两个主要身份识别点'},
        'world_influences': {'environment': '当代城市日常室内工作，发式与肤质不用极端气候标签'},
        'facial_surface': {'makeup': '本合成测试身份不加可卸妆面，使用原生色差与哑光肤质'},
        'visual_details': {
            'face': {'contour': face, 'brow_eyes': '；'.join([*CUES['brow'].values(), *CUES['eye'].values(), *CUES['ear'].values()]),
                     'nose_mouth': '；'.join([*CUES['nose'].values(), *CUES['lip'].values()])},
            'hair': {'hairline_part': hair['hairline_part'], 'volume_flow': hair['back_flow'],
                     'length_texture_color': hair['type_length']},
            'skin': {'tone_variation': skin['tone_distribution'], 'surface_distribution': skin['finish_artifact_control']},
            'adornments': {'head_neck': '耳颈头部均明确留空，识别任务由脸型与发片承担'}},
        'prompt_detail_contract': {'schema_version': 'PromptDetailContractV1', 'stage': 'avatar',
            'complexity': 'ordinary', 'items': [{'id': kind, 'kind': kind, 'source_refs': ['synthetic:design-choice'],
                                                'cues': copy.deepcopy(cues)} for kind, cues in CUES.items()]}}
    mapping = {'character-face-design': ('visual_details.face.contour', face),
               'character-hair-design': ('visual_details.hair.volume_flow', hair['back_flow']),
               'character-skin-design': ('visual_details.skin.tone_variation', skin['tone_distribution']),
               'character-face-signature-design': ('visual_details.adornments.head_neck', payload['visual_details']['adornments']['head_neck']),
               'character-face-decoration-design': ('facial_surface.makeup', payload['facial_surface']['makeup']),
               'character-feature-focus': ('feature_focus.core', payload['feature_focus']['core']),
               'character-world-appearance-design': ('world_influences.environment', payload['world_influences']['environment'])}
    snapshots = cp.read_json(PLUGIN / 'knowledge-lock.json')['snapshots']
    execution = {}
    for specialist, (field, value) in mapping.items():
        knowledge = next(row for row in snapshots if specialist in row['capability_ids'])
        execution[specialist] = {'mode': 'inline', 'decision': '合成测试给定此专项结果，仅验证真实项目依据及文本覆盖。',
            'rules_applied': ['测试结构与当前画幅内可见设计的交接，非真实设计调用凭证。'],
            'knowledge_refs': [{'path': knowledge['path'], 'sha256': knowledge['rules_sha256']}],
            'results': [{'field': field, 'visible_result': value, 'basis': '合成测试设计选择', 'evidence_status': 'creative_choice'}]}
    identity = {'schema_version': 'CharacterStageDesignV1.2', 'scope': 'identity', 'character_id': 'CHR-TEST',
                'variant_id': 'base', 'parent_refs': {'design-brief:CHR-TEST:base': brief_sha},
                'payload': payload, 'specialist_execution': execution, 'unresolved': []}
    identity_sha = store('stage-design:identity:CHR-TEST:base', identity)
    (root / 'project.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    text = '林澄，约27岁中国女性，完全原创面孔，当代真人影视写实头像。\n\n' + '\n\n'.join('；'.join(item.values()) + '。' for item in CUES.values())
    package = {'schema_version': 'CharacterPromptPackageV1', 'character_id': 'CHR-TEST', 'variant_id': 'base',
        'stage': 'avatar', 'target_model': 'gpt-image-2.5', 'purpose': 'production',
        'reference_attire': 'white_sports_tank', 'anchor_images': {}, 'reference_images': [],
        'design_basis': {'records': {'design-brief:CHR-TEST:base': brief_sha, 'stage-design:identity:CHR-TEST:base': identity_sha}},
        'aspect_ratio': '3:4', 'prompts': [{'id': 'main', 'text': text}],
        'acceptance_checks': [next(iter(item.values())) for item in CUES.values()] + ['核对白色运动背心。']}
    inputs = {'project_root': str(root.resolve()), 'character_id': 'CHR-TEST', 'stage': 'avatar',
              'request': '只将给定的合成测试批准身份设计转换为完整头像JSON与TXT，不新增设计，不修改项目。'}
    return state, package, inputs


def write_delivery(folder, package):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'prompt-package.json').write_text(json.dumps(package, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (folder / '提示词.txt').write_bytes(('\n\n'.join(p['text'] for p in package['prompts']) + '\n').encode('utf-8'))


def envelope():
    return {'status': 'succeeded', 'result': {'status': 'done', 'artifact_path': 'prompt-package.json',
            'summary': 'Synthetic fixture prompt, contract checked only', 'questions': []},
            'artifacts': ['prompt-package.json', '提示词.txt'], 'questions': [], 'error': None}

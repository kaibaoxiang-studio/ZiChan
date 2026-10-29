"""Source-bound prompt editing checks; this is not a model of visual semantics.

The controller must actually review meaning.  Code checks the complete source
inventory, real text spans, version binding and unambiguous numeric/side/state
markers.  A review receipt is evidence of a declared review, not proof of taste,
screenplay understanding or image quality.  Legacy cue contracts remain separate.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import re
import unicodedata


SCHEMA = 'PromptFidelityReviewV1'
_NUMERALS = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
             '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
_OBJECTS = r'项链|木簪|皇冠|耳钉|耳饰|首饰|戒指|胸针|头纱|手套|帽子|发夹|腰带|饰品|妆面|底妆|妆'


def _ensure(condition, message):
    if not condition:
        raise ValueError(message)


def content_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def _leaves(value, path):
    if isinstance(value, str) and value.strip():
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _leaves(child, f'{path}.{key}')
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _leaves(child, f'{path}.{index}')


_METADATA = {'basis', 'reason', 'rationale', 'evidence_status', 'source_refs', 'script_refs',
             'basis_refs', 'evidence_refs', 'test_status', 'status', 'mode', 'notes',
             'confidence', 'scope', 'schema_version', 'field', 'activation_reason'}


def _visible_leaves(value, path):
    """Traverse selected structural containers, omitting their evidence metadata."""
    if isinstance(value, str) and value.strip():
        yield path, value
    elif isinstance(value, dict):
        for name, child in value.items():
            if name not in _METADATA:
                yield from _visible_leaves(child, f'{path}.{name}')
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _visible_leaves(child, f'{path}.{index}')


def design_inventory(design, stage):
    """Enumerate selected design, never a package-authored list of what to keep.

    Avatar/expression exclude body/clothing domains which are outside that frame.
    Everything else selected in the frame is required, including quiet details.
    No package can exempt a small visible part by labelling it low priority.
    """
    data = design.get('data', design)
    payload = data.get('payload', data)
    _ensure(isinstance(payload, dict), 'Fidelity source needs a design payload')
    inventory = {}
    contract = payload.get('prompt_detail_contract', {})
    if contract.get('stage') == stage:
        for item in contract.get('items', []):
            for field, cue in item.get('cues', {}).items():
                _ensure(isinstance(cue, str) and cue.strip(), 'Selected cue cannot be empty')
                detail_id = f'prompt_detail_contract.{item["id"]}.{field}'
                _ensure(detail_id not in inventory, 'Duplicate selected detail ID')
                inventory[detail_id] = cue
    covered = '\n'.join(inventory.values())
    for domain, details in payload.get('visual_details', {}).items():
        if stage in {'avatar', 'expression'} and domain in {'body', 'costume'}:
            continue
        for path, value in _visible_leaves(details, f'visual_details.{domain}'):
            if stage in {'avatar', 'expression'} and path.startswith('visual_details.adornments.body_hands'):
                continue
            if value not in covered:
                inventory[path] = value
    for key in ('morphology_details', 'identity_invariants'):
        value = payload.get(key, {})
        if key == 'morphology_details' and stage in {'avatar', 'expression'} and isinstance(value, dict):
            value = {k: v for k, v in value.items() if k == 'identity'}
        for path, text in _visible_leaves(value, key):
            if text not in covered:
                inventory[path] = text
    if stage in {'full_body', 'execution', 'costume_design'}:
        form = payload.get('body_form', {})
        anchors = form.get('proportion_anchors', {})
        for name, anchor in anchors.items():
            if isinstance(anchor, dict) and isinstance(anchor.get('relation'), str):
                inventory[f'body_form.proportion_anchors.{name}.relation'] = anchor['relation']
                for path, value in _visible_leaves(anchor.get('reference_points', []),
                                                  f'body_form.proportion_anchors.{name}.reference_points'):
                    inventory[path] = value
        for name in ('measurement_frame', 'proportions', 'masses', 'views'):
            for path, value in _visible_leaves(form.get(name, {}), f'body_form.{name}'):
                inventory[path] = value
        # The selected neutral posture and mobility constraints remain meaningful;
        # a narrative action used to test them is not a request to depict that event.
        for name in ('stance', 'mobility_result'):
            for path, value in _visible_leaves(form.get('action_check', {}).get(name, {}),
                                             f'body_form.action_check.{name}'):
                inventory[path] = value
    for name in ('appearance', 'facial_surface', 'execution_layout'):
        value = payload.get(name, {})
        if name == 'appearance' and stage in {'avatar', 'expression'} and isinstance(value, dict):
            value = {key: child for key, child in value.items() if key not in {'body', 'costume', 'clothing'}}
        for path, text in _visible_leaves(value, name):
            if text not in covered:
                inventory[path] = text
    if stage in {'execution', 'costume_design', 'full_body'}:
        for path, text in _visible_leaves(payload.get('costume', {}), 'costume'):
            inventory[path] = text
        direction = payload.get('costume_direction', {})
        for name in ('front_structure', 'back_structure', 'cut_and_fastening', 'layering',
                     'color_placement', 'material_behavior', 'recognition_focus',
                     'mobility_and_camera', 'state_continuity', 'makeup_and_hair',
                     'state_makeup', 'state_hair', 'head_ear_neck', 'wearable_accessories'):
            for path, text in _visible_leaves(direction.get(name, {}), f'costume_direction.{name}'):
                inventory[path] = text
    if stage in {'execution', 'costume_design'}:
        needs = payload.get('costume_direction', {}).get('scene_needs', {}).get('requirements', {})
        for name, need in needs.items():
            if need.get('decision') == 'design':
                for index, cue in enumerate(need.get('prompt_cues', [])):
                    inventory[f'costume_direction.scene_needs.{name}.{index}'] = cue
        if payload.get('schema_version') in {'GroupEnsembleDesignV1', 'SpeakingExtraDesignV1'}:
            for name in ('members', 'shared_visual_grammar', 'arrangement', 'world_style_translation',
                         'body_and_posture', 'face_and_hair', 'costume_front', 'costume_back',
                         'color_and_material', 'prop_and_action'):
                for path, text in _visible_leaves(payload.get(name, {}), name):
                    if not path.endswith('.slot'):
                        inventory[path] = text
            if type(payload.get('member_count')) is int:
                inventory['member_count'] = str(payload['member_count']) + '人'
    _ensure(inventory, 'Frozen source has no selected drawable details for this stage')
    return inventory


def _chinese_number(value):
    if '点' in value:
        left, right = value.split('点', 1)
        return _chinese_number(left) + '.' + ''.join(str(_NUMERALS[x]) for x in right)
    if '百' in value:
        left, right = value.split('百', 1)
        return str(int(_chinese_number(left or '一')) * 100 + int(_chinese_number(right.lstrip('零') or '零')))
    if '十' in value:
        left, right = value.split('十', 1)
        return str(int(_chinese_number(left or '一')) * 10 + int(_chinese_number(right or '零')))
    return ''.join(str(_NUMERALS[x]) for x in value)


def _normal(text):
    text = unicodedata.normalize('NFKC', text)
    # Only explicit quantities/measurements, not arbitrary characters inside words.
    pattern = r'[零〇一二两三四五六七八九十百]+(?:点[零〇一二两三四五六七八九]+)?(?=\s*(?:片|枚|只|件|个|层|道|组|头身|倍|厘米|毫米|度|颗|粒|扣))'
    text = re.sub(pattern, lambda m: _chinese_number(m.group()), text)
    return re.sub(r'\s+', '', text)


def hard_markers(text):
    """Extract only markers that code can compare without claiming comprehension."""
    text = _normal(text)
    numbers = {str(Decimal(x).normalize()) for x in re.findall(r'\d+(?:\.\d+)?', text)}
    quantities = set(re.findall(r'(\d+(?:\.\d+)?)(片|枚|只|件|个|层|道|组|头身|倍|厘米|毫米|度|颗|粒|扣)', text))
    quantities = {(str(Decimal(number).normalize()), unit) for number, unit in quantities}
    sides = set(re.findall(r'([左右])(?:侧|边)?(前发|侧发|发片|前片|后片|衣片|分缝|耳|眉|眼|肩|胸|袖|腰|手|腿|膝|腕|颈|鞋|脚|鬓)', text))
    states = set()
    for clause in re.split(r'[。；，,\n]', text):
        for match in re.finditer(_OBJECTS, clause):
            before, after = clause[:match.start()], clause[match.end():]
            absent = bool(re.search(r'(?:不戴|未戴|未佩戴|不佩戴|不再佩戴|不加|未添加|不添加|不使用|不施加|未施加|不穿|无|没有|留空|取下|摘下|移除)(?:任何|全部|所有|可卸)?$', before)
                          or re.match(r'(?:已|已经)?(?:取下|摘下|移除|留空|卸除|摘掉)', after))
            present = bool(re.search(r'(?:佩戴|戴着|戴有|配戴|穿着|穿戴|装有|带有|保留|\d+(?:枚|件|个|只))$', before))
            # Mentioning an object does not establish its state. Unrecognised
            # prose belongs to the controller's semantic check, never a guessed
            # positive which could reject a valid negative paraphrase.
            if absent or present:
                states.add(('absent' if absent else 'present', match.group()))
    return {'numbers': numbers, 'quantities': quantities, 'sides': sides, 'states': states}


def literal_retained(source, body):
    """An exact phrase under an obvious removal instruction is not coverage."""
    for match in re.finditer(re.escape(source), body):
        before = body[max(0, match.start() - 18):match.start()]
        if not re.search(r'(?:不要|避免|不采用|不保留|不使用|去掉|省略|不是|删除|不再是)\s*$', before):
            return True
    return False


def check_hard_markers(source, span, detail_id):
    _ensure(source not in span or literal_retained(source, span),
            f'Fidelity {detail_id} negates the selected source detail')
    expected, actual = hard_markers(source), hard_markers(span)
    for kind in ('numbers', 'quantities', 'sides'):
        _ensure(expected[kind] <= actual[kind],
                f'Fidelity {detail_id} changed or dropped hard {kind}: {sorted(expected[kind] - actual[kind])}')
    for state, obj in expected['states']:
        opposite = ('present' if state == 'absent' else 'absent', obj)
        _ensure(opposite not in actual['states'], f'Fidelity {detail_id} contradicts selected state: {obj}')


def validate_fidelity(package, inventory, source_sha256):
    """Validate a recorded controller review and objective guardrails only."""
    review = package.get('fidelity_review')
    _ensure(isinstance(review, dict) and review.get('schema_version') == SCHEMA,
            'New source-bound prompts need PromptFidelityReviewV1')
    _ensure(review.get('source_sha256') == source_sha256, 'Fidelity review design version changed')
    _ensure(review.get('prompt_sha256') == content_hash(package.get('prompts')), 'Fidelity review prompt content changed')
    semantic = review.get('semantic_review')
    _ensure(isinstance(semantic, dict) and semantic.get('reviewer') == 'controller' and
            semantic.get('verdict') == 'pass' and semantic.get('unresolved') == [],
            'Prompt needs a completed controller semantic review, not a code-only pass')
    _ensure(isinstance(semantic.get('notes'), str) and semantic['notes'].strip(),
            'Controller review must record its actual design and task findings')
    prompts = package.get('prompts')
    _ensure(isinstance(prompts, list) and prompts, 'Prompt fidelity needs actual prompts')
    bodies = {}
    for prompt in prompts:
        _ensure(isinstance(prompt, dict) and isinstance(prompt.get('id'), str) and prompt['id'].strip() and
                isinstance(prompt.get('text'), str) and prompt['text'].strip(), 'Prompt needs id and full text')
        _ensure(prompt['id'] not in bodies, 'Prompt IDs must be unique')
        bodies[prompt['id']] = prompt['text']
    coverage = review.get('coverage')
    _ensure(isinstance(coverage, list), 'Fidelity review needs source-to-body coverage')
    expected = {(prompt_id, detail_id) for prompt_id in bodies for detail_id in inventory}
    # Mechanical identity is stronger evidence than asking the model to repeat
    # the same span in another receipt. Only edited/nonliteral details need an
    # authored mapping; every selected source detail still belongs to expected.
    seen = {(prompt_id, detail_id) for prompt_id, body in bodies.items()
            for detail_id, source_text in inventory.items() if literal_retained(source_text, body)}
    literal_count = len(seen)
    explicit_seen = set()
    for row in coverage:
        _ensure(isinstance(row, dict), 'Fidelity coverage row must be an object')
        pair = row.get('prompt_id'), row.get('detail_id')
        _ensure(pair in expected and pair not in explicit_seen, 'Fidelity coverage has unknown or duplicate detail mapping')
        span = row.get('span')
        _ensure(isinstance(span, str) and span.strip() and span in bodies[pair[0]],
                f'Fidelity {pair[1]} must point to an actual prompt text span')
        check_hard_markers(inventory[pair[1]], span, pair[1])
        seen.add(pair)
        explicit_seen.add(pair)
    _ensure(seen == expected, f'Prompt dropped selected visible design details: {sorted(expected - seen)}')
    return {'verification_scope': 'source-inventory-and-hard-markers-with-recorded-controller-review',
            'literal_detail_matches': literal_count, 'explicit_review_mappings': len(explicit_seen),
            'semantic_equivalence_proven_by_code': False, 'image_review_performed': False}

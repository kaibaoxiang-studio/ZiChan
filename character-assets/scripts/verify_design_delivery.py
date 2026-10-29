"""Bind a typed design delivery to the real Harness inputs, without project writes.

Validation uses a disposable project/artifact copy. It never submits, approves or
replaces a production record. ``render`` exports every JSON value to design.md;
``validate`` reads the actual task inputs from stdin, not from the design file.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import character_project as cp
import requested_design

SCHEMA = 'CharacterDesignDeliveryV1'
STANDALONE = 'StandaloneCharacterDesignV1'
SCOPES = {'direction', 'identity', 'body', 'costume', 'complete'}


def source_bindings(inputs):
    """A request-only biography is valid; file evidence is bound when supplied."""
    cp.require_text(inputs, 'request')
    result = [{'kind': 'request', 'sha256': hashlib.sha256(inputs['request'].encode('utf-8')).hexdigest()}]
    sources = inputs.get('sources', [])
    cp.ensure(isinstance(sources, list), 'sources must be a list of real paths')
    paths = [('source', value) for value in sources]
    paths += [(name, inputs[name]) for name in ('script_context_path', 'direction_brief_path') if inputs.get(name)]
    for kind, value in paths:
        cp.ensure(isinstance(value, str) and value.strip(), 'Source path must be text')
        path = Path(value).expanduser().resolve()
        cp.ensure(path.is_file(), f'Design source does not exist: {path}')
        result.append({'kind': kind, 'path': str(path), 'sha256': cp.digest(path)})
    return result


def render_legacy(delivery):
    """Deterministic readable export: no second authored summary can drop detail."""
    cp.ensure(isinstance(delivery, dict), 'Design delivery must be an object')
    labels = {'data': '设计内容', 'payload': '具象设计', 'specialist_execution': '实际专项成果',
              'understanding': '人物理解', 'sources': '实际输入来源', 'subject': '独立设计对象',
              'parent_refs': '上游版本', 'specialist_plan': '专项任务计划'}
    lines = ['# 角色设计交付', '']

    def scalar(value):
        if isinstance(value, str):
            return value.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    def walk(value, depth=0):
        if isinstance(value, dict):
            if not value:
                lines.append('  ' * depth + '- {}')
            for key in sorted(value):
                item = value[key]
                label = labels.get(key, key)
                if isinstance(item, (dict, list)):
                    lines.append('  ' * depth + f'- **{label}**')
                    walk(item, depth + 1)
                else:
                    lines.append('  ' * depth + f'- **{label}**：{scalar(item)}')
        elif isinstance(value, list):
            if not value:
                lines.append('  ' * depth + '- []')
            for index, item in enumerate(value, 1):
                if isinstance(item, (dict, list)):
                    lines.append('  ' * depth + f'- 第 {index} 项')
                    walk(item, depth + 1)
                else:
                    lines.append('  ' * depth + '- ' + scalar(item))
        else:
            lines.append('  ' * depth + '- ' + scalar(value))

    walk(delivery)
    return '\n'.join(lines) + '\n'


def render(delivery, prompt_package=None, include_internal=True):
    """One complete user view, with technical provenance kept in an appendix."""
    cp.ensure(isinstance(delivery, dict), 'Design delivery must be an object')
    data = delivery.get('data', {})
    subject = data.get('subject', {})
    name = subject.get('name') or data.get('character_id') or '当前角色'
    lines = [f'# {name}角色设计', '', '## 人物定位与设计意图', '']
    understanding = data.get('understanding', {})
    labels = {'role_in_story': '人物定位', 'core_motivation': '动机', 'central_tension': '核心矛盾',
              'world_and_life': '生活与世界', 'relationships': '关系', 'arc': '人物变化',
              'contour': '轮廓与转面', 'brow_eyes': '眉眼与位置关系', 'nose_mouth': '鼻唇与连接',
              'hairline_part': '发际与分缝', 'volume_flow': '前侧后体积与发流',
              'length_texture_color': '长度、质地与颜色', 'tone_variation': '肤色与局部色差',
              'surface_distribution': '表面与肌理', 'frame_proportions': '比例与参照', 'weight_posture': '重心与体态',
              'silhouette_layers': '廓形与衣层', 'neckline': '领口', 'shoulder_sleeve': '肩袖',
              'seams_fastening_mobility': '衣片连接、开合与活动', 'material_drape_wear': '材料行为与状态',
              'color_placement': '色块分区', 'head_neck': '头耳颈佩戴', 'body_hands': '衣身与手部佩戴',
              'proportion_anchors': '测量锚点', 'measurement_frame': '测量姿态与端点',
              'head_body': '头身关系', 'shoulder_hip': '肩胯关系', 'torso_legs': '躯干与腿段',
              'arm_segments': '臂段', 'leg_segments': '腿段', 'proportions': '比例',
              'masses': '体块', 'head': '头部', 'ribcage': '胸腔', 'pelvis': '骨盆',
              'relationships': '相互关系', 'views': '视角', 'front': '正面', 'side': '侧面', 'back': '背面',
              'action_check': '动作核对', 'stance': '站姿', 'script_action': '实际动作',
              'mobility_result': '活动关系', 'test_status': '验证状态', 'relation': '关系',
              'reference_points': '参照端点', 'basis': '设计依据', 'mode': '表达方式',
              'script_requirement': '原文要求', 'narrative_function': '叙事作用',
              'front_structure': '正面结构', 'back_structure': '背面结构',
              'cut_and_fastening': '剪裁与开合', 'layering': '叠层', 'material_behavior': '材料行为',
              'recognition_focus': '识别重点', 'mobility_and_camera': '动作与镜头',
              'state_continuity': '状态接续', 'makeup_and_hair': '妆发',
              'environment': '环境接触', 'technology': '技术', 'resources_and_access': '资源与取得',
              'appearance_effects': '可见影响', 'feature': '结构', 'mechanism': '形成机制',
              'makeup': '妆面', 'core': '主要识别点', 'quiet_zones': '安静区'}

    def values(value):
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [s for entry in value for s in values(entry)]
        if isinstance(value, dict):
            return [s for key, entry in value.items() if key not in {'sha256', 'schema_version', 'source_refs', 'basis_refs'}
                    for s in values(entry)]
        return [str(value)] if value is not None else []

    def described(value, prefix=()):
        """Small domain labels preserve which bone, view or proportion is meant."""
        if isinstance(value, dict):
            for key, entry in value.items():
                if key in {'schema_version', 'sha256', 'evidence_status', 'source_refs', 'basis_refs', 'script_refs'}:
                    continue
                yield from described(entry, (*prefix, labels.get(key, key)))
        elif isinstance(value, list):
            if all(not isinstance(entry, (dict, list)) for entry in value):
                yield ' / '.join(prefix) + '：' + '、'.join(str(entry) for entry in value)
            else:
                for index, entry in enumerate(value, 1):
                    yield from described(entry, (*prefix, str(index)))
        elif value is not None:
            yield (' / '.join(prefix) + '：' if prefix else '') + str(value)

    if isinstance(understanding, dict):
        for key, value in understanding.items():
            if key in labels:
                lines.append(f'**{labels[key]}：** ' + '；'.join(values(value)) + '\n')
    elif understanding:
        lines.extend(values(understanding))
    for key in ('design_thesis', 'recommended_direction', 'visual_strategy'):
        if data.get(key):
            lines.extend(values(data[key]))
            lines.append('')
    payload = data.get('payload', data)
    details = payload.get('visual_details', {})
    lines.extend(['## 当前完整设计', ''])
    for domain, title in [('face', '脸与五官'), ('hair', '发型'), ('skin', '皮肤与妆面'),
                          ('body', '身体与体态'), ('costume', '衣装'), ('adornments', '佩戴与留白')]:
        if details.get(domain):
            lines.extend([f'### {title}', ''])
            for key, value in details[domain].items():
                lines.append(f'**{labels.get(key, title)}：** ' + '；'.join(values(value)) + '\n')
    # These fields carry real design beyond the compact visual index.
    for key, title in [('body_form', '体块、跨视角与动作'), ('morphology_details', '形态结构'),
                       ('appearance', '身份与外观'), ('costume', '当前衣装方案'),
                       ('costume_direction', '衣装接续与状态'), ('facial_surface', '稳定标记与妆面'),
                       ('identity_invariants', '保持不变的身份结构'), ('feature_focus', '焦点与安静区'),
                       ('world_influences', '世界与生活如何影响外观'),
                       ('differentiation_review', '近邻差异与辨识')]:
        if payload.get(key):
            lines.extend([f'### {title}', ''])
            lines.extend(paragraph + '\n' for paragraph in dict.fromkeys(described(payload[key])))
    # Include any selected cue not already present in the narrative; compilers
    # may use this detail without forcing the reader to inspect machine JSON.
    extra = []
    narrative = '\n'.join(lines)
    for item in payload.get('prompt_detail_contract', {}).get('items', []):
        for cue in item.get('cues', {}).values():
            if cue not in narrative and cue not in extra:
                extra.append(cue)
    if extra:
        lines.extend(['### 已选细节补充', '', '；'.join(extra), ''])
    lines.extend(['## 取舍、修改与待决', ''])
    for key in ('changes', 'alternatives', 'unresolved', 'deferred_dimensions'):
        if data.get(key):
            lines.extend(values(data[key]))
            lines.append('')
    if not any(data.get(key) for key in ('changes', 'alternatives', 'unresolved', 'deferred_dimensions')):
        lines.extend(['当前稿无额外待决事项；设计仍以用户实际确认范围为准。', ''])
    if prompt_package is not None:
        from export_prompt_text import render_prompt_text
        lines.extend(['## 当前可复制提示词', '', render_prompt_text(prompt_package).rstrip(), ''])
    if include_internal:
        lines.extend(['<details>', '<summary>来源与执行记录（内部附录）</summary>', '',
                      '```json', json.dumps(delivery, ensure_ascii=False, indent=2), '```', '', '</details>', ''])
    return '\n'.join(lines)


def merged_view(delivery, bases):
    """Mechanical candidate view; never a production card or approval."""
    if not bases:
        return copy.deepcopy(delivery)
    current = delivery.get('data', delivery)
    combined = {}
    payload = {}
    for base in bases:
        data = base.get('data', base)
        for key, value in data.items():
            if 'payload' not in data and key not in {'understanding', 'design_thesis', 'recommended_direction',
                                                       'alternatives', 'world_style_translation', 'narrative_function', 'subject'}:
                # A legacy card is itself the payload. Do not duplicate stale
                # appearance/visual fields beside the newly merged payload.
                continue
            if key not in {'payload', 'scope', 'schema_version', 'parent_refs', 'specialist_execution',
                           'approval', 'approved', 'operator', 'stale', 'provenance'}:
                combined.setdefault(key, copy.deepcopy(value))
        for key, value in data.get('payload', data).items():
            if key == 'visual_details':
                target = payload.setdefault(key, {})
                for domain, details in value.items():
                    cp.ensure(domain not in target or target[domain] == details,
                              'Base documents conflict; select compatible current source records')
                    target[domain] = copy.deepcopy(details)
            elif key not in {'schema_version', 'scope', 'character_id', 'variant_id', 'parent_refs', 'specialist_execution'}:
                payload.setdefault(key, copy.deepcopy(value))
    before = copy.deepcopy(payload.get('visual_details', {}))
    changed = set(current.get('requested_dimensions', current.get('payload', {}).get('visual_details', {})))
    _refresh_parent_views(payload, current.get('payload', {}), changed)
    for key, value in current.get('payload', {}).items():
        if key == 'visual_details':
            payload.setdefault(key, {}).update(copy.deepcopy(value))
        else:
            payload[key] = copy.deepcopy(value)
    combined.update(copy.deepcopy(current))
    combined['payload'] = payload
    changes = list(current.get('changes', []))
    domain_names = {'face': '脸与五官', 'hair': '发型', 'skin': '皮肤与妆饰',
                    'body': '身体与体态', 'costume': '衣装', 'adornments': '佩戴'}
    for domain, value in current.get('payload', {}).get('visual_details', {}).items():
        if domain in before and before[domain] != value:
            changes.append(f'{domain_names.get(domain, domain)}：本轮候选已调整，其他未指定部位保留所选基底；尚未替换正式批准。')
    combined['changes'] = changes or ['本稿为基底与当前候选的合并阅读视图，尚未替换正式批准。']
    return {**copy.deepcopy(delivery), 'data': combined}


def _refresh_parent_views(parent, delta, changed):
    """Remove stale same-domain projections while preserving unrelated identity.

    A legacy summary/invariant is a view, not authority to retain a previous
    haircut after the concrete hair field changed. Ambiguous mixed invariants
    are rejected rather than silently deleting the unchanged face they contain.
    """
    visual = delta.get('visual_details', {})
    summaries = {domain: '；'.join(str(value) for value in visual[domain].values())
                 for domain in changed if isinstance(visual.get(domain), dict)}
    aliases = {'face': {'face', 'face_shape', 'features'}, 'hair': {'hair', 'hair_style', 'hairstyle'},
               'skin': {'skin', 'skin_tone'}, 'body': {'body', 'body_shape', 'posture'},
               'costume': {'costume', 'clothing', 'outfit'}, 'adornments': {'adornments', 'accessories'}}
    appearance = parent.get('appearance')
    if isinstance(appearance, dict):
        for domain in changed:
            for alias in aliases.get(domain, {domain}):
                if alias in appearance:
                    appearance[alias] = summaries.get(domain, '')
    if 'costume' in changed and 'costume' in parent and 'costume' not in delta:
        parent['costume'] = {'main': summaries.get('costume', '')}
    axes = parent.get('recognition_axes')
    if isinstance(axes, dict):
        for axis, domain in {'face_structure': 'face', 'hair_structure': 'hair', 'silhouette': 'body',
                             'body_posture': 'body', 'costume_color': 'costume'}.items():
            if domain in changed and axis in axes:
                axes[axis] = summaries.get(domain, '')
    # Preserve selected details of every unaffected domain, including facial
    # specifics that may be richer than the compact visual_details index.
    kinds = {'face': {'face', 'brow', 'eye', 'ear', 'nose', 'lip'}, 'hair': {'hair'},
             'skin': {'skin', 'makeup'}, 'body': {'identity'},
             'costume': {'garment', 'footwear', 'focus_component', 'surface_pattern'}, 'adornments': {'adornment'}}
    contract = parent.get('prompt_detail_contract')
    if isinstance(contract, dict):
        replaced = set().union(*(kinds.get(domain, set()) for domain in changed))
        contract['items'] = [item for item in contract.get('items', []) if item.get('kind') not in replaced]
        if not contract['items']:
            parent.pop('prompt_detail_contract', None)
    patterns = {
        'hair': r'发型|发际|发流|发片|头发|短发|长发|后脑|后颈|分缝|分线|鬓',
        'face': r'脸型|骨相|颧|下颌|下颏|颏端|眉形|眼型|眼裂|鼻梁|鼻翼|鼻尖|唇形|嘴角|耳廓',
        'skin': r'肤色|皮肤|毛孔|肤质|色差|妆面',
        'body': r'头身|肩胯|肩宽|骨盆|腿长|肘|膝|踝|重心|体态|躯干|胸腔',
        'costume': r'衣层|外套|裤腿|裙摆|袖口|领口|衣片|鞋面|开襟',
        'adornments': r'耳饰|项链|戒指|发簪|头饰|腕饰|手环',
    }

    def revise(value):
        if isinstance(value, str):
            domains = {domain for domain, pattern in patterns.items() if re.search(pattern, value)}
            affected = domains & changed
            if not affected:
                return value
            if domains - changed:
                pieces = re.split(r'([，,；;。]|与|和|及)', value)
                if len(pieces) > 1:
                    return ''.join(revise(piece) if index % 2 == 0 else piece
                                   for index, piece in enumerate(pieces))
            cp.ensure(not domains - changed,
                      'Inherited mixed-domain design view conflicts with this trial; supply a separated updated view without dropping unchanged identity')
            return '；'.join(summaries[domain] for domain in sorted(affected) if summaries.get(domain))
        if isinstance(value, list):
            return [revise(item) for item in value]
        if isinstance(value, dict):
            return {key: revise(item) for key, item in value.items()}
        return value

    # New explicit views supersede old ones. Otherwise refresh only an
    # identifiable changed domain; do not guess at a combined face/hair claim.
    for key in ('identity_invariants', 'feature_focus', 'differentiation_review'):
        if key in parent and key not in delta:
            parent[key] = revise(parent[key])
    for key in ('approved_choices',):
        if isinstance(parent.get(key), list) and key not in delta:
            prefixes = {'face': ('visual_details.face.', 'appearance.face'),
                        'hair': ('visual_details.hair.', 'appearance.hair', 'recognition_axes.hair_structure', 'costume_direction.state_hair'),
                        'skin': ('visual_details.skin.', 'appearance.skin', 'costume_direction.state_makeup'),
                        'body': ('visual_details.body.', 'body_form.', 'appearance.body', 'recognition_axes.silhouette', 'recognition_axes.body_posture'),
                        'costume': ('visual_details.costume.', 'costume.', 'costume_direction.', 'recognition_axes.costume_color'),
                        'adornments': ('visual_details.adornments.', 'appearance.accessories')}
            parent[key] = [row for row in parent[key] if not any(
                str(row.get('field', '')).startswith(prefixes.get(domain, ()))
                or str(row.get('field', '')) in {'appearance.' + alias for alias in aliases.get(domain, {domain})}
                for domain in changed)]


def resolved_delivery(delivery, inputs):
    """Read-only parent projection supplies unchanged face/body to a trial."""
    bases = read_base_designs(inputs, delivery.get('data', {}).get('subject'))
    if inputs.get('project_root'):
        root = Path(inputs['project_root']).expanduser().resolve()
        state = cp.read_json(root / 'project.json')
        for record_key, expected in inputs.get('parent_refs', {}).items():
            record = cp._checked_record(root, state, record_key)
            cp.ensure(record['sha256'] == expected, f'Trial parent version changed: {record_key}')
            if record_key.startswith(('stage-design:', 'design-card:')):
                bases.append(cp.read_json(root / record['path']))
    return merged_view(delivery, bases)


def read_base_designs(inputs, subject=None):
    """Task-local canonical bases are file-bound sources, never project approval."""
    references = inputs.get('base_designs', [])
    cp.ensure(isinstance(references, list), 'base_designs must be actual path/SHA references')
    cp.ensure(not references or not inputs.get('project_root'),
              'Local base designs are project-free only; a project trial must inherit its real approved parent_refs')
    bases = []
    expected = subject
    for reference in references:
        cp.ensure(isinstance(reference, dict) and set(reference) == {'path', 'sha256'}, 'Local base needs path and sha256 only')
        cp.require_text(reference, 'path')
        path = Path(reference['path']).expanduser()
        cp.ensure(path.is_absolute() and path.is_file() and not path.is_symlink(), 'Local base needs a real absolute canonical file')
        cp.ensure(cp.digest(path) == reference['sha256'], 'Local base design changed; freeze a new candidate')
        base = cp.read_json(path)
        cp.ensure(isinstance(base, dict), 'Local base design must be an object')
        data = base.get('data', base)
        cp.ensure(isinstance(data, dict) and isinstance(data.get('payload', data), dict) and
                  bool(data.get('payload', data).get('visual_details') or data.get('payload', data).get('morphology_details')),
                  'Local base needs actual drawable canonical design, not a summary or approval receipt')
        actual = data.get('subject')
        cp.ensure(isinstance(actual, dict) and actual.get('name') and actual.get('local_key'),
                  'Project-free base needs its actual named local subject')
        if expected is None:
            expected = actual
        cp.ensure(isinstance(expected, dict) and all(actual.get(field) == expected.get(field)
                  for field in ('name', 'local_key')), 'Local base belongs to another subject/local_key')
        bases.append(base)
    return bases


def _project_sources(root, state):
    for source in state.get('inputs', {}).values():
        path = (root / source['path']).resolve()
        cp.ensure(path.is_relative_to(root) and path.is_file(), 'Project source is missing or outside project')
        cp.ensure(cp.digest(path) == source['sha256'], 'Project source changed')


def _copy_resource(source_root, target_root, relative):
    """Copy one referenced resource, rejecting traversal and linked inputs."""
    relative = Path(relative)
    cp.ensure(not relative.is_absolute() and '..' not in relative.parts,
              'Design validation resource must be project/artifact-relative')
    source_root = source_root.resolve()
    source = source_root / relative
    cp.ensure(source.resolve().is_relative_to(source_root), 'Design validation resource escapes its root')
    cp.ensure(all(not part.is_symlink() for part in [source, *source.parents] if part != source_root.parent),
              'Design validation resources must not follow symlinks')
    cp.ensure(source.is_file(), f'Design validation resource is missing: {relative}')
    target = target_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _proposal_resources(data):
    refs = [work['proposal_ref'] for work in data.get('specialist_execution', {}).values()
            if isinstance(work, dict) and work.get('mode') == 'independent' and isinstance(work.get('proposal_ref'), str)]
    if isinstance(data.get('route_ref'), str):
        refs.append(data['route_ref'])
    refs += [work['proposal_ref'] for work in data.get('specialist_coverage', {}).values()
             if isinstance(work, dict) and work.get('status') == 'used' and isinstance(work.get('proposal_ref'), str)]
    return refs


def _minimal_copy(source_root, target_root, state, data, artifact_root):
    """No generated images, archives or unrelated files enter the validator."""
    target_root.mkdir(parents=True, exist_ok=True)
    if state is not None:
        _copy_resource(source_root, target_root, 'project.json')
        for source in state.get('inputs', {}).values():
            _copy_resource(source_root, target_root, source['path'])
        for record in state.get('records', {}).values():
            _copy_resource(source_root, target_root, record['path'])
    # A new independent result stays in artifact_dir until normal project import.
    # Its bound JSON is overlaid only in this throwaway validation tree.
    for relative in _proposal_resources(data):
        origin = artifact_root if (artifact_root / relative).is_file() else source_root
        _copy_resource(origin, target_root, relative)
    # Copy only knowledge snapshots actually referenced by this or parent work.
    documents = [data]
    if state is not None:
        documents += [cp.read_json(target_root / row['path']) for row in state.get('records', {}).values()]
    for document in documents:
        for relative in _proposal_resources(document):
            if not (target_root / relative).is_file():
                _copy_resource(source_root, target_root, relative)
        for work in document.get('specialist_execution', {}).values():
            if not isinstance(work, dict):
                continue
            if work.get('mode') == 'independent':
                relative = work.get('proposal_ref')
                if isinstance(relative, str) and not (target_root / relative).is_file():
                    _copy_resource(source_root, target_root, relative)
                if isinstance(relative, str):
                    refs = cp.read_json(target_root / relative).get('knowledge_refs', [])
                else:
                    refs = []
            else:
                refs = work.get('knowledge_refs', [])
            for ref in refs:
                sha = ref.get('sha256', '') if isinstance(ref, dict) else ''
                if re.fullmatch(r'[0-9a-f]{64}', sha):
                    relative = 'knowledge-snapshots/' + sha
                    if (source_root / relative).is_file():
                        _copy_resource(source_root, target_root, relative)


def _legacy_card(root, state, data, character, variant):
    """Keep the complete-card submission contract without migrating the project."""
    for dependency in ('visual-bible', 'cast-plan'):
        cp._checked_record(root, state, dependency)
    cp._validate_record('design-card', data, state, character, variant)
    record_key = cp._record_key('design-card', character, variant)
    prior = state.get('records', {}).get(record_key)
    unchanged = bool(prior and prior.get('approval') and not prior.get('stale') and
                     prior.get('sha256') == cp.digest(data))
    if unchanged:
        cp._checked_record(root, state, record_key)
        return
    human = data.get('morphology') in {'human', 'humanoid'}
    if human:
        row = next(row for row in state['roster'] if row['id'] == character)
        if row.get('tier') in cp.HEAVY_TIERS or row.get('priority') == 'deep':
            schema = 'CharacterDesignCardV2.4' if state.get('pipeline_version', 1) >= 2 else 'CharacterDesignCardV2.2'
            cp.ensure(data.get('schema_version') == schema,
                      f'Submitted lead/important human design cards require {schema}; existing approvals remain readable')
        if data.get('schema_version') in {'CharacterDesignCardV2.2', 'CharacterDesignCardV2.4'}:
            cp.validate_body_proportion_anchors(data)
            cp.validate_design_handoffs(data, root)


def _standalone_payload(data, artifact_root):
    scope = data['scope']
    cp.ensure(data.get('execution_contract_version') == 2, 'Standalone design needs execution_contract_version:2')
    payload = data.get('payload')
    cp.ensure(isinstance(payload, dict), 'Standalone design needs a concrete payload')
    cp.ensure(payload.get('morphology') in {'human', 'humanoid', 'nonhuman'}, 'Standalone needs explicit morphology')
    cp.ensure(set(payload) <= cp.phased.COMMON_PAYLOAD | cp.phased.SCOPE_PAYLOAD[scope] | {'visual_details'},
              'Standalone payload changes another scope')
    details = payload.get('visual_details')
    cp.ensure(isinstance(details, dict), 'Standalone needs visual_details')
    allowed = cp.phased.OWNERS[scope] | ({'adornments'} if scope != 'body' else set())
    cp.ensure(set(details) <= allowed, 'Standalone visual fields belong to another scope')
    human = payload['morphology'] in {'human', 'humanoid'}
    if human:
        for domain in cp.phased.OWNERS[scope]:
            cp.ensure(isinstance(details.get(domain), dict), f'Standalone needs visual_details.{domain}')
            for field in cp.DETAIL_FIELDS[domain]:
                cp.require_text(details[domain], field)
                cp.ensure(len(details[domain][field].strip()) >= 8, f'Concrete design missing: {domain}.{field}')
        if scope in {'identity', 'costume'}:
            owned = 'head_neck' if scope == 'identity' else 'body_hands'
            cp.ensure(set(details.get('adornments', {})) == {owned}, 'Standalone adornment ownership mismatch')
            cp.require_text(details['adornments'], owned)
        if scope == 'identity':
            cp.validate_world_and_face(payload, allow_proposals=True)
            cp.validate_feature_focus(payload)
            cp.ensure(isinstance(payload.get('identity_invariants'), list) and payload['identity_invariants'],
                      'Standalone identity needs stable identity_invariants')
        elif scope == 'body':
            cp.validate_body_form(payload)
            cp.validate_body_proportion_anchors(payload)
        else:
            cp.ensure(isinstance(payload.get('costume'), dict) and payload['costume'], 'Standalone costume needs costume summary')
    else:
        form = payload.get('morphology_details')
        cp.ensure(isinstance(form, dict) and set(form) == {scope} and form[scope],
                  'Nonhuman standalone needs current-scope morphology_details')
    cp.require_list(data, 'deferred_dimensions')
    cp.require_list(data, 'unresolved')
    # The local key is only a temporary proposal target, never a formal asset ID.
    stage = {**data, 'character_id': data['subject']['local_key'], 'variant_id': 'base'}
    cp.phased.validate_execution(cp._runtime(), artifact_root, stage, state=None, strict=True)
    if human and scope == 'identity':
        cp.phased.validate_prompt_detail_contract(cp._runtime(), stage, root=artifact_root, state=None, strict=True)
    elif payload.get('prompt_detail_contract'):
        cp.phased.validate_prompt_detail_contract(cp._runtime(), stage, root=artifact_root, state=None, strict=True)


def validate(design_path, inputs, markdown_path=None):
    cp.ensure(isinstance(inputs, dict), 'Design delivery needs the actual task inputs')
    cp.require_text(inputs, 'request')
    requested = 'requested_dimensions' in inputs
    scope = 'requested' if requested else inputs.get('scope')
    if scope is None:
        scope = 'identity'
        if inputs.get('project_root'):
            metadata = Path(inputs['project_root']).expanduser().resolve() / 'project.json'
            if metadata.is_file():
                state = cp.read_json(metadata)
                if state.get('schema_version') == cp.SCHEMA and not cp.phased.enabled(state):
                    scope = 'complete'
    cp.ensure(scope in SCOPES | {'requested'}, 'Unsupported requested design scope')
    cp.ensure(not requested or inputs.get('scope') in {None, 'requested'},
              'requested_dimensions cannot downgrade an explicit production scope')
    design_path = Path(design_path).resolve()
    delivery = cp.read_json(design_path)
    cp.ensure(isinstance(delivery, dict) and set(delivery) == {'schema_version', 'kind', 'scope', 'data'},
              'Design delivery needs schema_version, kind, scope and data only')
    cp.ensure(delivery['schema_version'] == SCHEMA, f'Expected {SCHEMA}')
    cp.ensure(delivery['scope'] == scope, 'Design delivery scope differs from actual task scope')
    data = delivery['data']
    cp.ensure(isinstance(data, dict), 'Design delivery data must be an object')
    markdown_path = Path(markdown_path) if markdown_path else design_path.with_name('design.md')
    cp.ensure(markdown_path.is_file() and not markdown_path.is_symlink(), 'Design delivery needs design.md')
    allowed_views = {render(delivery).encode('utf-8')}
    if not requested:
        allowed_views.add(render_legacy(delivery).encode('utf-8'))
    cp.ensure(markdown_path.read_bytes() in allowed_views,
              'design.md must be the exact deterministic export of design-result.json')
    with tempfile.TemporaryDirectory(prefix='character-design-validation-') as folder:
        sandbox = Path(folder)
        if requested:
            cp.ensure(delivery['kind'] == 'standalone' and data.get('schema_version') == STANDALONE,
                      'Requested dimensions need the explicit standalone delivery branch')
            cp.ensure(isinstance(data.get('subject'), dict), 'Requested design needs a named local subject')
            for field in ('name', 'local_key'):
                cp.require_text(data['subject'], field)
            cp.ensure(not re.match(r'^CHR-', data['subject']['local_key'], re.I), 'Standalone local key must not impersonate a formal character ID')
            cp.ensure(data.get('sources') == source_bindings(inputs), 'Standalone sources must match the actual task request and source hashes')
            read_base_designs(inputs, data.get('subject'))
            working = sandbox / 'artifacts'
            _minimal_copy(design_path.parent, working, None, data, design_path.parent)
            requested_design.validate(cp, data, inputs, working)
        elif inputs.get('project_root'):
            root = Path(inputs['project_root']).expanduser().resolve()
            cp.ensure((root / 'project.json').is_file(), 'Design delivery needs a real character project')
            state = cp.read_json(root / 'project.json')
            cp.ensure(state.get('schema_version') == cp.SCHEMA, 'Unsupported project state')
            cp.ensure(not state.get('pending_impact'), 'Resolve upstream impact before design delivery')
            _project_sources(root, state)
            cp.require_text(inputs, 'character_id')
            character, variant = inputs['character_id'], inputs.get('variant_id', 'base')
            cp.ensure(character in {row['id'] for row in state['roster']}, 'Unknown character ID in actual task')
            cp.require_known_variant(state, character, variant)
            working = sandbox / 'project'
            _minimal_copy(root, working, state, data, design_path.parent)
            if not cp.phased.enabled(state):
                cp.ensure(scope == 'complete', 'Legacy complete projects only accept scope complete; do not auto-migrate')
                cp.ensure(delivery['kind'] == 'legacy_card', 'Complete task needs kind legacy_card')
                _legacy_card(working, state, data, character, variant)
            elif scope == 'direction':
                cp.ensure(delivery['kind'] == 'direction', 'Direction task needs kind direction')
                cp.ensure(variant == 'base', 'Direction belongs to base')
                cp.phased.validate_brief(cp._runtime(), working, state, data, character)
            else:
                cp.ensure(scope != 'complete', 'Scope complete belongs only to legacy complete projects')
                cp.ensure(delivery['kind'] == 'stage', 'Stage task cannot be satisfied by a direction draft')
                cp.ensure(data.get('schema_version') == 'CharacterStageDesignV1.2', 'New stage delivery needs CharacterStageDesignV1.2')
                cp.ensure(data.get('execution_contract_version') == 2, 'Stage delivery needs execution_contract_version:2')
                cp.phased.validate_stage(cp._runtime(), working, state, data, character, variant, scope, strict=True)
        else:
            cp.ensure(scope in {'identity', 'body', 'costume'}, 'Standalone needs a concrete identity/body/costume scope')
            cp.ensure(delivery['kind'] == 'standalone', 'A project-free design needs kind standalone')
            cp.ensure(not inputs.get('character_id') and not inputs.get('variant_id'), 'Standalone task cannot assert a formal asset ID or variant')
            cp.ensure(data.get('schema_version') == STANDALONE and data.get('scope') == scope, 'Standalone schema or scope mismatch')
            cp.ensure(not any(key in data for key in ('character_id', 'variant_id', 'parent_refs', 'project_id')),
                      'Standalone design cannot manufacture formal IDs, project or approved parents')
            subject = data.get('subject')
            cp.ensure(isinstance(subject, dict), 'Standalone needs a named local subject')
            cp.require_text(subject, 'name')
            cp.require_text(subject, 'local_key')
            cp.ensure(not re.match(r'^CHR-', subject['local_key'], re.I), 'Standalone local key must not impersonate a formal character ID')
            cp.ensure(data.get('sources') == source_bindings(inputs), 'Standalone sources must match the actual task request and source hashes')
            cp.ensure(isinstance(data.get('understanding'), dict), 'Standalone needs character understanding')
            for field in cp.phased.UNDERSTANDING_FIELDS:
                cp.require_text(data['understanding'], field)
            cp.require_text(data, 'design_thesis')
            working = sandbox / 'artifacts'
            _minimal_copy(design_path.parent, working, None, data, design_path.parent)
            _standalone_payload(data, working)
    return {'valid': True, 'kind': delivery['kind'], 'scope': scope, 'design_sha256': cp.digest(delivery),
            'project_write_performed': False, 'approved': False}


def validate_frozen(source):
    """Read a frozen task delivery; never submit or approve a project record."""
    cp.ensure(isinstance(source, dict) and source.get('kind') == 'task_frozen_delivery', 'Expected task_frozen_delivery source')
    paths = {}
    for field in ('path', 'inputs_path'):
        cp.require_text(source, field)
        path = Path(source[field]).expanduser()
        cp.ensure(path.is_absolute() and path.is_file() and not path.is_symlink(), 'Frozen design source needs real absolute files')
        expected = source.get('sha256' if field == 'path' else 'inputs_sha256')
        cp.ensure(cp.digest(path) == expected, f'Frozen {field} changed')
        paths[field] = path.resolve()
    inputs = cp.read_json(paths['inputs_path'])
    cp.ensure(source.get('project_root') == inputs.get('project_root') and
              source.get('parent_refs', {}) == inputs.get('parent_refs', {}), 'Frozen project constraints differ from actual design inputs')
    checked = validate(paths['path'], inputs)
    delivery = cp.read_json(paths['path'])
    return {'delivery': delivery, 'resolved_delivery': resolved_delivery(delivery, inputs),
            'inputs': inputs, 'validation': checked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('render', help='Export design.md mechanically; does not approve or validate design')
    export.add_argument('--design', required=True, type=Path)
    export.add_argument('--output', type=Path)
    check = commands.add_parser('validate', help='Validate using actual task inputs JSON from stdin')
    check.add_argument('--design', required=True, type=Path)
    check.add_argument('--markdown', type=Path)
    document = commands.add_parser('document', help='Update the sole user document from canonical design and current prompt')
    document.add_argument('--design', required=True, type=Path)
    document.add_argument('--prompt', type=Path)
    document.add_argument('--base-design', type=Path, action='append', default=[],
                          help='Existing canonical base or stage record; repeat for compatible identity/body/costume records')
    document.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command in {'render', 'document'}:
            output = args.output or args.design.with_name('design.md')
            prompt = cp.read_json(args.prompt) if args.command == 'document' and args.prompt else None
            delivery = cp.read_json(args.design)
            if args.command == 'document':
                dims = delivery.get('data', {}).get('requested_dimensions')
                cp.ensure(not (output.exists() and dims and not args.base_design),
                          'Updating a task-local document needs its canonical --base-design, not inferred Markdown')
                delivery = merged_view(delivery, [cp.read_json(p) for p in args.base_design])
            output.write_bytes(render(delivery, prompt,
                                     include_internal=args.command != 'document').encode('utf-8'))
            print(json.dumps({'path': str(output), 'sha256': cp.digest(output)}, ensure_ascii=False))
        else:
            print(json.dumps(validate(args.design, json.load(sys.stdin), args.markdown), ensure_ascii=False))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()

"""Check explicit prompt layout instructions, never the resulting picture.

The text remains the authority: booleans and an execution_layout object cannot
stand in for the actual crop, panel and clothing instructions. These deliberately
bounded checks catch omitted/contradictory geometry; the controller still checks
the meaning of the prompt. 生成后交付用户人工反馈，不自动审图；显式请求图像审查时才看图。
"""
from __future__ import annotations

import re
import unicodedata

from prompt_canvas import canonical_ratio, resolve_canvas, validate_canvas_text


STAGES = {'avatar', 'expression', 'full_body', 'execution'}
_NEG = re.compile(r'(?:不|无|勿|避免|禁止|不得|不能|不要|not|never|without)\s*[^。；;!?！\n]{0,7}$', re.I)
_QUADRANTS = re.compile(r'(左上|上左|右上|上右|左下|下左|右下|下右)(?:格|角|区域)?\s*[:：]?')
_ALIASES = {'上左': '左上', '上右': '右上', '下左': '左下', '下右': '右下'}


def _normal(text):
    return unicodedata.normalize('NFKC', text).replace('×', 'x').replace('°', '度')


def _has(text, pattern):
    """Require an affirmative occurrence, excluding nearby explicit negation."""
    for match in re.finditer(pattern, text, re.I):
        prefix = re.split(r'[。；;!?！\n，,]', text[:match.start()])[-1]
        # These are positive garment/crop terms, not a negation of the next noun.
        prefix = re.sub(r'无头|无袖|无图案|不含头部', '', prefix)
        if not _NEG.search(prefix):
            return True
    return False


def _panels(text):
    found = {}
    matches = list(_QUADRANTS.finditer(text))
    for index, match in enumerate(matches):
        key = _ALIASES.get(match.group(1), match.group(1))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        # The layout paragraph ends before unrelated clothing prose. Otherwise
        # e.g. a small shoulder reveal becomes a claim about back-panel scale.
        paragraph = re.search(r'\n\s*\n', text[match.end():end])
        if paragraph:
            end = match.end() + paragraph.start()
        found.setdefault(key, []).append(text[match.end():end])
    return {key: '。'.join(values) for key, values in found.items()}


def _fraction(text, region):
    label = (r'上(?:方[^。；;\n]{0,5}(?:区|格)|面两格|区|排|部)'
             if region == 'upper' else r'下(?:方[^。；;\n]{0,5}(?:区|格)|面两格|区|排|部)')
    fraction = r'(?:1\s*/\s*3|三分之一|33(?:\.\d+)?\s*%)' if region == 'upper' else r'(?:2\s*/\s*3|三分之二|6[67](?:\.\d+)?\s*%)'
    return _has(text, label + r'[^。；;\n]{0,32}' + fraction)


def _execution(text):
    # Boots and shoes share a visible footwear endpoint. Do not require users
    # to replace correct garment nouns merely to satisfy literal keywords.
    text = text.replace('靴', '鞋')
    errors = []
    if not _has(text, r'2\s*[xX*]\s*2|两行两列|二行二列'):
        errors.append('execution: 正文须明确2×2两行两列，不能只声明四格')
    if not _fraction(text, 'upper') or not _fraction(text, 'lower'):
        errors.append('execution: 正文须明确上区约占总高1/3、下区约占总高2/3')
    if _has(text, r'上下(?:两区|两排|区域)?(?:各半|等高|均分)|(?:等大|等高|均等)(?:的)?四格|上(?:区|排)[^。；;\n]{0,20}(?:1/2|二分之一|50\s*%)'):
        errors.append('execution: 上下各半或等高四格与标准1/3、2/3版式矛盾')
    panels = _panels(text)
    for key in ('左上', '右上', '左下', '右下'):
        if key not in panels:
            errors.append(f'execution: 正文缺少{key}格的实际内容和裁切')
    upper_left, upper_right = panels.get('左上', ''), panels.get('右上', '')
    if not (_has(upper_left, r'正面') and _has(upper_left, r'头像|面孔|脸部|面部|头肩')):
        errors.append('execution: 左上须为正面头像，不能用全身或半侧脸替代')
    if not (_has(upper_right, r'45\s*度|四十五度') and _has(upper_right, r'头像|面孔|脸部|面部|头肩')):
        errors.append('execution: 右上须为约45°半侧面头像')
    for key, value in (('左上', upper_left), ('右上', upper_right)):
        if _has(value, r'全身|从头到鞋|90\s*度|九十度'):
            errors.append(f'execution: {key}格有与脸部格不符的全身或90°侧面指令')
    front = panels.get('左下', '')
    if not (_has(front, r'正面') and _has(front, r'服装|衣装|衣服')):
        errors.append('execution: 左下须展示正面服装主体')
    if not _has(front, r'放大|更近|近景|占满|满格|更满'):
        errors.append('execution: 左下须明确放大、更近的服装展示尺度')
    no_head = (_has(front, r'(?:头部|头脸|整颗头)[^。；;\n]{0,8}(?:完全|彻底)[^。；;\n]{0,5}(?:出画|不入画)')
               or _has(front, r'无头(?:的|放大)?正面|不含头部|头部完全不入画')
               or _has(front, r'头发[、，,与和及\s]*(?:下巴[、，,与和及\s]*嘴唇|嘴唇[、，,与和及\s]*下巴)[^。；;\n]{0,5}(?:全部|完全|彻底)出画'))
    if not no_head:
        errors.append('execution: 左下须明确头部彻底出画；metadata或“服装格”不能代替裁切正文')
    if not (_has(front, r'颈肩以下|颈部以下|肩颈以下|脖子以下|颈肩下方') and _has(front, r'鞋')):
        errors.append('execution: 左下范围须从颈肩以下到鞋，不能截在腰或腿中部')
    for label, pattern in (('肩', r'肩'), ('双臂', r'双臂|两臂|两条手臂|左右手臂'),
                           ('双手', r'双手|两手|两只手'), ('躯干', r'躯干|胸腰|上身'),
                           ('腿', r'双腿|两腿|腿部|腿'), ('鞋', r'鞋')):
        if not _has(front, pattern):
            errors.append(f'execution: 左下正文缺少完整{label}的可见要求')
    if not _has(front, r'完整|全部入画|均入画|全入画'):
        errors.append('execution: 左下须明确肩臂手躯干腿鞋完整入画')
    if _has(front, r'(?:头部|头顶|嘴唇|下巴|头发)[^。；;\n]{0,4}(?:入画|可见|露出|残留)|(?:裁至|裁到|只到|截止在?)(?:腰|膝|大腿|腿中部)|含头全身|带头全身'):
        errors.append('execution: 左下存在露头、嘴唇/下巴/头发残留或截断下肢的矛盾指令')
    back = panels.get('右下', '')
    if not (_has(back, r'背面|背视') and _has(back, r'完整|全身') and _has(back, r'头部|头顶|后脑|从头') and _has(back, r'鞋')):
        errors.append('execution: 右下须明确完整背面，从头部/后脑到鞋全部入画')
    if _has(back, r'无头|不含头|裁掉(?:头|鞋)|只到(?:腰|膝|大腿)|小(?:幅|尺寸)(?:的)?(?:背面|人物|全身)|小人物|缩小(?:人物|全身)'):
        errors.append('execution: 右下不能裁头、裁鞋或缩成过小的背面人物')
    return errors


def _attire(text, stage, inputs):
    exception = inputs.get('attire_exception')
    if isinstance(exception, dict) and exception.get('description') and exception.get('basis'):
        return [] if exception['description'] in text else ['模卡着装例外须在正文完整写出实际方案']
    if stage in {'avatar', 'expression'}:
        if _has(text, r'(?:服装|衣服|衣着)(?:完全)?不入画|仅露面部|只露面部'):
            return []
        if _has(text, r'白色[^。；;\n]{0,8}(?:运动)?背心|白(?:色)?(?:无图案|纯色)?(?:运动)?背心'):
            return []
        return ['头像/表情正文须明确服装不入画或白色模卡背心，不用metadata代替着装']
    if stage == 'full_body':
        if not (_has(text, r'白色[^。；;\n]{0,8}(?:运动)?背心|白(?:色)?(?:无图案|纯色)?(?:运动)?背心') and _has(text, r'短裤') and _has(text, r'赤脚|光脚')):
            return ['full_body: 人形模卡正文须有白色背心、短裤和赤脚，定制遮盖方案须有真实例外依据']
    return []


def _body_proportions(text):
    errors = []
    number = r'(?:\d+(?:\.\d+)?|[一二三四五六七八九十]+)'
    if not re.search(number + r'\s*(?:头身|个?头高)|(?:头高|头长)[^。；;\n]{0,16}(?:全高|身高)[^。；;\n]{0,12}' + number + r'|(?:全高|身高)[^。；;\n]{0,16}' + number + r'[^。；;\n]{0,8}(?:头高|头长)', text):
        errors.append('full_body: 正文须给头高与全高的明确比例端点')
    if not re.search(r'(?:肩峰|肩宽)[^。；;\n]{0,24}(?:骨盆|髋宽|髋部)[^。；;\n]{0,16}' + number, text):
        errors.append('full_body: 正文须给肩峰/肩宽与骨盆/髋宽的明确比例')
    if not re.search(r'(?:上段|上身|躯干)[^。；;\n]{0,35}(?:下段|下身|腿长|下肢)[^。；;\n]{0,20}' + number, text):
        errors.append('full_body: 正文须写同一测量体系的上段/下段比例，不能只有“长腿”')
    upper = re.search(r'(?:上段|上身|躯干)[^。；;\n]{0,5}(?:从|起于)?[^。；;\n，,]{1,15}(?:至|到|—|–)[^。；;\n，,]{1,15}', text)
    lower = re.search(r'(?:下段|下身|腿长|下肢)[^。；;\n]{0,5}(?:从|起于)?[^。；;\n，,]{1,15}(?:至|到|—|–)[^。；;\n，,]{1,15}', text)
    if not (upper and lower):
        errors.append('full_body: 上段和下段须分别写实际测量起止点，不能只写上下身数值比')
    return errors


def validate_entry(entry, inputs, morphology='human', asset_mode='individual'):
    """Return explicit-text contract errors; an empty list is not visual approval."""
    errors = []
    if not isinstance(entry, dict) or not isinstance(inputs, dict):
        return ['Prompt entry and actual inputs must be objects']
    stage, raw = entry.get('stage'), entry.get('text')
    if stage not in STAGES:
        return ['Prompt document stage must be avatar/expression/full_body/execution']
    if not isinstance(raw, str) or not raw.strip():
        return ['Prompt entry needs its actual complete text']
    text = _normal(raw)
    ensemble = asset_mode == 'ensemble'
    if asset_mode in {'ensemble', 'speaking_extra'} and stage != 'execution':
        errors.append('群演/群像仅需execution，不强套头像、表情、模卡四图链')
    try:
        if ensemble and not any(k in inputs for k in ('aspect_ratio',)):
            # Group count determines a suitable canvas; never guess it from body ratios.
            constraint = resolve_canvas(inputs, stage, use_default=False)
            if constraint is None:
                constraint = {'aspect_ratio': canonical_ratio(entry.get('aspect_ratio')), 'source': 'ensemble presentation'}
        else:
            constraint = resolve_canvas(inputs, stage)
        if 'aspect_ratio' in entry and canonical_ratio(entry['aspect_ratio']) != constraint['aspect_ratio']:
            errors.append('Prompt entry aspect_ratio differs from the actual task canvas')
        validate_canvas_text(raw, constraint)
    except ValueError as exc:
        errors.append(str(exc))
    human = morphology in {'human', 'humanoid'}
    if ensemble:
        if not (_has(text, r'同一(?:张)?画布|同画布|同一画面') and _has(text, r'完整全身|全身完整|从头到脚') and _has(text, r'从左到右|自左至右|左至右')):
            errors.append('ensemble: 正文须有同画布完整全身群像与从左到右槽位')
        if _has(text, r'2\s*[xX*]\s*2|无头正面'):
            errors.append('ensemble: 不采用独立人物四格或无头裁切')
        return errors
    if not human:
        if stage == 'execution' and not (_has(text, r'替代布局|多视图|多角度|2\s*[xX*]\s*2') and _has(text, r'轮廓|形态|结构') and _has(text, r'尺度|比例|大小')):
            errors.append('nonhuman: 正文须写适应该形态的替代视图、结构与尺度，不强套人脸/无头服装')
        return errors
    if stage in {'avatar', 'expression'}:
        errors.extend(_attire(text, stage, inputs))
        if not (_has(text, r'完整头部|头部完整|完整头顶|头顶[^。；;\n]{0,8}(?:完整|入画)') and _has(text, r'双肩|两肩')):
            errors.append('头像/表情正文须给完整头部和双肩的头肩取景')
    if stage == 'expression':
        sixteen = inputs.get('expression_grid') == 16
        wanted = r'4\s*[xX*]\s*4|十六格|16格' if sixteen else r'3\s*[xX*]\s*3|九宫格|9格'
        if not _has(text, wanted):
            errors.append('expression: 正文须明确3×3九宫格；16格只接受实际输入明确选择')
        if not (_has(text, r'从左到右|自左至右|从上到下|逐行|顺序') and _has(text, r'标签|标注|标明|文字')):
            errors.append('expression: 正文须说明表情格顺序与中文标签')
    elif stage == 'full_body':
        errors.extend(_attire(text, stage, inputs))
        errors.extend(_body_proportions(text))
        if not (_has(text, r'头(?:顶|部)?[^。；;\n]{0,12}(?:双脚|脚底|脚|足)') and _has(text, r'双手|两手') and _has(text, r'完整|全部入画|均入画')):
            errors.append('full_body: 正文须明确头到双脚及双手完整入画')
        if _has(text, r'无头正面|头部彻底出画|头部完全出画'):
            errors.append('full_body: 单独模卡必须含头，不能沿用执行图左下裁切')
    elif stage == 'execution':
        errors.extend(_execution(text))
    return errors


def validate_package(package, inputs=None, morphology='human', asset_mode='individual'):
    """Guard new formal submissions/generation; do not recheck historic approvals."""
    actual = dict(inputs or {})
    # Formal callers must derive morphology/mode from the real design/project.
    errors = []
    for item in package.get('prompts', []):
        entry = {'stage': package.get('stage'), 'text': item.get('text'),
                 'aspect_ratio': package.get('aspect_ratio')}
        errors.extend(validate_entry(entry, actual, morphology, asset_mode))
    if not package.get('prompts'):
        errors.append('Prompt package needs actual prompts[].text')
    return list(dict.fromkeys(errors))

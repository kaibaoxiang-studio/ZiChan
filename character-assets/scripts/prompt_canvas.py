"""Check an actual task's parsed canvas ratio, with a deliberately narrow fallback.

This module does not parse general requirements, negatives or conflicting
choices. The controller supplies aspect_ratio for those cases. Bare body ratios
are never candidates. Defaults apply only when there is no current constraint.
"""
from __future__ import annotations

import math
import re
import unicodedata


_RATIO = r'[1-9][0-9]*\s*:\s*[1-9][0-9]*(?![\d.:])'
_LABEL = r'(?:画幅(?:比例|宽高比)?|画布(?:比例|宽高比)?|aspect\s+ratio)'
_AFFIRM = r'(?:必须|采用|设为|设置为|使用|改为|改成|调整为|保持|固定|要求|为|是|用|must\s+be|should\s+be|is|use|set\s+to|[:,=])'
_NEGATIVE_PREFIX = re.compile(r'(?:不要|不能|不准|不是|并非|避免|别|不要求|不强制|不考虑|\bnot|\bnever|\bavoid)\s*(?:使用|采用|设为|设置为|用|use|adopt|set\s+to)?\s*$', re.I)
_CANDIDATE = re.compile(_LABEL + r'\s*(?:(?:' + _AFFIRM + r'|不要|不能|不准|不使用|不采用|不设为|不是|并非|not|must\s+not\s+be)\s*)*(' + _RATIO + r')', re.I)
_POSITIVE = re.compile(_LABEL + r'\s*(?:' + _AFFIRM + r'\s*)*(' + _RATIO + r')', re.I)
_CHOICE = re.compile(r'\s*(?:或|还是|/|、|和|与|及|or|and)\s*(' + _RATIO + r')', re.I)


def _ensure(condition, message):
    if not condition:
        raise ValueError(message)


def _normal(text):
    return unicodedata.normalize('NFKC', text)


def canonical_ratio(value):
    _ensure(isinstance(value, str) and re.fullmatch(_RATIO, _normal(value).strip()),
            'Task aspect_ratio must be one positive integer width:height ratio')
    width, height = (int(part.strip()) for part in _normal(value).split(':'))
    factor = math.gcd(width, height)
    return f'{width // factor}:{height // factor}'


def explicit_canvas_ratio(request):
    """Recognise only labelled, single-target, affirmative canvas statements.

    A labelled negative or a multi-target choice needs controller resolution.
    This returns no assertion for arbitrary N:M strings or body measurements.
    """
    if not isinstance(request, str):
        return {'status': 'absent'}
    found, unresolved = set(), False
    for clause in re.split(r'[。；;！!\n，,]', _normal(request)):
        for match in _CANDIDATE.finditer(clause):
            positive = _POSITIVE.match(clause, match.start())
            if not positive or _NEGATIVE_PREFIX.search(clause[:match.start()]):
                unresolved = True
                continue
            found.add(canonical_ratio(positive.group(1)))
            position = positive.end()
            while choice := _CHOICE.match(clause, position):
                found.add(canonical_ratio(choice.group(1)))
                position = choice.end()
    if unresolved or len(found) > 1:
        return {'status': 'needs_resolution'}
    if found:
        return {'status': 'explicit', 'aspect_ratio': next(iter(found))}
    return {'status': 'absent'}


def _actual_constraint(inputs):
    parsed = explicit_canvas_ratio(inputs.get('request'))
    if 'aspect_ratio' in inputs:
        ratio = canonical_ratio(inputs['aspect_ratio'])
        _ensure(parsed['status'] != 'explicit' or parsed['aspect_ratio'] == ratio,
                'Parsed task aspect_ratio contradicts the explicit canvas request')
        return {'aspect_ratio': ratio, 'source': 'task.aspect_ratio'}
    _ensure(parsed['status'] != 'needs_resolution',
            'Canvas request needs controller-resolved task aspect_ratio; negative or conflicting choices are not parsed')
    if parsed['status'] == 'explicit':
        return {'aspect_ratio': parsed['aspect_ratio'], 'source': 'explicit_canvas_request'}
    return None


def resolve_canvas(inputs, stage, design_inputs=None, use_default=True):
    """The current actual task wins; source framing fills gaps, then defaults."""
    current = _actual_constraint(inputs)
    if current:
        return current
    if design_inputs is not None:
        frozen = _actual_constraint(design_inputs)
        if frozen:
            return {**frozen, 'source': 'frozen_design.' + frozen['source']}
    if use_default:
        return {'aspect_ratio': '3:4' if stage in {'avatar', 'expression'} else '9:16',
                'source': 'stage_default'}
    return None


def rendered_canvas_ratios(text):
    """Find declared canvas notation, excluding incidental body N:M values."""
    text = _normal(text)
    parsed = explicit_canvas_ratio(text)
    _ensure(parsed['status'] != 'needs_resolution', 'Prompt canvas declaration is negative or conflicting')
    ratios = {parsed['aspect_ratio']} if parsed['status'] == 'explicit' else set()
    # Existing prompts also use N:M竖版 / N:M画幅 or start a paragraph with
    # N:M 单人头像. Those are presentation notation, not a ratio deep in prose.
    for match in re.finditer(r'(' + _RATIO + r')\s*(?=画幅|画布|正方形|方形|竖版|横版)', text):
        ratios.add(canonical_ratio(match.group(1)))
    for match in re.finditer(r'^\s*(' + _RATIO + r')(?=\s|[。；,，;]|$)', text):
        tail = text[match.end():].lstrip()
        if not re.match(r'(?:头身|肩髋|肩宽|髋宽|肢段|上下肢|body|shoulder|hip|head)', tail, re.I):
            ratios.add(canonical_ratio(match.group(1)))
    return ratios


def validate_canvas_text(text, constraint):
    _ensure(isinstance(text, str) and text.strip(), 'Prompt needs its full canvas text')
    actual = rendered_canvas_ratios(text)
    expected = constraint['aspect_ratio']
    _ensure(actual == {expected},
            f'Prompt canvas must be {expected} from {constraint["source"]}; found {sorted(actual)}')


def validate_canvas_package(package, constraint):
    _ensure(canonical_ratio(package.get('aspect_ratio')) == constraint['aspect_ratio'],
            f'Prompt aspect_ratio must be {constraint["aspect_ratio"]} from {constraint["source"]}')
    prompts = package.get('prompts')
    _ensure(isinstance(prompts, list) and prompts, 'Candidate needs complete prompts')
    for prompt in prompts:
        _ensure(isinstance(prompt, dict), 'Prompt must be an object')
        validate_canvas_text(prompt.get('text'), constraint)

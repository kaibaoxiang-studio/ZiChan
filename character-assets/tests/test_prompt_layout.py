"""Explicit geometry regressions; these fixtures are not picture approval."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prompt_layout import validate_entry, validate_package


AVATAR = '画幅3:4竖版。林澄完整头部和双肩入画，穿白色运动背心。圆角下颌，右侧分缝，发尾停在颌角，浅棕瞳孔。'
BODY = ('画幅9:16竖版。林澄从头顶到双脚及双手完整入画，白色运动背心、黑色短裤、赤脚。'
        '全高为7.3个头高，肩峰宽与骨盆宽之比1.25:1；'
        '上段从颈根到胯点、下段从胯点到脚底，两段比例1:1.3。')
EXECUTION = ('画幅9:16竖版，2×2参考板，上区约占画面高度三分之一，下区约占画面高度三分之二。'
             '左上：正面头像，脸型五官与发际清晰。右上：约45°半侧面头像，鼻梁和颧骨可读。'
             '左下：放大的正面服装主体，从颈肩以下到鞋，肩、双臂、双手、躯干、双腿和鞋完整入画；头部彻底出画。'
             '右下：完整背面，从头部、后脑发型和服装背面到鞋全部入画。')


class PromptLayoutTest(unittest.TestCase):
    def check(self, text, stage='execution', **inputs):
        return validate_entry({'stage': stage, 'text': text}, {'request': '只交当前完整提示词', **inputs})

    def test_standard_layouts_and_body_ratio_not_canvas(self):
        self.assertEqual(self.check(EXECUTION), [])
        self.assertEqual(self.check(AVATAR, 'avatar'), [])
        self.assertEqual(self.check(BODY, 'full_body'), [])
        expression = AVATAR + '。3×3九宫格，从左到右逐行排列；每格中文标签标注：平静、愉悦、悲伤、愤怒、惊讶、疑惑、厌恶、恐惧、轻蔑。'
        self.assertEqual(self.check(expression, 'expression'), [])

    def test_metadata_or_four_panels_alone_never_substitute_for_geometry(self):
        value = {'stage': 'execution', 'text': '画幅9:16，四格基本符合，布局正确。',
                 'layout_ok': True, 'execution_layout': {'headless': True, 'upper_fraction': 1 / 3}}
        errors = validate_entry(value, {'request': '执行图'})
        self.assertTrue(any('1/3' in error for error in errors))
        self.assertTrue(any('左下' in error for error in errors))

    def test_tianjin_wrong_half_height_and_truncated_lower_front_are_rejected(self):
        wrong = EXECUTION.replace('上区约占画面高度三分之一，下区约占画面高度三分之二', '上下两排各半')
        wrong = wrong.replace('从颈肩以下到鞋，肩、双臂、双手、躯干、双腿和鞋完整入画', '从颈肩以下只到腿中部，躯干和大腿入画')
        errors = self.check(wrong)
        self.assertTrue(any('1/3' in error for error in errors))
        self.assertTrue(any('双手' in error for error in errors))
        self.assertTrue(any('鞋' in error for error in errors))

    def test_negated_requirements_do_not_count_as_positive_layout(self):
        wrong = EXECUTION.replace('头部彻底出画', '不要头部彻底出画')
        self.assertTrue(any('彻底出画' in error for error in self.check(wrong)))
        wrong = EXECUTION.replace('约45°半侧面头像', '90°纯侧面头像')
        self.assertTrue(any('45' in error for error in self.check(wrong)))

    def test_explicit_residual_head_and_missing_back_head_are_rejected(self):
        wrong = EXECUTION.replace('头部彻底出画', '头部彻底出画，但下巴可见')
        self.assertTrue(any('矛盾' in error for error in self.check(wrong)))
        wrong = EXECUTION.replace('从头部、后脑发型和服装背面到鞋全部入画', '服装背面到鞋全部入画')
        self.assertTrue(any('右下' in error for error in self.check(wrong)))
        # An exclusion of a defect is different from an affirmative defect.
        correct = EXECUTION.replace('头部彻底出画', '头部彻底出画，禁止下巴可见')
        self.assertEqual(self.check(correct), [])
        self.assertEqual(self.check(EXECUTION.replace('放大的正面服装主体', '无头正面衣装放大图')), [])

    def test_actual_canvas_override_is_binding_but_body_ratio_is_not(self):
        self.assertTrue(self.check(EXECUTION, aspect_ratio='1:1'))
        self.assertEqual(self.check(EXECUTION.replace('9:16', '1:1'), aspect_ratio='1:1'), [])
        self.assertTrue(self.check(EXECUTION.replace('9:16', '1:1')))

    def test_model_card_clothes_and_measured_body_endpoints_are_required(self):
        self.assertTrue(self.check(BODY.replace('白色运动背心、黑色短裤、赤脚', '深蓝长袍和靴子'), 'full_body'))
        self.assertTrue(self.check(BODY.replace('肩峰宽与骨盆宽之比1.25:1', '修长身材'), 'full_body'))
        self.assertTrue(self.check(BODY.replace('上段从颈根到胯点、下段从胯点到脚底，两段比例1:1.3', '上身与下身比例1:1.3'), 'full_body'))
        self.assertTrue(self.check(BODY.replace('从头顶到双脚及双手完整入画', '无头正面从肩到脚入画'), 'full_body'))
        self.assertTrue(self.check(AVATAR.replace('完整头部和双肩入画', '半侧脸近景'), 'avatar'))

    def test_ensemble_and_nonhuman_keep_their_own_layouts(self):
        ensemble = {'stage': 'execution', 'aspect_ratio': '16:9',
                    'text': '画幅16:9横版，同一画布中三人完整全身，从左到右依次站立。'}
        self.assertEqual(validate_entry(ensemble, {'request': '三人群像'}, asset_mode='ensemble'), [])
        nonhuman = {'stage': 'execution', 'text': '画幅9:16竖版，采用多视图替代布局；外环轮廓、侧向机械结构和整体尺度明确。'}
        self.assertEqual(validate_entry(nonhuman, {'request': '机械环'}, morphology='nonhuman'), [])
        self.assertTrue(validate_entry({'stage': 'avatar', 'text': AVATAR}, {'request': '群像'}, asset_mode='ensemble'))

    def test_package_guard_uses_actual_text_not_metadata(self):
        value = {'stage': 'execution', 'aspect_ratio': '9:16', 'prompts': [{'text': EXECUTION}]}
        self.assertEqual(validate_package(value), [])
        value['prompts'][0]['text'] = '9:16 四格已满足所有裁切要求。'
        self.assertTrue(validate_package(value))


if __name__ == '__main__':
    unittest.main()

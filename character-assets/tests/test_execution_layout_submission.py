"""Guard new execution text without re-auditing historical pictures."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import character_project as cp
from test_prompt_layout import EXECUTION


class ExecutionSubmissionTest(unittest.TestCase):
    def package(self, text):
        return {'stage': 'execution', 'aspect_ratio': '9:16', 'prompts': [{'text': text}]}

    def test_new_legacy_and_speaking_extra_text_obeys_the_same_geometry(self):
        for mode in ('individual', 'speaking_extra'):
            cp.validate_new_execution_layout(self.package(EXECUTION), {'morphology': 'human'}, mode)
            with self.assertRaisesRegex(ValueError, '1/3'):
                cp.validate_new_execution_layout(self.package('9:16 四格布局正确。'),
                                                 {'morphology': 'human'}, mode)

    def test_actual_design_morphology_not_package_claim_controls_guard(self):
        data = self.package('9:16 仅四格。')
        data['morphology'] = 'nonhuman'
        with self.assertRaisesRegex(ValueError, '左下'):
            cp.validate_new_execution_layout(data, {'morphology': 'human'})
        cp.validate_new_execution_layout(data, {'morphology': 'nonhuman'})
        cp.validate_new_execution_layout(data, {'morphology': 'human'}, 'ensemble')

    def test_explicit_legacy_user_canvas_and_runtime_actual_canvas(self):
        data = self.package(EXECUTION.replace('9:16', '4:5'))
        data.update(aspect_ratio='4:5', aspect_ratio_explicit_user_override=True,
                    aspect_ratio_basis='用户本轮指定4:5')
        cp.validate_new_execution_layout(data, {'morphology': 'human'})
        with self.assertRaisesRegex(ValueError, 'ratio|canvas|画幅'):
            cp.validate_new_execution_layout(data, {'morphology': 'human'}, inputs={'aspect_ratio': '9:16'})

    def test_equivalent_face_zone_and_boot_endpoints_need_no_keyword_rewrite(self):
        text = EXECUTION.replace('上区约占画面高度三分之一，下区约占画面高度三分之二',
                                 '上方头像区只占整张图高度约三分之一；下方服饰区占约三分之二')
        text = text.replace('头部彻底出画', '头发、下巴、嘴唇全部出画').replace('鞋', '靴')
        cp.validate_new_execution_layout(self.package(text), {'morphology': 'human'})
        cp.validate_new_execution_layout(self.package(text + '\n\n夹克静态可小幅露肩，衣片按当前状态。'),
                                         {'morphology': 'human'})


if __name__ == '__main__':
    unittest.main()

"""Stage-specific model-card attire must survive prompt-package handoff."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugin_files" / "scripts"))
import character_project as project  # noqa: E402


def package(stage, profile, phrase):
    return {"stage": stage, "reference_attire": profile,
            "prompts": [{"id": "A", "text": f"模卡图；{phrase}。"}],
            "acceptance_checks": [f"核对{phrase}。"]}


class ModelCardAttireTests(unittest.TestCase):
    human = {"morphology": "human"}

    def test_avatar_face_only_and_upper_chest_tank_are_valid(self):
        face = package("avatar", "face_only", "以脸为主体，服装不入画")
        project.validate_model_card_attire(face, self.human)
        face["prompts"][0]["text"] = "模卡图，服装可见。"
        with self.assertRaisesRegex(ValueError, "must describe model-card attire"):
            project.validate_model_card_attire(face, self.human)

        upper_chest = package("avatar", "white_sports_tank", "3:4 竖版，以脸为主体，完整头部与双肩，上胸入画，白色运动背心")
        project.validate_model_card_attire(upper_chest, self.human)
        tank = package("avatar", "white_tank", "头肩至上胸近景，白色纯色背心")
        project.validate_model_card_attire(tank, self.human)

    def test_expression_inherits_avatar_or_records_fallback(self):
        avatar = package("avatar", "face_only", "以脸为主体，服装不入画")
        expression = package("expression", "face_only", "以脸为主体，服装不入画")
        project.validate_model_card_attire(expression, self.human)
        project.validate_expression_attire_transition(expression, avatar)
        expression = package("expression", "white_sports_tank", "白色运动背心")
        project.validate_model_card_attire(expression, self.human)
        with self.assertRaisesRegex(ValueError, "clothed fallback"):
            project.validate_expression_attire_transition(expression, avatar)
        expression["reference_attire_basis"] = "无服装入画的九宫格审查受阻"
        project.validate_model_card_attire(expression, self.human)
        project.validate_expression_attire_transition(expression, avatar)
        avatar["reference_attire"] = "white_tank"
        with self.assertRaisesRegex(ValueError, "must match approved avatar"):
            project.validate_expression_attire_transition(expression, avatar)

    def test_full_body_attire_is_not_avatar_profile(self):
        male = package("full_body", "white_tank_shorts_barefoot", "白色纯色背心、短裤、赤脚")
        project.validate_model_card_attire(male, self.human)
        female = package("full_body", "white_sports_tank_black_shorts_barefoot",
                         "白色运动背心、黑色运动短裤、赤脚")
        project.validate_model_card_attire(female, self.human)
        female["acceptance_checks"] = ["核对9:16全身图。"]
        with self.assertRaisesRegex(ValueError, "acceptance checks must verify"):
            project.validate_model_card_attire(female, self.human)
        male["reference_attire"] = "face_only"
        with self.assertRaisesRegex(ValueError, "stage-appropriate"):
            project.validate_model_card_attire(male, self.human)

    def test_exception_requires_description_and_basis(self):
        exception = package("full_body", "approved_exception", "素色短袖上衣与短裤、赤脚")
        with self.assertRaisesRegex(ValueError, "reference_attire_basis"):
            project.validate_model_card_attire(exception, self.human)
        exception["reference_attire_basis"] = "儿童角色需要充分覆盖"
        with self.assertRaisesRegex(ValueError, "reference_attire_description"):
            project.validate_model_card_attire(exception, self.human)
        exception["reference_attire_description"] = "素色短袖上衣与短裤、赤脚"
        project.validate_model_card_attire(exception, self.human)
        project.validate_model_card_attire({"stage": "full_body"}, {"morphology": "nonhuman"})


if __name__ == "__main__":
    unittest.main()

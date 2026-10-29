"""The full-body prompt must inherit measurable, approved body anchors."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import character_project as project  # noqa: E402


def anchored_card():
    anchors = {
        "measurement_frame": "正立、去鞋，头顶至足底为全高，正面投影作比例核对。",
        "head_body": {
            "mode": "numeric", "reference_points": ["头顶至下颏", "头顶至足底"],
            "relation": "头顶至足底约为头顶至下颏的7.2倍",
            "basis": "待审的写实角色设计选择，不由身高体重推算"},
        "shoulder_hip": {
            "mode": "landmark", "reference_points": ["双肩峰外缘", "骨盆外缘"],
            "relation": "双肩峰外缘宽度略窄于骨盆外缘宽度",
            "basis": "待审的角色剪影设计选择"},
        "torso_legs": {
            "mode": "numeric", "reference_points": ["头顶至裆点", "裆点至足底"],
            "relation": "裆点至足底约占全高47%，短于头顶至裆点",
            "basis": "待审的腿身关系设计选择"},
        "arm_segments": {
            "mode": "landmark", "reference_points": ["肘尖", "自然腰线", "腕骨"],
            "relation": "肘尖与自然腰线齐平，腕骨落在髋部下缘",
            "basis": "待审的正面站姿设计选择"},
        "leg_segments": {
            "mode": "landmark", "reference_points": ["裆点", "膝中心", "踝中心"],
            "relation": "膝中心略高于裆点至踝中心的中点",
            "basis": "待审的膝踝位置设计选择"},
    }
    relations = {key: value["relation"] for key, value in anchors.items() if isinstance(value, dict)}
    return {
        "schema_version": "CharacterDesignCardV2.2", "morphology": "human",
        "visual_details": {"body": {"frame_proportions": "；".join(
            relations[key] for key in ("head_body", "shoulder_hip", "torso_legs"))}},
        "body_form": {
            "proportion_anchors": anchors,
            "proportions": {key: relations[key] for key in
                            ("torso_legs", "arm_segments", "leg_segments")}},
    }


class BodyProportionGateTests(unittest.TestCase):
    def test_abstract_height_weight_card_is_rejected(self):
        card = anchored_card()
        card["visual_details"]["body"]["frame_proportions"] = (
            "165cm、48kg、瘦高型；肩线自然，腿修长但可信")
        card["body_form"].pop("proportion_anchors")
        with self.assertRaisesRegex(ValueError, "proportion_anchors is required"):
            project.validate_body_proportion_anchors(card)

    def test_measurable_and_landmark_anchored_card_is_accepted(self):
        project.validate_body_proportion_anchors(anchored_card())

    def test_c7_to_gluteal_fold_ratio_supports_longer_lower_body(self):
        card = anchored_card()
        anchors = card["body_form"]["proportion_anchors"]
        old_head = anchors["head_body"]["relation"]
        anchors["head_body"]["relation"] = "头顶至足底约为头顶至下颏的7.5倍"
        old_torso = anchors["torso_legs"]["relation"]
        anchors["torso_legs"] = {
            "mode": "numeric", "reference_points": ["第七颈椎至臀纹", "臀纹至足底"],
            "relation": "第七颈椎至臀纹与臀纹至足底约为48:52，臀纹至足底略长",
            "basis": "操作者选择的腿部略长设计方向"}
        details = card["visual_details"]["body"]
        details["frame_proportions"] = details["frame_proportions"].replace(
            old_head, anchors["head_body"]["relation"]).replace(
            old_torso, anchors["torso_legs"]["relation"])
        card["body_form"]["proportions"]["torso_legs"] = anchors["torso_legs"]["relation"]
        project.validate_body_proportion_anchors(card)

    def test_numeric_anchor_cannot_be_height_and_weight_only(self):
        card = anchored_card()
        anchor = card["body_form"]["proportion_anchors"]["head_body"]
        anchor["relation"] = "头顶至足底165cm，头顶至下颏与体重48kg一样写实"
        card["visual_details"]["body"]["frame_proportions"] = (
            card["visual_details"]["body"]["frame_proportions"].replace(
                "头顶至足底约为头顶至下颏的7.2倍", anchor["relation"]))
        with self.assertRaisesRegex(ValueError, "explicit ratio"):
            project.validate_body_proportion_anchors(card)

    def test_full_body_prompt_must_copy_approved_relations_and_checks(self):
        card = anchored_card()
        vague_prompt = {
            "prompts": [{"id": "A", "text": "165cm、48kg，腿修长但可信，正面站立。"}],
            "acceptance_checks": ["身体比例写实可信。"]}
        with self.assertRaisesRegex(ValueError, "must carry approved"):
            project.validate_full_body_prompt_proportions(vague_prompt, card)
        package = copy.deepcopy(vague_prompt)
        anchors = card["body_form"]["proportion_anchors"]
        core = [anchors[key]["relation"] for key in ("head_body", "shoulder_hip", "torso_legs")]
        package["prompts"][0]["text"] = "；".join(core)
        with self.assertRaisesRegex(ValueError, "acceptance checks"):
            project.validate_full_body_prompt_proportions(package, card)
        package["acceptance_checks"] = [core[0], core[2]]
        project.validate_full_body_prompt_proportions(package, card)

    def test_full_body_canvas_defaults_to_9_by_16(self):
        package = {
            "schema_version": "CharacterPromptPackageV1", "character_id": "CHR-001",
            "variant_id": "base", "stage": "full_body", "target_model": "gpt-image-2.5",
            "design_card_sha256": "sample-sha", "anchor_images": {}, "reference_images": [],
            "prompts": [{"id": "A", "text": "单人头到鞋完整，9:16 竖版全身图。"}],
            "acceptance_checks": ["核对9:16竖版且头脚完整。"],
            "head_visible": True, "feet_visible": True}
        with self.assertRaisesRegex(ValueError, "needs aspect_ratio"):
            project._validate_record("prompt-package", package, {}, "CHR-001", "base", "full_body")
        package["aspect_ratio"] = "3:4"
        with self.assertRaisesRegex(ValueError, "aspect_ratio_basis"):
            project._validate_record("prompt-package", package, {}, "CHR-001", "base", "full_body")
        package["aspect_ratio_basis"] = "操作者明确指定 3:4"
        with self.assertRaisesRegex(ValueError, "explicit user override"):
            project._validate_record("prompt-package", package, {}, "CHR-001", "base", "full_body")
        package["aspect_ratio"] = "9:16"
        del package["aspect_ratio_basis"]
        project._validate_record("prompt-package", package, {}, "CHR-001", "base", "full_body")
        package["prompts"][0]["text"] = "单人头到鞋完整的竖版全身图。"
        with self.assertRaisesRegex(ValueError, "must state canvas ratio"):
            project._validate_record("prompt-package", package, {}, "CHR-001", "base", "full_body")
        package["prompts"][0]["text"] = "单人头到鞋完整，9:16 竖版全身图。"
        package["acceptance_checks"] = ["核对头脚完整。"]
        with self.assertRaisesRegex(ValueError, "must verify canvas ratio"):
            project._validate_record("prompt-package", package, {}, "CHR-001", "base", "full_body")


if __name__ == "__main__":
    unittest.main()

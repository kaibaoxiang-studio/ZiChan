"""Regression checks for the V2.2 design handoff gate."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "plugin_files" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import character_project as project  # noqa: E402


class V22HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.handoffs = self.root / "drafts" / "specialists"
        self.handoffs.mkdir(parents=True)
        self.specialist = "character-feature-focus"
        self.route = {
            "schema_version": "CharacterSpecialistRouteV1", "character_id": "CHR-001",
            "variant_id": "base", "specialists": {
                key: {"decision": "invoke" if key == self.specialist else "skip",
                      "trigger": "当前角色面孔与近邻趋同" if key == self.specialist else "现有证据已足够",
                      "reason": "需要明确主锚点" if key == self.specialist else "现阶段不产生新提案"}
                for key in project.SPECIALIST_DOMAINS_V22}}
        self.proposal = {
            "schema_version": "CharacterSpecialistProposalV1.1",
            "specialist": self.specialist, "character_id": "CHR-001", "variant_id": "base", "scope": "成年基础造型",
            "facts": [], "unresolved": [], "not_applicable_reason": None,
            "options": [{"id": "A", "visible_design": "轻微不对称的眉眼与有方向的发束",
                         "design_elements": [
                             {"part": "眉眼", "visible_feature": "左眉尾略低", "placement_or_structure": "左眼上缘", "basis": "待审设计"},
                             {"part": "发际", "visible_feature": "右侧短发束", "placement_or_structure": "沿右额角", "basis": "待审设计"}],
                         "rationale": "便于近景辨认", "comparison_difference": "近邻为对称眉眼",
                         "production_check": "核对半侧脸"}],
            "recommended_option_id": "A", "single_option_reason": "现阶段只需一组候选供测试"}
        self.route_path = self.handoffs / "route.json"
        self.proposal_path = self.handoffs / "feature.json"
        self._write(self.route_path, self.route)
        self._write(self.proposal_path, self.proposal)
        details = {domain: {field: f"{domain} 的 {field} 采用可复现的具体结构" for field in fields}
                   for domain, fields in project.DETAIL_FIELDS.items()}
        coverage = {key: {"status": "not_needed", "decision": "现有结构足够"}
                    for key in project.SPECIALIST_DOMAINS_V22}
        coverage[self.specialist] = {
            "status": "used", "decision": "选择 A 的左眉尾与发束",
            "proposal_ref": "drafts/specialists/feature.json",
            "proposal_sha256": project.digest(self.proposal_path),
            "selected_option_id": "A", "applied_fields": ["face.brow_eyes", "hair.hairline_part"],
            "applied_elements": [{"field": "face.brow_eyes", "element_index": 0},
                                 {"field": "hair.hairline_part", "element_index": 1}]}
        self.card = {
            "schema_version": "CharacterDesignCardV2.2", "character_id": "CHR-001",
            "variant_id": "base", "morphology": "human", "facts": [], "inferences": [],
            "approved_choices": [], "identity_invariants": [], "appearance": {}, "costume": {},
            "unresolved": [], "visual_details": details, "specialist_coverage": coverage,
            "recognition_axes": {axis: "具体可见的识别关系" for axis in project.RECOGNITION_AXES},
            "differentiation_review": {"closest_character_ids": [], "shared_features": [],
                                        "distinct_features": [], "realism_check": "与比较组并排审查"},
            "route_ref": "drafts/specialists/route.json",
            "route_sha256": project.digest(self.route_path),
            "feature_focus": {
                "core_sentence": "总在收住急促的表情", "primary_anchors": [
                    {"part": "眉眼", "geometry": "左眉尾略低", "basis": "待审选择", "visible_views": ["front", "avatar"]},
                    {"part": "发际", "geometry": "右额角短发束", "basis": "待审选择", "visible_views": ["front", "side"]}],
                "quiet_features": [{"part": "鼻唇", "decision": "维持普通比例，不争焦点"}],
                "imperfection_policy": {"status": "existing", "detail": "眉尾轻微不对称", "basis": "已选方案"},
                "view_checks": {"silhouette": {"status": "not_tested", "evidence": "尚未成图"},
                                "occlusion": {"status": "not_tested", "evidence": "尚未成图"}}},
            "body_form": {
                "proportions": {"torso_legs": "躯干与腿接近，腿稍长", "arm_segments": "前臂与上臂接近",
                                "leg_segments": "小腿与大腿接近"},
                "masses": {"head": "头部轻前倾", "ribcage": "胸腔窄而稳定", "pelvis": "盆腔略后收",
                           "relationships": "胸盆扭转幅度很小"},
                "views": {"front": "肩胯对齐", "side": "头略前伸", "back": "肩胛线偏窄"},
                "action_check": {"stance": "重心落双足中线", "script_action": "提起轻箱",
                                 "mobility_result": "肘肩活动范围足够", "test_status": "not_tested"}}}

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _write(path, data):
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def validate(self, card=None):
        card = card or self.card
        project._validate_record("design-card", card, {}, "CHR-001", "base")
        project.validate_design_handoffs(card, self.root)

    def test_valid_real_handoff(self):
        self.validate()

    def test_fabricated_or_mutated_proposal_rejected(self):
        self.proposal["character_id"] = "CHR-002"
        self._write(self.proposal_path, self.proposal)
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            self.validate()
        self.card["specialist_coverage"][self.specialist]["proposal_sha256"] = project.digest(self.proposal_path)
        with self.assertRaisesRegex(ValueError, "target mismatch"):
            self.validate()

    def test_missing_option_and_route_mismatch_rejected(self):
        card = copy.deepcopy(self.card)
        card["specialist_coverage"][self.specialist]["selected_option_id"] = "B"
        with self.assertRaisesRegex(ValueError, "Selected option missing"):
            self.validate(card)
        self.route["specialists"][self.specialist]["decision"] = "skip"
        self._write(self.route_path, self.route)
        card = copy.deepcopy(self.card)
        card["route_sha256"] = project.digest(self.route_path)
        with self.assertRaisesRegex(ValueError, "Route/coverage mismatch"):
            self.validate(card)

    def test_path_escape_and_missing_element_rejected(self):
        card = copy.deepcopy(self.card)
        card["specialist_coverage"][self.specialist]["proposal_ref"] = "../feature.json"
        with self.assertRaisesRegex(ValueError, "project-relative"):
            self.validate(card)
        card = copy.deepcopy(self.card)
        card["specialist_coverage"][self.specialist]["applied_elements"][0]["element_index"] = 99
        with self.assertRaisesRegex(ValueError, "element index"):
            self.validate(card)

    def test_focus_and_form_required(self):
        card = copy.deepcopy(self.card)
        del card["body_form"]["masses"]["pelvis"]
        with self.assertRaisesRegex(ValueError, "pelvis"):
            self.validate(card)

    def test_legacy_v21_card_still_readable(self):
        card = copy.deepcopy(self.card)
        card["schema_version"] = "CharacterDesignCardV2.1"
        del card["specialist_coverage"][self.specialist]
        card.pop("feature_focus")
        card.pop("body_form")
        card.pop("route_ref")
        card.pop("route_sha256")
        project._validate_record("design-card", card, {}, "CHR-001", "base")


if __name__ == "__main__":
    unittest.main()

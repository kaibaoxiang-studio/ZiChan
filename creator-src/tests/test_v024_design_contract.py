"""New world and facial-surface contract without regressing V2.2 cards."""
from __future__ import annotations

import copy
import unittest

import test_v022_contract as fixtures

project = fixtures.project


class V24DesignContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.V22HandoffTests("test_valid_real_handoff")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.card = copy.deepcopy(self.fixture.card)
        self.card["schema_version"] = "CharacterDesignCardV2.4"
        self.card["world_influences"] = {
            "environment": "室内纸张工作与偶尔室外行走",
            "technology": "仅使用手工文书工具",
            "resources_and_access": "常用纸墨可取得",
            "appearance_effects": [{"feature": "手指有淡墨迹", "mechanism": "日常文书接触",
                                    "basis": "获批准的角色职业", "evidence_status": "approved_choice"}]}
        self.card["facial_surface"] = {"stable_marks": [], "applied_decoration": [],
                                       "temporary_effects": [],
                                       "absence_or_focus_decision": "面部无需新增装饰，保留眉眼锚点"}
        for specialist in ("character-world-appearance-design", "character-face-decoration-design"):
            self.card["specialist_coverage"][specialist] = {
                "status": "not_needed", "decision": "本轮无进一步造型缺口"}
            self.fixture.route["specialists"][specialist] = {
                "decision": "skip", "trigger": "已核对世界和面部状态",
                "reason": "现有设计足够"}
        self.fixture._write(self.fixture.route_path, self.fixture.route)
        self.card["route_sha256"] = project.digest(self.fixture.route_path)

    def validate(self):
        project._validate_record("design-card", self.card, {}, "CHR-001", "base")
        project.validate_design_handoffs(self.card, self.fixture.root)

    def test_world_face_fields_and_thirteen_specialist_route(self):
        self.validate()
        self.card["facial_surface"]["stable_marks"].append({"feature": "新疤"})
        with self.assertRaisesRegex(ValueError, "placement"):
            self.validate()

    def test_unsupported_world_inference_rejected(self):
        self.card["world_influences"]["appearance_effects"][0]["evidence_status"] = "guess"
        with self.assertRaisesRegex(ValueError, "approved choices"):
            self.validate()


if __name__ == "__main__":
    unittest.main()

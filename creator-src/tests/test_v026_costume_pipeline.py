"""V3 costume contracts and V2 migration; synthetic bytes check state, not image quality."""
from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from test_v025_phased_runtime import PhasedRuntimeTests, ROOT, cp
import test_v024_pipeline as v24


class CostumeV3Tests(unittest.TestCase):
    def setUp(self):
        self.h = PhasedRuntimeTests("test_default_and_full_context_coverage_and_actionable_tasks")
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        state = self.h.state()
        state["pipeline_version"] = 3
        cp.write_json(self.h.root / "project.json", state)

    def direction(self):
        self.h.setup_brief()
        state = self.h.state()
        key = f"design-brief:{self.h.character}:base"
        brief = cp.read_json(self.h.root / state["records"][key]["path"])
        for name in ("character-costume-style-design", "character-costume-cut-design",
                     "character-costume-color-design", "character-costume-material-design"):
            brief["specialist_plan"][name] = {"status": "defer", "reason": "到服饰状态时具体深化"}
        self.h.submit("design-brief", brief)
        self.h.approve("design-brief")

    def bible(self):
        state = self.h.state()
        char = self.h.character
        refs = {k: state["records"][k]["sha256"] for k in
                (f"design-brief:{char}:base", f"stage-design:identity:{char}:base",
                 f"stage-design:body:{char}:base")}
        text = "维修者把实际劳动痕迹融入正式衣装，线条依旧允许双臂转动"
        data = {"schema_version": "CostumeStyleBibleV1", "character_id": char, "variant_id": "base",
                "parent_refs": refs, "tier": "full", "new_lore_policy": "none", "unresolved": [],
                **{x: text for x in ("wearing_thesis", "world_translation", "signature_silhouette",
                    "cut_grammar", "palette_grammar", "material_grammar", "recognition_anchor",
                    "wearing_habits", "state_logic", "physical_and_camera_rules")},
                "state_matrix": [{"variant_id": x, "narrative_function": text,
                                  "silhouette_shift": text, "anchor_continuity": text} for x in ("S01", "S02")]}
        self.h.submit("costume-bible", data)
        self.h.approve("costume-bible")
        return data

    def costume(self, variant, payload):
        state = self.h.state()
        char = self.h.character
        refs = {k: state["records"][k]["sha256"] for k in cp.phased.required_parents(state, char, "costume", variant)}
        direction = payload["costume_direction"]
        knowledge = ROOT / "character-assets/references/knowledge/character-costume-designer/costume-deep.md"
        work = {}
        mapping = {"character-costume-style-design": "front_structure",
                   "character-costume-cut-design": "cut_and_fastening",
                   "character-costume-color-design": "color_placement",
                   "character-costume-material-design": "material_behavior"}
        for specialist, field in mapping.items():
            work[specialist] = {"mode": "inline", "decision": "按人物劳动语法设计本状态衣装",
                "task": self.h.task(), "activation_reason": "进入服饰状态阶段",
                "rules_applied": ["具体部位、结构与剧情依据"],
                "knowledge_refs": [{"path": "references/knowledge/character-costume-designer/costume-deep.md",
                                    "sha256": cp.digest(knowledge)}],
                "results": [{"field": f"costume_direction.{field}", "visible_result": direction[field],
                             "basis": "人物方向和当前状态", "evidence_status": "creative_choice"}]}
        work["character-costume-accessory-design"] = {"mode": "not_needed", "decision": "工作场景不加附加饰物，以免妨碍动作"}
        data = {"schema_version": "CharacterStageDesignV1", "character_id": char, "variant_id": variant,
                "scope": "costume", "parent_refs": refs, "payload": payload,
                "specialist_execution": work, "deferred_dimensions": [], "unresolved": []}
        with patch.object(cp, "__file__", str(ROOT / "character-assets/scripts/character_project.py")):
            self.h.submit("stage-design", data, "costume", variant)
        self.h.approve("stage-design", "costume", variant)
        return data

    def execution(self, variant):
        state = self.h.state()
        char = self.h.character
        basis = {k: state["records"][k]["sha256"] for k in cp.phased.basis_keys(char, variant, "execution", state)}
        anchors = {s: cp._checked_image(self.h.root, state, s, char, "base")["sha256"] for s in cp.IDENTITY_STAGES}
        pkg = {"schema_version": "CharacterPromptPackageV1", "character_id": char, "variant_id": variant,
               "stage": "execution", "target_model": "gpt-image-2.5", "purpose": "production",
               "design_basis": {"records": basis}, "anchor_images": anchors, "reference_images": [],
               "prompts": [{"id": "推荐", "text": "9:16 竖版四格，上方正面脸与45°脸，下方放大无头正面服饰与完整背面"}],
               "acceptance_checks": ["9:16 竖版像素比例", "服饰正背结构与剪裁一致"],
               "aspect_ratio": "9:16", "variant_name": cp.variant_name(state, char, variant),
               "morphology": "human", "layout": {"top_left": "front_face", "top_right": "three_quarter_face_45",
                   "bottom_left": "headless_enlarged_front_costume", "bottom_right": "complete_back_head_to_shoes"}}
        wrong_ratio = copy.deepcopy(pkg)
        wrong_ratio["aspect_ratio"] = "16:9"
        wrong_ratio["aspect_ratio_basis"] = "测试不允许擅自改画幅"
        with self.assertRaisesRegex(ValueError, "explicit user override"):
            self.h.submit("prompt-package", wrong_ratio, variant=variant, stage="execution")
        wrong_layout = copy.deepcopy(pkg)
        wrong_layout["layout"]["bottom_left"] = "small_full_body_front"
        with self.assertRaisesRegex(ValueError, "four-panel layout"):
            self.h.submit("prompt-package", wrong_layout, variant=variant, stage="execution")
        self.h.submit("prompt-package", pkg, variant=variant, stage="execution")
        self.h.seq += 1
        image_path = self.h.work / f"synthetic-v3-{self.h.seq}.png"
        image_path.write_bytes(f"synthetic-v3:{self.h.seq}".encode())
        image = cp.cmd_import_image(NS(project_root=str(self.h.root), character_id=char,
                                       variant_id=variant, stage="execution", path=str(image_path)))
        report = {"schema_version": "CharacterImageReviewV1", "image_sha256": image["sha256"],
                  "stage": "execution", "verdict": "pass",
                  **{k: [] for k in ("factual_conflicts", "identity_issues", "layout_issues",
                                    "label_issues", "blocking_issues", "adoption_proposals")}}
        cp.cmd_submit_review(NS(project_root=str(self.h.root), image_id=image["id"], file=self.h.save(report)))
        cp.cmd_approve_image(NS(project_root=str(self.h.root), image_id=image["id"], operator="测试操作者"))
        return image

    def test_v3_one_image_per_state_and_local_invalidation(self):
        self.direction()
        identity, body, costume = self.h.payloads()
        self.h.stage("identity", identity)
        self.h.prompt_image("avatar")
        self.h.prompt_image("expression")
        self.h.stage("body", body)
        self.h.prompt_image("full_body")
        self.bible()
        state_payloads = {}
        for variant in ("S01", "S02"):
            payload = copy.deepcopy(costume)
            phrase = f"{variant} 工作衣前胸斜切两片，下摆错层但不妨碍维修动作"
            payload["costume_direction"] = {x: phrase for x in
                ("script_requirement", "narrative_function", "front_structure", "back_structure",
                 "cut_and_fastening", "layering", "color_placement", "material_behavior",
                 "recognition_focus", "mobility_and_camera", "state_continuity", "makeup_and_hair")}
            payload["costume_direction"].update(evidence_status="mixed", script_refs=["EP-01-S01"])
            state_payloads[variant] = payload
            self.costume(variant, payload)
            cp.phased.compile_card(cp._runtime(), NS(project_root=str(self.h.root), character_id=self.h.character, variant_id=variant))
            self.execution(variant)
        state = self.h.state()
        self.assertEqual(state["pipeline_version"], 3)
        self.assertEqual({x["stage"] for x in state["images"] if x.get("approval")}, set(cp.V3_STAGES))
        self.assertFalse(any(x["stage"] == "costume_design" for x in state["images"]))
        self.assertEqual(len([x for x in state["images"] if x["stage"] == "execution" and x.get("approval")]), 2)
        with self.assertRaisesRegex(ValueError, "not available"):
            cp.cmd_plan(NS(project_root=str(self.h.root), character_id=[self.h.character], variant_id=None, stage="costume_design"))
        output = self.h.work / "v3-pack"
        with patch.object(cp, "__file__", str(ROOT / "character-assets/scripts/character_project.py")):
            cp.cmd_package(NS(project_root=str(self.h.root), character_id=self.h.character, variant_id="S02", output=str(output)))
        self.assertEqual(cp.read_json(output / "manifest.json")["schema_version"], "CharacterAssetPackV3")
        changed = copy.deepcopy(state_payloads["S01"])
        changed["costume_direction"]["front_structure"] += "；袖口再收窄一指宽"
        self.costume("S01", changed)
        after_state_change = self.h.state()
        cp._checked_image(self.h.root, after_state_change, "execution", self.h.character, "S02")
        with self.assertRaisesRegex(ValueError, "approved"):
            cp._checked_image(self.h.root, after_state_change, "execution", self.h.character, "S01")
        bible_key = f"costume-bible:{self.h.character}:base"
        bible = cp.read_json(self.h.root / after_state_change["records"][bible_key]["path"])
        bible["wearing_thesis"] += "；此版加入新的穿着习惯"
        self.h.submit("costume-bible", bible)
        self.h.approve("costume-bible")
        with self.assertRaisesRegex(ValueError, "approved"):
            cp._checked_image(self.h.root, self.h.state(), "execution", self.h.character, "S02")

    def test_explicit_upgrade_preserves_identity_approvals(self):
        state = self.h.state()
        state["pipeline_version"] = 2
        cp.write_json(self.h.root / "project.json", state)
        self.h.setup_brief()
        identity, body, _ = self.h.payloads()
        self.h.stage("identity", identity)
        image = self.h.prompt_image("avatar")
        expression = self.h.prompt_image("expression")
        self.h.stage("body", body)
        full_body = self.h.prompt_image("full_body")
        blocked_state = self.h.state()
        synthetic_approved_garment = copy.deepcopy(next(x for x in blocked_state["images"] if x["id"] == image["id"]))
        synthetic_approved_garment.update(id="historical-approved-costume", stage="costume_design", variant_id="S01")
        blocked_state["images"].append(synthetic_approved_garment)
        cp.write_json(self.h.root / "project.json", blocked_state)
        with self.assertRaisesRegex(ValueError, "Approved garment images"):
            cp.cmd_upgrade_pipeline(NS(project_root=str(self.h.root), operator="测试操作者"))
        blocked_state["images"].pop()
        cp.write_json(self.h.root / "project.json", blocked_state)
        result = cp.cmd_upgrade_pipeline(NS(project_root=str(self.h.root), operator="测试操作者"))
        self.assertEqual(set(result["preserved_approved_identity_images"]),
                         {image["id"], expression["id"], full_body["id"]})
        self.assertEqual(self.h.state()["pipeline_version"], 3)
        for stage in cp.IDENTITY_STAGES:
            cp._checked_image(self.h.root, self.h.state(), stage, self.h.character, "base")


class CompleteV2MigrationTests(unittest.TestCase):
    def test_complete_v2_identity_images_keep_historical_basis(self):
        fixture = v24.V024PipelineTests("test_dependency_plan_names_and_state_package")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.prepare_decisions()
        images = [fixture.stage_image(stage) for stage in v24.cp.IDENTITY_STAGES]
        result = v24.cp.cmd_upgrade_pipeline(NS(project_root=str(fixture.root), operator="测试操作者"))
        self.assertEqual(result["pipeline_version"], 3)
        self.assertIn("approved identity/body backfill", result["requires"])
        state = v24.cp.read_json(fixture.root / "project.json")
        self.assertEqual(state["design_progression"], "phased")
        self.assertEqual(set(result["preserved_approved_identity_images"]), {x["id"] for x in images})
        for stage in v24.cp.IDENTITY_STAGES:
            image = v24.cp._checked_image(fixture.root, state, stage, fixture.character["id"], "base")
            self.assertIn("migration_legacy_identity", image)


if __name__ == "__main__":
    unittest.main()

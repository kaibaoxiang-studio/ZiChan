"""Regression for the one-image route of non-speaking extras."""
import copy
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace as NS

from test_v025_phased_runtime import cp
import ensemble_assets as ensemble


class EnsembleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.root = self.work / "project"
        script = {"schema_version": "standardized_screenplay_v1", "episodes": [{"id": "E1", "scenes": [
            {"id": "1-1", "blocks": [
                {"type": "action", "text": "三名持弓者在崖边列队。", "source_refs": ["P1"]},
                {"type": "dialogue", "speaker": "传令员", "text": "撤离！", "source_refs": ["P2"]}]}]}]}
        assets = {"schema_version": "screenplay_assets_v1", "characters": [
            {"id": "CHR-001", "name": "持弓者", "tier": "群演",
             "states": [{"id": "S01", "name": "崖边常态", "evidence": [
                 {"source_refs": ["P1"], "text": "三名持弓者在崖边列队。"}]}]},
            {"id": "CHR-002", "name": "传令员", "tier": "群演",
             "states": [{"id": "S01", "name": "常态", "evidence": [{"source_refs": ["P2"]}]}]}]}
        self.script = self.work / "script.json"
        self.assets = self.work / "assets.json"
        cp.write_json(self.script, script)
        cp.write_json(self.assets, assets)
        cp.cmd_init(NS(project_root=str(self.root), project_id="ensemble-test", snapshot=None,
                       screenplay=str(self.script), asset_table=str(self.assets),
                       scene_log=None, design_progression="phased"))
        self.seq = 0

    def save(self, data):
        self.seq += 1
        path = self.work / f"draft-{self.seq}.json"
        cp.write_json(path, data)
        return str(path)

    def state(self):
        return cp.read_json(self.root / "project.json")

    def submit(self, kind, data, character=None, variant="base", stage=None):
        return cp.cmd_submit(NS(project_root=str(self.root), kind=kind, file=self.save(data),
                                character_id=character, variant_id=variant, stage=stage, scope=None))

    def approve(self, kind, character=None, variant="base"):
        return cp.cmd_approve_record(NS(project_root=str(self.root), kind=kind,
                                        character_id=character, variant_id=variant, scope=None,
                                        operator="测试操作者"))

    def foundation(self):
        listing = cp.phased.context_units(cp._runtime(), NS(project_root=str(self.root), source=None, output=None))
        units = [{"unit_id": x["unit_id"], "sha256": x["sha256"]} for x in listing["units"]]
        context = {"schema_version": "ScriptContextV1", "source_sha256": listing["source_sha256"],
                   "source_kind": "screenplay", "read_units": units,
                   "synopsis": "三名持弓者警戒，传令员要求撤离。",
                   "world_summary": "崖道与弓的活动要求", "narrative_structure": "警戒后撤离",
                   "character_index": [{"character_id": x["id"], "name": x["name"],
                                        "role_in_story": "警戒或传令", "arc_summary": "执行任务",
                                        "relationships": "同场协作",
                                        "evidence_unit_ids": [z["unit_id"] for z in units]}
                                       for x in self.state()["roster"]], "unresolved": []}
        self.submit("script-context", context)
        self.submit("visual-bible", {"schema_version": "ProjectVisualBibleV1",
                    "project_id": "ensemble-test", "world_rules": ["弓手需要活动袖"],
                    "style": {"medium": "写实摄影"}, "evidence": [{"claim": "三人持弓",
                    "source_refs": ["P1"]}], "unresolved": []})
        self.approve("visual-bible")
        self.submit("cast-plan", {"schema_version": "CastPlanV1", "characters": [
                    {"id": x["id"], "design_distinction": "不同职责与体态"}
                    for x in self.state()["roster"]], "unresolved": []})
        self.approve("cast-plan")

    def design(self):
        state = self.state()
        return {"schema_version": "GroupEnsembleDesignV1", "character_id": "CHR-001",
                "variant_id": "S01", "parent_refs": {x: state["records"][x]["sha256"]
                for x in ("script-context", "visual-bible", "cast-plan")},
                "narrative_function": "崖边三名弓手警戒",
                "world_style_translation": "沿用获批写实摄影和崖道活动衣袖",
                "shared_visual_grammar": "同组深色哑光外衣与弓，袖口可活动",
                "variation_logic": "三人脸宽、肩宽、发束与站姿不同",
                "quantity_basis": "剧本 P1 明确三名", "quantity_status": "script_explicit",
                "script_count": 3, "member_count": 3, "source_refs": ["P1"],
                "arrangement": "左中右单排，全身不重叠，道具各归其主",
                "members": [{"slot": f"G{i}", "body_and_posture": f"第{i}人肩宽站姿",
                             "face_and_hair": f"第{i}人脸形发束",
                             "costume_structure": f"第{i}人袖口腰带",
                             "color_and_material": f"第{i}人深色哑光布料",
                             "action_or_prop": f"第{i}人持自己的弓",
                             "evidence_status": "mixed"} for i in range(1, 4)],
                "new_lore_policy": "none", "unresolved": []}

    def prompt(self):
        state = self.state()
        return {"schema_version": "CharacterPromptPackageV1", "character_id": "CHR-001",
                "variant_id": "S01", "variant_name": "崖边常态", "stage": "execution",
                "target_model": "gpt-image-2.5", "purpose": "production", "morphology": "group",
                "aspect_ratio": "16:9", "aspect_ratio_basis": "三人全身同框的辨识度",
                "design_basis": {"records": {"ensemble-design:CHR-001:S01":
                    state["records"]["ensemble-design:CHR-001:S01"]["sha256"]}},
                "anchor_images": {}, "reference_images": [],
                "layout": {"type": "ensemble_lineup", "single_canvas": True, "full_body": True,
                           "member_count": 3, "ordered_slots": ["G1", "G2", "G3"]},
                "prompts": [{"id": "推荐", "text": "16:9 横版3人全身，沿用获批写实摄影和崖道活动衣袖风格；G1、G2、G3依次站立"}],
                "acceptance_checks": ["16:9 画幅", "人数3", "全身可见", "顺序 G1 G2 G3",
                                      "风格一致", "服饰结构和道具归属清楚"]}

    def test_one_group_image_and_dialogue_route(self):
        self.foundation()
        plan = cp.cmd_plan(NS(project_root=str(self.root), character_id=None, variant_id=None, stage=None))
        group = [x for x in plan["tasks"] if x["character_id"] == "CHR-001"]
        speaker = [x for x in plan["tasks"] if x["character_id"] == "CHR-002"]
        self.assertEqual([(x["stage"], x["asset_mode"]) for x in group], [("execution", "ensemble")])
        self.assertEqual([(x["stage"], x["asset_mode"]) for x in speaker],
                         [("execution", "speaking_extra")])
        bad = self.design()
        bad["member_count"] = 2
        with self.assertRaisesRegex(ValueError, "scripted number"):
            self.submit("ensemble-design", bad, "CHR-001", "S01")
        self.submit("ensemble-design", self.design(), "CHR-001", "S01")
        self.approve("ensemble-design", "CHR-001", "S01")
        bad_prompt = self.prompt()
        bad_prompt["layout"] = {"top_left": "front_face"}
        with self.assertRaisesRegex(ValueError, "full body on one canvas"):
            self.submit("prompt-package", bad_prompt, "CHR-001", "S01", "execution")
        bad_prompt = self.prompt()
        bad_prompt["aspect_ratio"] = "9:16"
        with self.assertRaisesRegex(ValueError, "horizontal canvas"):
            self.submit("prompt-package", bad_prompt, "CHR-001", "S01", "execution")
        self.submit("prompt-package", self.prompt(), "CHR-001", "S01", "execution")
        image_path = self.work / "group.png"
        image_path.write_bytes(b"synthetic-image")
        image = cp.cmd_import_image(NS(project_root=str(self.root), path=str(image_path),
                                       character_id="CHR-001", variant_id="S01", stage="execution"))
        self.assertIn("群像执行资产", image["path"])
        review = {"schema_version": "CharacterImageReviewV1", "image_sha256": image["sha256"],
                  "stage": "execution", "verdict": "pass",
                  **{x: [] for x in ("factual_conflicts", "identity_issues", "layout_issues",
                                    "label_issues", "blocking_issues", "adoption_proposals")}}
        cp.cmd_submit_review(NS(project_root=str(self.root), image_id=image["id"], file=self.save(review)))
        cp.cmd_approve_image(NS(project_root=str(self.root), image_id=image["id"], operator="测试操作者"))
        out = self.work / "pack"
        with patch.object(cp, "__file__", str(Path(__file__).resolve().parents[2] /
                                            "character-assets/scripts/character_project.py")):
            cp.cmd_package(NS(project_root=str(self.root), character_id="CHR-001",
                              variant_id="S01", output=str(out)))
        self.assertEqual(cp.read_json(out / "manifest.json")["schema_version"], "CharacterEnsemblePackV1")
        changed = copy.deepcopy(self.design())
        changed["variation_logic"] += "；修改排位"
        self.submit("ensemble-design", changed, "CHR-001", "S01")
        with self.assertRaisesRegex(ValueError, "approved"):
            cp._checked_image(self.root, self.state(), "execution", "CHR-001", "S01")

    def test_speaker_cannot_use_group_shortcut(self):
        self.foundation()
        self.assertEqual(cp.ensemble.mode(cp._runtime(), self.root, self.state(), "CHR-002"), "speaking_extra")
        wrong = self.design()
        wrong["character_id"] = "CHR-002"
        with self.assertRaisesRegex(ValueError, "non-speaking"):
            self.submit("ensemble-design", wrong, "CHR-002", "S01")

    def test_speaking_extra_has_one_independent_execution_sheet(self):
        self.foundation()
        state = self.state()
        design = {"schema_version": "SpeakingExtraDesignV1", "character_id": "CHR-002",
                  "variant_id": "S01", "parent_refs": {x: state["records"][x]["sha256"]
                  for x in ("script-context", "visual-bible", "cast-plan")},
                  "narrative_function": "崖边传令", "spoken_line": "撤离！",
                  "world_style_translation": "获批写实摄影，崖边自然散射光",
                  "face_and_hair": "圆脸、短束发", "body_and_posture": "中等身量，重心前移",
                  "costume_front": "活动袖与前开襟", "costume_back": "背后窄肩片",
                  "color_and_material": "哑光深灰布", "prop_and_action": "手势示意撤离",
                  "source_refs": ["P2"], "evidence_status": "mixed",
                  "new_lore_policy": "none", "unresolved": []}
        self.submit("extra-design", design, "CHR-002", "S01")
        self.approve("extra-design", "CHR-002", "S01")
        sha = self.state()["records"]["extra-design:CHR-002:S01"]["sha256"]
        layout = {"top_left": "front_face", "top_right": "three_quarter_face_45",
                  "bottom_left": "headless_enlarged_front_costume",
                  "bottom_right": "complete_back_head_to_shoes"}
        package = {"schema_version": "CharacterPromptPackageV1", "character_id": "CHR-002",
                   "variant_id": "S01", "variant_name": "常态", "stage": "execution",
                   "target_model": "gpt-image-2.5", "purpose": "production", "morphology": "human",
                   "aspect_ratio": "9:16", "design_basis": {"records": {"extra-design:CHR-002:S01": sha}},
                   "anchor_images": {}, "reference_images": [], "layout": layout,
                   "prompts": [{"id": "推荐", "text": "9:16 正脸与45度脸、无头正面衣装、完整背面；获批写实摄影，崖边自然散射光"}],
                   "acceptance_checks": ["9:16", "正脸", "45度脸", "无头正面服装结构", "完整背面", "风格一致"]}
        bad = copy.deepcopy(package)
        bad["aspect_ratio"] = "16:9"
        with self.assertRaisesRegex(ValueError, "aspect_ratio_basis"):
            self.submit("prompt-package", bad, "CHR-002", "S01", "execution")
        self.submit("prompt-package", package, "CHR-002", "S01", "execution")
        image_path = self.work / "speaker.png"
        image_path.write_bytes(b"synthetic-speaker-image")
        image = cp.cmd_import_image(NS(project_root=str(self.root), path=str(image_path),
                                       character_id="CHR-002", variant_id="S01", stage="execution"))
        self.assertIn("独立执行资产", image["path"])
        review = {"schema_version": "CharacterImageReviewV1", "image_sha256": image["sha256"],
                  "stage": "execution", "verdict": "pass",
                  **{x: [] for x in ("factual_conflicts", "identity_issues", "layout_issues",
                                    "label_issues", "blocking_issues", "adoption_proposals")}}
        cp.cmd_submit_review(NS(project_root=str(self.root), image_id=image["id"], file=self.save(review)))
        cp.cmd_approve_image(NS(project_root=str(self.root), image_id=image["id"], operator="测试操作者"))
        out = self.work / "speaker-pack"
        with patch.object(cp, "__file__", str(Path(__file__).resolve().parents[2] /
                                            "character-assets/scripts/character_project.py")):
            cp.cmd_package(NS(project_root=str(self.root), character_id="CHR-002",
                              variant_id="S01", output=str(out)))
        self.assertEqual(cp.read_json(out / "manifest.json")["schema_version"],
                         "CharacterSpeakingExtraPackV1")

    def test_explicit_count_spelling_and_conflicts(self):
        row = {"name": "持弓者", "states": [{"evidence": [{"text": "十二名持弓者列队"}]}]}
        self.assertEqual(ensemble._script_count(row), 12)
        row["states"][0]["evidence"] = [{"text": "几名持弓者列队"}]
        self.assertIsNone(ensemble._script_count(row))
        row["states"][0]["evidence"] = [{"text": "持弓者25人列队"}]
        self.assertEqual(ensemble._script_count(row), 25)
        row["states"][0]["evidence"].append({"text": "十二名持弓者离开"})
        with self.assertRaisesRegex(ValueError, "Conflicting explicit group counts"):
            ensemble._script_count(row)

    def test_group_style_must_carry_approved_style(self):
        self.foundation()
        bad = self.design()
        bad["world_style_translation"] = "漫画渲染的群体"
        with self.assertRaisesRegex(ValueError, "approved project visual style"):
            self.submit("ensemble-design", bad, "CHR-001", "S01")
        self.assertEqual(ensemble._style_anchors({"medium": "写实摄影", "palette": ["冷灰蓝", "旧铜色"]}),
                         ["写实摄影", "冷灰蓝", "旧铜色"])

    def test_script_count_survives_asset_summary_omitting_number(self):
        row = {"name": "持弓者", "states": [{"id": "S01", "evidence": [
            {"text": "持弓者列队", "source_refs": ["P1"]}]}]}
        screenplay = {"episodes": [{"scenes": [{"blocks": [
            {"type": "action", "text": "三名持弓者在崖边列队", "source_refs": ["P1"]}]}]}]}
        self.assertEqual(ensemble._script_count(row, screenplay, "S01"), 3)


if __name__ == "__main__":
    unittest.main()

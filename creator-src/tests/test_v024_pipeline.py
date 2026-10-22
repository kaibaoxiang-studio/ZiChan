"""State-machine checks for the five-stage, state-specific character pipeline.

These synthetic bytes test bookkeeping only; they are not visual-review fixtures.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "character-assets/scripts/character_project.py"
SPEC = importlib.util.spec_from_file_location("character_project_v024", SCRIPT)
cp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cp)


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


class V024PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.drafts = Path(self.temp.name) / "drafts"
        self.drafts.mkdir()
        examples = ROOT / "creator-src/plugin_files/examples"
        cp.cmd_init(ns(project_root=str(self.root), project_id="test-v024",
                       screenplay=str(examples / "sample-screenplay.json"),
                       asset_table=str(examples / "sample-assets.json"),
                       scene_log=None, snapshot=None, design_progression="complete"))
        self.state = cp.read_json(self.root / "project.json")
        self.character = self.state["roster"][0]

    def save(self, name, data):
        path = self.drafts / f"{name}.json"
        cp.write_json(path, data)
        return str(path)

    def submit_record(self, kind, data, variant="base", stage=None):
        return cp.cmd_submit(ns(project_root=str(self.root), kind=kind,
                                character_id=self.character["id"] if kind in {"design-card", "prompt-package"} else None,
                                variant_id=variant, stage=stage,
                                file=self.save(f"{kind}-{variant}-{stage or 'record'}", data)))

    def approve_record(self, kind, variant="base"):
        return cp.cmd_approve_record(ns(project_root=str(self.root), kind=kind,
                                        character_id=self.character["id"] if kind == "design-card" else None,
                                        variant_id=variant, operator="fixture"))

    def prepare_decisions(self):
        self.submit_record("visual-bible", {"schema_version": "ProjectVisualBibleV1",
                           "project_id": "test-v024", "world_rules": [], "style": {},
                           "evidence": [{"claim": "测试", "source_refs": ["fixture"]}], "unresolved": []})
        self.approve_record("visual-bible")
        self.submit_record("cast-plan", {"schema_version": "CastPlanV1",
                           "characters": [{"id": x["id"], "design_distinction": "测试轮廓"}
                                          for x in self.state["roster"]], "unresolved": []})
        self.approve_record("cast-plan")
        for variant in ("base", "S01", "S02"):
            card = {"schema_version": "CharacterDesignCardV1", "character_id": self.character["id"],
                    "variant_id": variant, "morphology": "nonhuman", "facts": [],
                    "inferences": [], "approved_choices": [], "identity_invariants": [],
                    "appearance": {}, "costume": {}, "execution_layout": {"views": "fixture"},
                    "unresolved": []}
            self.submit_record("design-card", card, variant)
            self.approve_record("design-card", variant)

    def stage_image(self, stage, variant="base", content=None):
        state = cp.read_json(self.root / "project.json")
        modern = state.get("pipeline_version", 1) >= 2
        card = state["records"][f"design-card:{self.character['id']}:{variant}"]
        predecessors = ({"avatar": (), "expression": ("avatar",),
                         "full_body": ("avatar", "expression"),
                         "costume_design": ("avatar", "expression", "full_body"),
                         "execution": ("avatar", "expression", "full_body", "costume_design")}[stage]
                        if modern else {"avatar": (), "expression": ("avatar",),
                                        "full_body": ("avatar",),
                                        "execution": ("avatar", "expression", "full_body")}[stage])
        anchors = {prior: cp._checked_image(self.root, state, prior, self.character["id"],
                                            "base" if modern and prior in cp.IDENTITY_STAGES else variant)["sha256"]
                   for prior in predecessors}
        prompt = {"schema_version": "CharacterPromptPackageV1", "character_id": self.character["id"],
                  "variant_id": variant, "stage": stage, "target_model": "gpt-image-2.5",
                  "design_card_sha256": card["sha256"], "anchor_images": anchors,
                  "reference_images": [], "prompts": [{"id": "p1", "text": "测试画面 3:4 竖版" if stage == "avatar" else
                                                       "测试画面 9:16 竖版" if stage == "full_body" else "测试画面"}],
                  "acceptance_checks": ["服饰结构清晰" if stage == "costume_design" else "身份一致"]}
        if stage == "avatar":
            prompt["aspect_ratio"] = "3:4"
            prompt["prompts"].append({"id": "p2", "text": "测试画面 3:4 竖版"})
        elif stage == "expression":
            prompt["labels"] = [f"表情{i}" for i in range(9)]
        elif stage == "full_body":
            prompt.update(aspect_ratio="9:16", head_visible=True, feet_visible=True)
            prompt["acceptance_checks"].append("画幅 9:16")
        elif stage == "costume_design":
            prompt["variant_name"] = cp.variant_name(state, self.character["id"], variant)
        else:
            prompt.update(morphology="nonhuman", layout={"views": "fixture"})
        self.submit_record("prompt-package", prompt, variant, stage)
        image_path = self.drafts / f"{stage}-{variant}-{content or 'first'}.png"
        image_path.write_bytes(f"synthetic:{stage}:{variant}:{content or 'first'}".encode())
        image = cp.cmd_import_image(ns(project_root=str(self.root), stage=stage,
                                       character_id=self.character["id"], variant_id=variant,
                                       path=str(image_path)))
        review = {"schema_version": "CharacterImageReviewV1", "image_sha256": image["sha256"],
                  "stage": stage, "verdict": "pass", "factual_conflicts": [],
                  "identity_issues": [], "layout_issues": [], "label_issues": [],
                  "blocking_issues": [], "adoption_proposals": []}
        cp.cmd_submit_review(ns(project_root=str(self.root), image_id=image["id"],
                                file=self.save(f"review-{stage}-{variant}-{content}", review)))
        cp.cmd_approve_image(ns(project_root=str(self.root), image_id=image["id"], operator="fixture"))
        return image

    def test_dependency_plan_names_and_state_package(self):
        self.prepare_decisions()
        plan = cp.cmd_plan(ns(project_root=str(self.root), character_id=self.character["id"],
                              variant_id=None, stage=None))
        self.assertEqual([x["stage"] for x in plan["tasks"]],
                         ["avatar", "expression", "full_body", "costume_design", "execution",
                          "costume_design", "execution"])
        self.assertEqual(plan["tasks"][0]["status"], "ready")
        selected = cp.cmd_plan(ns(project_root=str(self.root),
                                  character_id=[x["id"] for x in self.state["roster"]],
                                  variant_id=None, stage="avatar"))
        self.assertEqual(selected["mode"], "batch")
        self.assertEqual(len(selected["tasks"]), len(self.state["roster"]))
        with self.assertRaises(ValueError):
            self.stage_image("costume_design", "S01")
        for stage in cp.IDENTITY_STAGES:
            self.stage_image(stage)
        first = self.stage_image("costume_design", "S01")
        self.assertIn(self.character["name"], Path(first["path"]).name)
        self.assertIn("工作服", Path(first["path"]).name)
        self.stage_image("execution", "S01")
        self.stage_image("costume_design", "S02")
        self.stage_image("execution", "S02")
        output = Path(self.temp.name) / "pack"
        cp.cmd_package(ns(project_root=str(self.root), character_id=self.character["id"],
                          variant_id="S01", output=str(output)))
        manifest = cp.read_json(output / "manifest.json")
        self.assertEqual(manifest["schema_version"], "CharacterAssetPackV2")
        self.assertEqual(set(manifest["approved_images"]), set(cp.STAGES))
        replacement = self.stage_image("costume_design", "S01", "replacement")
        self.assertNotEqual(first["id"], replacement["id"])
        state = cp.read_json(self.root / "project.json")
        self.assertTrue(cp._checked_image(self.root, state, "execution", self.character["id"], "S02"))
        with self.assertRaises(ValueError):
            cp._checked_image(self.root, state, "execution", self.character["id"], "S01")
        self.stage_image("full_body", "base", "replacement")
        state = cp.read_json(self.root / "project.json")
        for variant in ("S01", "S02"):
            with self.assertRaises(ValueError):
                cp._checked_image(self.root, state, "costume_design", self.character["id"], variant)

    def test_existing_four_stage_project_remains_packagable(self):
        state = cp.read_json(self.root / "project.json")
        state.pop("pipeline_version")
        cp.write_json(self.root / "project.json", state)
        self.prepare_decisions()
        for stage in cp.LEGACY_STAGES:
            self.stage_image(stage, "base")
        output = Path(self.temp.name) / "legacy-pack"
        cp.cmd_package(ns(project_root=str(self.root), character_id=self.character["id"],
                          variant_id="base", output=str(output)))
        manifest = cp.read_json(output / "manifest.json")
        self.assertEqual(manifest["schema_version"], "CharacterAssetPackV1")
        self.assertEqual(set(manifest["approved_images"]), set(cp.LEGACY_STAGES))


if __name__ == "__main__":
    unittest.main()

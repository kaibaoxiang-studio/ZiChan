"""Synthetic protocol checks; fixture bytes are not a visual review or approval."""
from pathlib import Path
import tempfile
from types import SimpleNamespace as Args
import unittest

from prompt_fixture import cp, make_avatar_project


class ImageStateGates(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "project"
        _, self.package, _ = make_avatar_project(self.root)
        self.file = self.base / "package.json"
        self.submit_prompt()
        self.picture = self.base / "fixture.png"
        self.picture.write_bytes(b"synthetic image bytes, never visually approved")
        self.import_args = Args(project_root=self.root, path=self.picture, character_id="CHR-TEST",
                                variant_id="base", stage="avatar")

    def submit_prompt(self):
        cp.write_json(self.file, self.package)
        return cp.cmd_submit(Args(project_root=self.root, kind="prompt-package", character_id="CHR-TEST",
                                  variant_id="base", stage="avatar", file=self.file))

    def review(self, image, proposals=None):
        report = {"schema_version": "CharacterImageReviewV1", "image_sha256": image["sha256"], "stage": "avatar",
                  "verdict": "pass", **{name: [] for name in ("factual_conflicts", "identity_issues", "layout_issues",
                  "label_issues", "blocking_issues")}, "adoption_proposals": proposals or []}
        file = self.base / "review.json"
        cp.write_json(file, report)
        return cp.cmd_submit_review(Args(project_root=self.root, image_id=image["id"], file=file))

    def test_unapproved_new_feature_cannot_be_passing_review(self):
        image = cp.cmd_import_image(self.import_args)
        with self.assertRaisesRegex(ValueError, "adoption_proposals"):
            self.review(image, [{"feature": "未批准的颊部新疤痕"}])
        self.assertFalse(cp.read_json(self.root / "project.json")["reviews"])

    def test_reimport_same_pixels_new_prompt_creates_fresh_review_target(self):
        first = cp.cmd_import_image(self.import_args)
        self.review(first)
        cp.cmd_approve_image(Args(project_root=self.root, image_id=first["id"], operator="test:fixture-only"))
        self.package["prompts"][0]["text"] += "\n全部设计保持，测试仅改变提示词措辞。"
        self.submit_prompt()
        second = cp.cmd_import_image(self.import_args)
        state = cp.read_json(self.root / "project.json")
        self.assertNotEqual(first["id"], second["id"])
        self.assertFalse(second["stale"])
        self.assertIsNone(second["approval"])
        self.assertEqual(second["prompt_sha256"], state["records"]["prompt-package:avatar:CHR-TEST:base"]["sha256"])
        self.assertNotIn(second["id"], state["reviews"])
        self.assertTrue(next(x for x in state["images"] if x["id"] == first["id"])["stale"])
        self.assertEqual(cp.cmd_import_image(self.import_args)["id"], second["id"])

    def test_same_prompt_stale_reimport_has_unique_identity(self):
        first = cp.cmd_import_image(self.import_args)
        state = cp.read_json(self.root / "project.json")
        state["images"][0]["stale"] = True
        cp.write_json(self.root / "project.json", state)
        second = cp.cmd_import_image(self.import_args)
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(cp.cmd_import_image(self.import_args)["id"], second["id"])
        self.assertEqual(len(cp.read_json(self.root / "project.json")["images"]), 2)

    def test_changed_prompt_file_cannot_be_import_basis(self):
        state = cp.read_json(self.root / "project.json")
        path = self.root / state["records"]["prompt-package:avatar:CHR-TEST:base"]["path"]
        changed = cp.read_json(path)
        changed["prompts"][0]["text"] = "tampered prompt"
        cp.write_json(path, changed)
        with self.assertRaisesRegex(ValueError, "contents changed"):
            cp.cmd_import_image(self.import_args)


if __name__ == "__main__":
    unittest.main()

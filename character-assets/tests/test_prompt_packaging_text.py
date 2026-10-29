"""The shipped readable text is the same approved JSON, including old projects."""
from pathlib import Path
import tempfile
import unittest

from prompt_fixture import cp


class PromptPackagingText(unittest.TestCase):
    def test_legacy_missing_knowledge_cache_is_derived_only_in_pack(self):
        with tempfile.TemporaryDirectory() as folder:
            root, output, _ = self.prepare(folder, metadata=False)
            plugin = Path(cp.__file__).resolve().parents[1]
            locked = cp.read_json(plugin / "knowledge-lock.json")["snapshots"][0]
            ref = {"path": locked["path"], "sha256": locked["rules_sha256"]}
            row = cp.copy_pack_knowledge(root, output, ref)
            self.assertEqual(cp.digest(output / row["path"]), ref["sha256"])
            self.assertFalse((root / "knowledge-snapshots").exists())

    def test_damaged_existing_knowledge_cache_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            root, output, _ = self.prepare(folder, metadata=False)
            plugin = Path(cp.__file__).resolve().parents[1]
            locked = cp.read_json(plugin / "knowledge-lock.json")["snapshots"][0]
            ref = {"path": locked["path"], "sha256": locked["rules_sha256"]}
            cache = root / "knowledge-snapshots" / ref["sha256"]
            cache.parent.mkdir()
            cache.write_bytes(b"corrupted")
            with self.assertRaisesRegex(ValueError, "snapshot changed"):
                cp.copy_pack_knowledge(root, output, ref)

    def prepare(self, folder, metadata=True):
        root, output = Path(folder) / "project", Path(folder) / "pack"
        package = {"schema_version": "CharacterPromptPackageV1", "prompts": [{"id": "main", "text": "完整脸发设计。\n\n保留剧情状态。"}]}
        cp.write_json(root / "records/prompt.json", package)
        record = {"path": "records/prompt.json", "sha256": cp.digest(package)}
        if metadata:
            target = root / "提示词/角色_头像.txt"
            cp.write_prompt_text(package, target)
            record.update(text_path="提示词/角色_头像.txt", text_sha256=cp.digest(target))
        return root, output, record

    def test_new_record_copies_exact_txt_and_manifest_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root, output, record = self.prepare(folder)
            row = cp.copy_prompt_text_delivery(root, output, record)
            self.assertEqual((output / row["path"]).read_bytes(), (root / record["text_path"]).read_bytes())
            self.assertEqual(row["sha256"], record["text_sha256"])

    def test_changed_txt_is_rejected_even_with_manually_updated_txt_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root, output, record = self.prepare(folder)
            path = root / record["text_path"]
            path.write_text("另一份手改提示词。", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "TXT changed"):
                cp.copy_prompt_text_delivery(root, output, record)
            record["text_sha256"] = cp.digest(path)
            with self.assertRaisesRegex(ValueError, "exact JSON export"):
                cp.copy_prompt_text_delivery(root, output, record)

    def test_legacy_approved_record_derives_txt_only_inside_pack(self):
        with tempfile.TemporaryDirectory() as folder:
            root, output, record = self.prepare(folder, metadata=False)
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            row = cp.copy_prompt_text_delivery(root, output, record)
            self.assertEqual((output / row["path"]).read_text(), "完整脸发设计。\n\n保留剧情状态。\n")
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertNotIn("text_path", record)

    def test_text_path_cannot_escape_project_or_pack(self):
        with tempfile.TemporaryDirectory() as folder:
            root, output, record = self.prepare(folder)
            record["text_path"] = "../outside.txt"
            with self.assertRaisesRegex(ValueError, "project-relative"):
                cp.copy_prompt_text_delivery(root, output, record)


if __name__ == "__main__":
    unittest.main()

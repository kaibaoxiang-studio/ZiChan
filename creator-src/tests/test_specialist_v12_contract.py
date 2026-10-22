"""A single recommendation still needs a real task and attributable design work."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "plugin_files/scripts/validate_specialist_proposal.py"
SPEC = importlib.util.spec_from_file_location("specialist_v12", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class SpecialistV12Tests(unittest.TestCase):
    def setUp(self):
        self.proposal = {
            "schema_version": "CharacterSpecialistProposalV1.2",
            "specialist": "character-hair-design", "character_id": "CHR-001",
            "variant_id": "base", "scope": "identity", "execution_mode": "independent",
            "task": {"objective": "频繁抬头检修时保持视野", "character_context": "人物重视工作体面而非炫耀",
                     "constraints": ["不能增加未写明的伤疤"], "expected_result": "有前侧后结构的单套发型"},
            "knowledge_refs": [{"path": "references/knowledge/character-hair-design/hair.md", "sha256": "a" * 64}],
            "facts": [], "options": [{"id": "A", "visible_design": "额前分束后掠，两侧收入耳后，低位短束口",
                "rationale": "把不遮挡视野的功能落实到固定方式", "comparison_difference": "区别于同事的高位束发轮廓",
                "production_check": "抬头与背面仍保持同一束口", "design_elements": [
                    {"part": "额前", "visible_feature": "偏分后掠短束", "placement_or_structure": "额角向耳后收束",
                     "basis": "头部动作需要视野", "evidence_status": "inference"},
                    {"part": "后脑", "visible_feature": "低位窄束口", "placement_or_structure": "枕骨下沿固定",
                     "basis": "原创轮廓选择", "evidence_status": "creative_choice"}]}],
            "recommended_option_id": "A", "unresolved": []}

    def test_single_recommendation_with_task_and_provenance(self):
        self.assertEqual(validator.validate(self.proposal)["options"], 1)

    def test_generic_used_label_cannot_replace_task_or_knowledge(self):
        for field in ("task", "knowledge_refs"):
            candidate = copy.deepcopy(self.proposal)
            candidate.pop(field)
            with self.assertRaises(ValueError):
                validator.validate(candidate)

    def test_execution_and_creative_evidence_must_be_explicit(self):
        self.proposal["execution_mode"] = "used"
        with self.assertRaises(ValueError):
            validator.validate(self.proposal)
        self.proposal["execution_mode"] = "inline"
        self.proposal["options"][0]["design_elements"][0]["evidence_status"] = "script_fact_or_guess"
        with self.assertRaises(ValueError):
            validator.validate(self.proposal)


if __name__ == "__main__":
    unittest.main()

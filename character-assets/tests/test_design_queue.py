"""Design work remains visible independently of image production readiness."""
import copy
from pathlib import Path
import tempfile
import unittest

from prompt_fixture import cp, make_avatar_project


class DesignQueueTest(unittest.TestCase):
    def queue(self, root, state, stages=("avatar",), mode="individual"):
        return cp._design_queue(root, state, state["roster"], [
            {"character_id": "CHR-TEST", "variant_id": "base", "asset_mode": mode, "stage": stage}
            for stage in stages])

    def test_approved_direction_is_not_finished_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state, _, _ = make_avatar_project(root)
            del state["records"]["stage-design:identity:CHR-TEST:base"]
            tasks = self.queue(root, state)
            self.assertEqual(tasks[0]["status"], "approved")
            self.assertEqual(tasks[1]["status"], "needs_design")
            self.assertEqual(tasks[1]["scope"], "identity")
            self.assertEqual(tasks[1]["capability"], "character-design")

    def test_direction_draft_can_feed_identity_draft_without_fake_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state, _, _ = make_avatar_project(root)
            state["records"]["design-brief:CHR-TEST:base"]["approval"] = None
            del state["records"]["stage-design:identity:CHR-TEST:base"]
            tasks = self.queue(root, state)
            self.assertEqual([x["status"] for x in tasks], ["awaiting_approval", "needs_design"])
            self.assertIsNone(state["records"]["design-brief:CHR-TEST:base"]["approval"])

    def test_existing_identity_draft_requests_review_not_duplicate_design(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state, _, _ = make_avatar_project(root)
            state["records"]["stage-design:identity:CHR-TEST:base"]["approval"] = None
            task = self.queue(root, state)[1]
            self.assertEqual((task["status"], task["action"]), ("awaiting_approval", "review_design"))

    def test_execution_lists_body_bible_and_state_design(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state, _, _ = make_avatar_project(root)
            before = copy.deepcopy(state)
            tasks = self.queue(root, state, ("execution",))
            self.assertEqual([x["scope"] for x in tasks], ["direction", "identity", "body", "style_bible", "costume"])
            self.assertEqual(tasks[2]["status"], "needs_design")
            self.assertEqual(tasks[3]["status"], "blocked")
            self.assertEqual(tasks[4]["status"], "blocked")
            self.assertEqual(state, before)

    def test_single_image_extra_route_does_not_inherit_individual_stage_queue(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state, _, _ = make_avatar_project(root)
            self.assertEqual(self.queue(root, state, ("execution",), "speaking_extra"), [])
            self.assertEqual(self.queue(root, state, ("execution",), "ensemble"), [])

    def test_complete_legacy_workflow_keeps_its_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state, _, _ = make_avatar_project(root)
            state["design_progression"] = "complete"
            self.assertEqual(self.queue(root, state), [])


if __name__ == "__main__":
    unittest.main()

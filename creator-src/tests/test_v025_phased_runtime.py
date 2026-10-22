"""Real CLI contracts and state lineage; synthetic image bytes do not test visuals."""
from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import patch

import test_v022_contract as old
from test_body_proportion_gate import anchored_card

cp = old.project
ROOT = Path(__file__).resolve().parents[2]


class PhasedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.root = self.work / "project"
        self.fixture = old.V22HandoffTests("test_valid_real_handoff")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        examples = ROOT / "creator-src/plugin_files/examples"
        cp.cmd_init(NS(project_root=str(self.root), project_id="phased-test", snapshot=None,
                       screenplay=str(examples / "sample-screenplay.json"),
                       asset_table=str(examples / "sample-assets.json"), scene_log=None))
        self.character = "CHR-001"
        self.seq = 0

    def state(self):
        return cp.read_json(self.root / "project.json")

    def save(self, obj):
        self.seq += 1
        path = self.work / f"draft-{self.seq}.json"
        cp.write_json(path, obj)
        return str(path)

    def submit(self, kind, data, scope=None, variant="base", stage=None):
        return cp.cmd_submit(NS(project_root=str(self.root), kind=kind, character_id=self.character,
                                variant_id=variant, scope=scope, stage=stage, file=self.save(data)))

    def approve(self, kind, scope=None, variant="base"):
        return cp.cmd_approve_record(NS(project_root=str(self.root), kind=kind, character_id=self.character,
                                        variant_id=variant, scope=scope, operator="测试操作者"))

    def setup_context(self):
        listing = cp.phased.context_units(cp._runtime(), NS(project_root=str(self.root), source=None, output=None))
        context = {"schema_version": "ScriptContextV1", "source_sha256": listing["source_sha256"],
                   "source_kind": "screenplay", "read_units": [{"unit_id": x["unit_id"], "sha256": x["sha256"]} for x in listing["units"]],
                   "synopsis": "维修者与礼服来客发生争论，随后进入危险机舱。", "world_summary": "可维修的飞船技术与分工环境。",
                   "narrative_structure": "从身份冲突进入机舱危险。", "character_index": [{"character_id": row["id"],
                   "name": row["name"], "role_in_story": "维修行动、争论或警戒中的参与者", "arc_summary": "从争论进入机舱事件",
                   "relationships": "林岚与陆遥争执，灰爪警戒", "evidence_unit_ids": [x["unit_id"] for x in listing["units"]]}
                   for row in self.state()["roster"]], "unresolved": []}
        receipt = self.submit("script-context", context)
        self.assertIn(receipt["status"], {"ready", "unchanged"})
        if receipt["status"] == "ready":
            self.assertFalse(receipt["interpretation_confirmed"])
        self.submit("visual-bible", {"schema_version": "ProjectVisualBibleV1", "project_id": "phased-test",
                   "world_rules": ["飞船能够维护"], "style": {"medium": "写实摄影"},
                   "evidence": [{"claim": "维修飞船", "source_refs": ["EP-01-S01"]}], "unresolved": []})
        self.approve("visual-bible")
        self.submit("cast-plan", {"schema_version": "CastPlanV1", "characters": [
                   {"id": x["id"], "design_distinction": "按角色职能区分轮廓"} for x in self.state()["roster"]], "unresolved": []})
        self.approve("cast-plan")
        return context

    def task(self):
        return {"objective": "让维护习惯成为可见结构", "character_context": "林岚是飞船维修行动者",
                "constraints": ["保留右眉旧伤原文事实"], "expected_result": "当前阶段能画出的结构与关系"}

    def setup_brief(self, approve=True):
        context = self.setup_context()
        plan = {x: {"status": "not_needed", "reason": "当前不额外添加该类特征"} for x in cp.SPECIALIST_DOMAINS_V24}
        for name in ("character-hair-design", "character-body-design", "character-costume-material-design"):
            plan[name] = {"status": "inline" if name == "character-hair-design" else "defer", "reason": "按阶段深化"}
            if plan[name]["status"] == "inline":
                plan[name]["task"] = self.task()
        brief = {"schema_version": "DesignDirectionBriefV1", "asset_domain": "character", "character_id": self.character, "variant_id": "base",
                 "context_sha256": self.state()["records"]["script-context"]["sha256"],
                 "understanding": {"schema_version": "CharacterUnderstandingV1",
                    **{name: "结合维修、争论与进入机舱的全文行为理解人物" for name in cp.phased.UNDERSTANDING_FIELDS},
                    "evidence_unit_ids": [x["unit_id"] for x in context["read_units"]]},
                 "design_thesis": "维护实用形象中保留自主与不服从", "visual_strategy": "contrast",
                 "recommended_direction": "发型服从工作需要，眉部旧伤保留原文，普通骨相不作身份美化",
                 "alternatives": [], "delegated_dimensions": ["普通皮肤细节"], "specialist_plan": plan, "unresolved": []}
        self.submit("design-brief", brief)
        if approve:
            self.approve("design-brief")
        return brief

    def payloads(self):
        card = copy.deepcopy(self.fixture.card)
        anchors = anchored_card()
        card["body_form"].update(anchors["body_form"])
        card["visual_details"]["body"].update(anchors["visual_details"]["body"])
        identity = {name: copy.deepcopy(card[name]) for name in
                    ("morphology", "appearance", "feature_focus", "differentiation_review")}
        identity["identity_invariants"] = ["右眉旧伤位置固定"]
        identity["visual_details"] = {name: copy.deepcopy(card["visual_details"][name]) for name in ("face", "hair", "skin")}
        identity["visual_details"]["adornments"] = {"head_neck": card["visual_details"]["adornments"]["head_neck"]}
        identity["recognition_axes"] = {name: card["recognition_axes"][name] for name in ("face_structure", "hair_structure")}
        identity["world_influences"] = {"environment": "维修机舱", "technology": "可维护飞船", "resources_and_access": "常用维修资源可得",
            "appearance_effects": [{"feature": "短发束收在耳后", "mechanism": "避免维修时遮挡视线",
                                    "basis": "维修行为与可用固定方式", "evidence_status": "inference"}]}
        identity["facial_surface"] = {"stable_marks": [], "applied_decoration": [], "temporary_effects": [],
                                     "absence_or_focus_decision": "本轮不新增装饰"}
        body = {"visual_details": {"body": card["visual_details"]["body"]}, "body_form": card["body_form"],
                "recognition_axes": {name: card["recognition_axes"][name] for name in ("silhouette", "body_posture")}}
        costume = {"visual_details": {"costume": card["visual_details"]["costume"],
                                      "adornments": {"body_hands": card["visual_details"]["adornments"]["body_hands"]}},
                   "costume": {"summary": "深蓝工作服，袖口保留活动余量"}, "recognition_axes": {"costume_color": "深蓝工作服色块"}}
        return identity, body, costume

    def stage(self, scope, payload, variant="base", approve=True):
        state = self.state()
        refs = {k: state["records"][k]["sha256"] for k in cp.phased.required_parents(state, self.character, scope, variant)}
        work = {specialist: {"mode": "not_needed", "decision": "本阶段保留已定的留白，不额外添物"}
                for specialist in cp.phased.SCOPE_SPECIALISTS[scope]}
        specialist, field = {"identity": ("character-hair-design", "visual_details.hair.hairline_part"),
                             "body": ("character-body-design", "visual_details.body.frame_proportions"),
                             "costume": ("character-costume-material-design", "visual_details.costume.material_drape_wear")}[scope]
        knowledge = Path(cp.__file__).resolve().parents[1] / "references/evidence.md"
        work[specialist] = {"mode": "inline", "decision": "采用当前阶段的一套推荐设计", "rules_applied": ["说明部位与可复现结构，不把提案伪称事实"],
                            "knowledge_refs": [{"path": "references/evidence.md", "sha256": cp.digest(knowledge)}],
                            "results": [{"field": field, "visible_result": cp.phased._get(payload, field), "basis": "已读剧本与人物设计命题",
                                         "evidence_status": "creative_choice"}]}
        if scope != "identity":
            work[specialist].update(task=self.task(), activation_reason="现在到达负责的设计阶段")
        data = {"schema_version": "CharacterStageDesignV1", "character_id": self.character, "variant_id": variant,
                "scope": scope, "parent_refs": refs, "payload": payload, "specialist_execution": work,
                "deferred_dimensions": ["其他画幅的细节后续深化"] if scope == "identity" else [], "unresolved": []}
        self.submit("stage-design", data, scope, variant)
        if approve:
            self.approve("stage-design", scope, variant)
        return data

    def independent_hair(self, identity):
        stage = self.stage("identity", identity, approve=False)
        proposal = copy.deepcopy(self.fixture.proposal)
        knowledge_path = Path(cp.__file__).resolve().parents[1] / "references/evidence.md"
        proposal.update(schema_version="CharacterSpecialistProposalV1.2", specialist="character-hair-design",
                        execution_mode="independent", task=self.task(),
                        knowledge_refs=[{"path": "references/evidence.md", "sha256": cp.digest(knowledge_path)}])
        for option in proposal["options"]:
            for element in option["design_elements"]:
                element["evidence_status"] = "creative_choice"
        path = self.root / "drafts/specialists/hair-independent.json"
        cp.write_json(path, proposal)
        stage["specialist_execution"]["character-hair-design"] = {
            "mode": "independent", "decision": "采用一套独立发型推荐", "execution_change_reason": "复杂结构改用独立会诊",
            "proposal_ref": str(path.relative_to(self.root)), "proposal_sha256": cp.digest(path), "selected_option_id": "A",
            "applied_elements": [{"field": "visual_details.hair.hairline_part", "element_index": 1}]}
        return stage, proposal, path

    def prompt_image(self, stage, variant="base", preview=False, mode="direction_first", approve=True):
        state = self.state()
        prior = {"avatar": (), "expression": ("avatar",), "full_body": ("avatar", "expression"),
                 "costume_design": cp.IDENTITY_STAGES, "execution": (*cp.IDENTITY_STAGES, "costume_design")}[stage]
        anchors = {x: cp._checked_image(self.root, state, x, self.character, "base" if x in cp.IDENTITY_STAGES else variant)["sha256"] for x in prior}
        basis = {k: state["records"][k]["sha256"] for k in cp.phased.basis_keys(self.character, variant, stage)}
        text = "身份结构一致，服装不入画 3:4"
        checks = ["身份结构一致，服装不入画"]
        pkg = {"schema_version": "CharacterPromptPackageV1", "character_id": self.character, "variant_id": variant,
               "stage": stage, "target_model": "gpt-image-2.5", "purpose": "preview" if preview else "production",
               "preview_mode": mode, "design_basis": {"records": basis}, "anchor_images": anchors,
               "reference_images": [], "prompts": [{"id": "推荐", "text": text}], "acceptance_checks": checks}
        if stage == "avatar":
            pkg.update(aspect_ratio="3:4", reference_attire="face_only")
        elif stage == "expression":
            pkg.update(labels=[f"表情{i}" for i in range(9)], reference_attire="face_only")
        elif stage == "full_body":
            body = cp.phased.resolve_basis(cp._runtime(), self.root, state, pkg, self.character, variant, stage)
            relations = [body["body_form"]["proportion_anchors"][x]["relation"] for x in ("head_body", "shoulder_hip", "torso_legs")]
            pkg.update(aspect_ratio="9:16", head_visible=True, feet_visible=True,
                       reference_attire="white_tank_shorts_barefoot")
            pkg["prompts"][0]["text"] = "；".join(["9:16 白色纯色背心 短裤 赤脚", *relations])
            pkg["acceptance_checks"] = ["9:16 白色纯色背心 短裤 赤脚", *relations]
        elif stage == "costume_design":
            pkg.update(variant_name=cp.variant_name(state, self.character, variant))
            pkg["acceptance_checks"] = ["服饰结构与当前状态一致"]
        else:
            pkg.update(morphology="human", layout={"top_left": "front_face", "top_right": "three_quarter_face_45",
                       "bottom_left": "headless_enlarged_front_costume", "bottom_right": "complete_back_head_to_shoes"})
        self.submit("prompt-package", pkg, variant=variant, stage=stage)
        self.seq += 1
        path = self.work / f"synthetic-{self.seq}.png"
        path.write_bytes(f"synthetic-state-test:{self.seq}".encode())
        image = cp.cmd_import_image(NS(project_root=str(self.root), character_id=self.character,
                                       variant_id=variant, stage=stage, path=str(path)))
        report = {"schema_version": "CharacterImageReviewV1", "image_sha256": image["sha256"], "stage": stage, "verdict": "pass",
                  **{k: [] for k in ("factual_conflicts", "identity_issues", "layout_issues", "label_issues", "blocking_issues", "adoption_proposals")}}
        cp.cmd_submit_review(NS(project_root=str(self.root), image_id=image["id"], file=self.save(report)))
        if approve:
            cp.cmd_approve_image(NS(project_root=str(self.root), image_id=image["id"], operator="测试操作者"))
        return image

    def test_default_and_full_context_coverage_and_actionable_tasks(self):
        self.assertEqual(self.state()["design_progression"], "phased")
        context = self.setup_context()
        context["read_units"] = []
        with self.assertRaisesRegex(ValueError, "every source unit"):
            self.submit("script-context", context)
        brief = self.setup_brief()
        del brief["specialist_plan"]["character-hair-design"]["task"]
        with self.assertRaisesRegex(ValueError, "actionable task"):
            self.submit("design-brief", brief)

    def test_image_first_preview_promotes_same_file_with_explicit_basis_approval(self):
        self.setup_brief(approve=False)
        identity, _, _ = self.payloads()
        self.stage("identity", identity, approve=False)
        with self.assertRaisesRegex(ValueError, "approved record"):
            self.prompt_image("avatar", preview=True, approve=False)
        image = self.prompt_image("avatar", preview=True, mode="image_first", approve=False)
        with self.assertRaisesRegex(ValueError, "promote-candidate"):
            cp.cmd_approve_image(NS(project_root=str(self.root), image_id=image["id"], operator="测试操作者"))
        with self.assertRaises(ValueError):
            self.prompt_image("expression")
        with self.assertRaises(ValueError):
            cp.phased.promote(cp._runtime(), NS(project_root=str(self.root), image_id=image["id"], operator="测试操作者", approve_design_basis=False))
        result = cp.phased.promote(cp._runtime(), NS(project_root=str(self.root), image_id=image["id"], operator="测试操作者", approve_design_basis=True))
        self.assertEqual(result["same_image_sha256"], image["sha256"])
        self.prompt_image("expression")

    def test_phased_whole_chain_package_and_costume_local_invalidation(self):
        self.setup_brief()
        identity, body, costume = self.payloads()
        identity_stage, _, _ = self.independent_hair(identity)
        self.submit("stage-design", identity_stage, "identity")
        self.approve("stage-design", "identity")
        self.prompt_image("avatar")
        self.prompt_image("expression")
        self.stage("body", body)
        self.prompt_image("full_body")
        for variant in ("S01", "S02"):
            self.stage("costume", copy.deepcopy(costume), variant)
            cp.phased.compile_card(cp._runtime(), NS(project_root=str(self.root), character_id=self.character, variant_id=variant))
            self.prompt_image("costume_design", variant)
            self.prompt_image("execution", variant)
        before = self.state()
        changed = copy.deepcopy(costume)
        changed["visual_details"]["costume"]["neckline"] += "，仅当前状态改变领口收边"
        self.stage("costume", changed, "S01")
        after = self.state()
        for stage in cp.IDENTITY_STAGES:
            cp._checked_image(self.root, after, stage, self.character, "base")
        cp._checked_image(self.root, after, "execution", self.character, "S02")
        with self.assertRaises(ValueError):
            cp._checked_image(self.root, after, "execution", self.character, "S01")
        output = self.work / "pack"
        # Creator sources intentionally omit generated provenance; use the real built
        # plugin's provenance path while exercising the source runtime under test.
        with patch.object(cp, "__file__", str(ROOT / "character-assets/scripts/character_project.py")):
            cp.cmd_package(NS(project_root=str(self.root), character_id=self.character, variant_id="S02", output=str(output)))
        manifest = cp.read_json(output / "manifest.json")
        self.assertEqual(manifest["design_progression"], "phased")
        self.assertTrue(manifest["context_source_receipt"]["read_units"])
        self.assertTrue(any(x.startswith("stage-design:body:") for x in manifest["record_approvals"]))
        self.assertTrue((output / "drafts/specialists/hair-independent.json").is_file())
        knowledge_sha = cp.digest(Path(cp.__file__).resolve().parents[1] / "references/evidence.md")
        self.assertTrue((output / "knowledge-snapshots" / knowledge_sha).is_file())
        self.assertEqual(before["records"]["stage-design:identity:CHR-001:base"]["sha256"], after["records"]["stage-design:identity:CHR-001:base"]["sha256"])

    def test_scope_ownership_and_changed_candidate_basis_block(self):
        self.setup_brief()
        identity, body, _ = self.payloads()
        draft = self.stage("identity", identity, approve=False)
        image = self.prompt_image("avatar", preview=True, approve=False)
        changed = copy.deepcopy(draft)
        changed["payload"]["visual_details"]["face"]["contour"] += "，调整颌角宽度"
        self.submit("stage-design", changed, "identity")
        with self.assertRaisesRegex(ValueError, "stale"):
            cp.phased.promote(cp._runtime(), NS(project_root=str(self.root), image_id=image["id"], operator="测试操作者", approve_design_basis=True))
        self.approve("stage-design", "identity")
        body["visual_details"]["face"] = {"contour": "越过阶段修改脸部轮廓"}
        with self.assertRaisesRegex(ValueError, "another scope"):
            self.stage("body", body)

    def test_source_refresh_blocks_context_and_keeps_old_mode_compatible(self):
        self.setup_brief()
        identity, _, _ = self.payloads()
        self.stage("identity", identity)
        self.prompt_image("avatar")
        source = self.work / "changed.md"
        source.write_text("林岚不再维修，改为拒绝进入机舱。", encoding="utf-8")
        cp.cmd_refresh(NS(project_root=str(self.root), screenplay=str(source), asset_table=None, scene_log=None))
        cp.cmd_resolve_impact(NS(project_root=str(self.root), affected=[self.character], global_style=False, operator="测试操作者"))
        with self.assertRaisesRegex(ValueError, "another source version"):
            cp._checked_record(self.root, self.state(), "script-context")
        state = self.state()
        self.assertTrue(state["records"]["stage-design:identity:CHR-001:base"]["stale"])
        state.pop("design_progression")
        self.assertFalse(cp.phased.enabled(state))

    def test_direction_first_preview_and_body_change_keep_face_approvals(self):
        self.setup_brief()
        identity, body, costume = self.payloads()
        self.stage("identity", identity, approve=False)
        image = self.prompt_image("avatar", preview=True, approve=False)
        plan = cp.cmd_plan(NS(project_root=str(self.root), character_id=[self.character], variant_id=None, stage="avatar"))
        self.assertEqual(plan["tasks"][0]["preview_modes"]["direction_first"]["status"], "ready")
        cp.phased.promote(cp._runtime(), NS(project_root=str(self.root), image_id=image["id"], operator="测试操作者", approve_design_basis=True))
        self.prompt_image("expression")
        self.stage("body", body)
        self.prompt_image("full_body")
        self.stage("costume", costume, "S01")
        cp.phased.compile_card(cp._runtime(), NS(project_root=str(self.root), character_id=self.character, variant_id="S01"))
        body["visual_details"]["body"]["weight_posture"] += "，日常重心后移半足"
        self.stage("body", body)
        state = self.state()
        cp._checked_image(self.root, state, "avatar", self.character, "base")
        cp._checked_image(self.root, state, "expression", self.character, "base")
        with self.assertRaises(ValueError):
            cp._checked_image(self.root, state, "full_body", self.character, "base")
        self.assertTrue(state["records"]["stage-design:costume:CHR-001:S01"]["stale"])
        self.assertTrue(state["records"]["design-card:CHR-001:S01"]["stale"])

    def test_nonhuman_identity_and_scope_fact_provenance(self):
        self.setup_brief()
        identity, _, _ = self.payloads()
        identity["morphology"] = "nonhuman"
        identity["morphology_details"] = {"identity": "四足机械主体，头部是低矮的警戒传感器平台，左右装甲边线不对称"}
        identity["visual_details"] = {}
        refs = {"design-brief:CHR-001:base": self.state()["records"]["design-brief:CHR-001:base"]["sha256"]}
        stage = {"schema_version": "CharacterStageDesignV1", "character_id": self.character, "variant_id": "base", "scope": "identity",
                 "parent_refs": refs, "payload": identity, "specialist_execution": {
                     name: {"mode": "not_needed", "decision": "该机械形态没有人类毛发与五官，本轮以形态结构设计代替"}
                     for name in cp.phased.SCOPE_SPECIALISTS["identity"]}, "deferred_dimensions": [], "unresolved": []}
        self.submit("stage-design", stage, "identity")
        stage["payload"]["facts"] = [{"text": "声称是剧本事实却没有出处", "source_refs": []}]
        with self.assertRaisesRegex(ValueError, "nonempty source_refs"):
            self.submit("stage-design", stage, "identity")

    def test_body_metadata_cannot_add_face_choices_or_override_world_rules(self):
        self.setup_brief()
        identity, body, costume = self.payloads()
        self.stage("identity", identity)
        avatar = self.prompt_image("avatar")
        self.prompt_image("expression")
        mutations = [
            {"identity_invariants": ["左眼下新增一颗稳定黑痣"]},
            {"approved_choices": [{"field": "visual_details.face.brow_eyes", "value": "新增脸部记号", "rationale": "错误地从身体阶段改变身份"}]},
            {"recognition_axes": {"face_structure": "身体阶段新加的宽颧骨"}},
            {"world_influences": {"environment": "改成其他世界环境", "appearance_effects": []}},
            {"world_influences": {"appearance_effects": [{"feature": "新脸部记号", "mechanism": "虚构原因", "basis": "错误阶段选择",
                "evidence_status": "creative_choice", "field": "visual_details.face.brow_eyes"}]}},
            {"morphology_details": {"identity": "绕过主体字段更新身份"}},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(body)
                changed.update(mutation)
                with self.assertRaises(ValueError):
                    self.stage("body", changed)
        body["approved_choices"] = [{"field": "visual_details.body.weight_posture", "value": body["visual_details"]["body"]["weight_posture"],
                                     "rationale": "只在身体阶段决定重心"}]
        body["world_influences"] = {"appearance_effects": [{"feature": "重心略向后", "mechanism": "日常动作取舍", "basis": "待确认体态策略",
            "evidence_status": "creative_choice", "field": "visual_details.body.weight_posture"}]}
        self.stage("body", body)
        state = self.state()
        self.assertEqual(cp._checked_image(self.root, state, "avatar", self.character, "base")["id"], avatar["id"])
        self.stage("costume", costume, "S01")
        wrong_costume = copy.deepcopy(costume)
        wrong_costume["approved_choices"] = [{"field": "body_form.proportions.torso_legs", "value": "暗改腿长", "rationale": "错误地从服装改比例"}]
        with self.assertRaisesRegex(ValueError, "another scope"):
            self.stage("costume", wrong_costume, "S01")

    def test_independent_knowledge_and_specialist_field_provenance(self):
        self.setup_brief()
        identity, _, _ = self.payloads()
        stage, proposal, path = self.independent_hair(identity)
        valid = copy.deepcopy(proposal)
        for ref in ({"path": "references/DOES-NOT-EXIST.md", "sha256": "a" * 64},
                    {"path": "references/evidence.md", "sha256": "b" * 64}):
            with self.subTest(ref=ref):
                proposal["knowledge_refs"] = [ref]
                cp.write_json(path, proposal)
                stage["specialist_execution"]["character-hair-design"]["proposal_sha256"] = cp.digest(path)
                with self.assertRaisesRegex(ValueError, "Knowledge"):
                    self.submit("stage-design", stage, "identity")
        cp.write_json(path, valid)
        work = stage["specialist_execution"]["character-hair-design"]
        work["proposal_sha256"] = cp.digest(path)
        work["applied_elements"][0]["field"] = "visual_details.face.contour"
        with self.assertRaisesRegex(ValueError, "outside the specialist"):
            self.submit("stage-design", stage, "identity")
        work["applied_elements"][0]["field"] = "visual_details.hair.hairline_part"
        self.submit("stage-design", stage, "identity")
        self.approve("stage-design", "identity")


if __name__ == "__main__":
    unittest.main()

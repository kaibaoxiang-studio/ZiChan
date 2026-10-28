"""Real validator functions with synthetic projects; no model, approval or images."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
from harness_core.engine import Engine, verify_result
from prompt_fixture import make_avatar_project, write_delivery, envelope, cp


def inventory(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


class PromptDeliveryGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.state, self.package, self.inputs = make_avatar_project(self.project)
        self.delivery = self.root / 'delivery'
        self.cap = next(item for item in cp.read_json(ROOT / 'capabilities.json')['capabilities']
                        if item['id'] == 'character-image-prompt')

    def check(self, package=None, inputs=None):
        write_delivery(self.delivery, package or self.package)
        return verify_result(envelope(), self.cap, self.delivery, inputs or self.inputs, ROOT)

    def test_valid_approved_basis_and_dual_delivery_do_not_write_project(self):
        before = inventory(self.project)
        self.assertEqual(len(self.check()), 2)
        self.assertEqual(inventory(self.project), before)

    def test_short_json_is_not_a_successful_prompt(self):
        package = copy.deepcopy(self.package)
        package['prompts'][0]['text'] = '3:4 白色运动背心，年轻女性。'
        with self.assertRaisesRegex(ValueError, 'dropped'):
            self.check(package)

    def test_selected_cue_cannot_disappear_from_json_and_text(self):
        package = copy.deepcopy(self.package)
        cue = package['prompts'][0]['text'].split('；')[0].split('\n\n')[-1]
        package['prompts'][0]['text'] = package['prompts'][0]['text'].replace(cue, '')
        with self.assertRaisesRegex(ValueError, 'dropped'):
            self.check(package)

    def test_wrong_stage_is_rejected_against_real_task(self):
        package = copy.deepcopy(self.package)
        package['stage'] = 'full_body'
        with self.assertRaisesRegex(ValueError, 'stage mismatch'):
            self.check(package)

    def test_wrong_character_is_rejected_against_real_task(self):
        package = copy.deepcopy(self.package)
        package['character_id'] = 'CHR-OTHER'
        with self.assertRaisesRegex(ValueError, 'target does not match'):
            self.check(package)

    def test_changed_source_is_rejected(self):
        (self.project / 'inputs/script.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Project source changed'):
            self.check()

    def test_changed_approved_design_is_rejected(self):
        record = self.state['records']['stage-design:identity:CHR-TEST:base']
        (self.project / record['path']).write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Approved record contents changed'):
            self.check()

    def test_wrong_basis_version_is_rejected(self):
        package = copy.deepcopy(self.package)
        package['design_basis']['records']['stage-design:identity:CHR-TEST:base'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'basis version changed'):
            self.check(package)

    def test_missing_real_project_is_rejected(self):
        inputs = dict(self.inputs, project_root=str(self.root / 'missing'))
        with self.assertRaisesRegex(ValueError, 'real character project'):
            self.check(inputs=inputs)

    def test_missing_actual_inputs_is_rejected(self):
        write_delivery(self.delivery, self.package)
        with self.assertRaisesRegex(ValueError, 'actual task inputs'):
            verify_result(envelope(), self.cap, self.delivery, plugin_root=ROOT)

    def test_text_must_be_declared(self):
        write_delivery(self.delivery, self.package)
        result = envelope()
        result['artifacts'].remove('提示词.txt')
        with self.assertRaisesRegex(ValueError, 'Required artifact'):
            verify_result(result, self.cap, self.delivery, self.inputs, ROOT)

    def test_text_summary_cannot_replace_exact_json_export(self):
        write_delivery(self.delivery, self.package)
        (self.delivery / '提示词.txt').write_text('年轻女性，写实头像。', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'exact UTF-8 export'):
            verify_result(envelope(), self.cap, self.delivery, self.inputs, ROOT)

    def test_text_crlf_cannot_silently_diverge_from_canonical_export(self):
        write_delivery(self.delivery, self.package)
        p = self.delivery / '提示词.txt'
        p.write_bytes(p.read_bytes().replace(b'\n', b'\r\n'))
        with self.assertRaisesRegex(ValueError, 'exact UTF-8 export'):
            verify_result(envelope(), self.cap, self.delivery, self.inputs, ROOT)

    def test_old_complete_nonhuman_does_not_require_new_human_contract(self):
        state = copy.deepcopy(self.state)
        state.update(pipeline_version=1, design_progression='complete')
        card = {'schema_version': 'CharacterDesignCardV1', 'morphology': 'nonhuman',
                'appearance': {'body': '圆弧翼壳、单中央镜眼的机械信鸟'}}
        card_path = self.project / 'records/legacy-card.json'
        card_path.write_text(json.dumps(card, ensure_ascii=False), encoding='utf-8')
        sha = cp.digest(card)
        state['records'] = {'design-card:CHR-TEST:base': {'path': 'records/legacy-card.json',
            'sha256': sha, 'stale': False, 'approval': {'operator': 'test:synthetic-legacy', 'sha256': sha}}}
        (self.project / 'project.json').write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
        package = copy.deepcopy(self.package)
        package.pop('design_basis')
        package.pop('reference_attire')
        package['design_card_sha256'] = sha
        package['prompts'] = [{'id': 'a', 'text': '3:4 正面机械信鸟头像，圆弧翼壳和中央镜眼，浅灰背景。'},
                              {'id': 'b', 'text': '3:4 正面机械信鸟头像，中央镜眼与左右铰接翼壳，白色背景。'}]
        self.assertEqual(len(self.check(package)), 2)

    def test_engine_rechecks_project_basis_on_recovery(self):
        def execute(capability, task, *args):
            write_delivery(task['artifact_dir'], self.package)
            return envelope(), None
        engine = Engine(ROOT, self.root / 'workspace', executor=execute)
        graph = {'id': 'prompt-gate-test', 'max_concurrency': 1, 'nodes': [{
            'id': 'prompt', 'capability': 'character-image-prompt', 'depends_on': [],
            'bindings': {key: {'from': 'inputs.' + key} for key in self.inputs},
            'idempotent': False, 'retries': 0}]}
        run_id = engine.create(graph, self.inputs)
        self.assertEqual(engine.execute(run_id)['status'], 'completed')
        (self.project / 'inputs/script.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Project source changed'):
            engine.execute(run_id)

    def test_old_pipeline_two_costume_design_keeps_original_anchor_contract(self):
        state = copy.deepcopy(self.state)
        state.update(pipeline_version=2, design_progression='complete', records={}, images=[], reviews={})

        def record(key, data):
            path = self.project / 'records' / (key.replace(':', '_') + '.json')
            path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            sha = cp.digest(data)
            state['records'][key] = {'path': str(path.relative_to(self.project)), 'sha256': sha,
                'stale': False, 'approval': {'operator': 'test:synthetic-legacy', 'sha256': sha}}
            return sha

        card_sha = record('design-card:CHR-TEST:base', {'schema_version': 'CharacterDesignCardV1',
                          'morphology': 'nonhuman', 'appearance': {'body': '圆弧翼壳机械信鸟'}})
        anchors = {}
        # Byte/hash fixtures only, not real pictures or visual-review evidence.
        for stage in ('avatar', 'expression', 'full_body'):
            prompt_sha = record('prompt-package:' + stage + ':CHR-TEST:base',
                                {'schema_version': 'CharacterPromptPackageV1', 'synthetic_hash_fixture': True})
            image = self.project / (stage + '.synthetic-image')
            image.write_bytes(('synthetic image hash fixture: ' + stage).encode())
            image_sha = cp.digest(image)
            review = {'verdict': 'pass', 'synthetic_hash_fixture': True}
            review_path = self.project / (stage + '-review.json')
            review_path.write_text(json.dumps(review), encoding='utf-8')
            review_sha = cp.digest(review)
            image_id = 'test-' + stage
            state['reviews'][image_id] = {'path': str(review_path.relative_to(self.project)), 'sha256': review_sha}
            state['images'].append({'id': image_id, 'stage': stage, 'character_id': 'CHR-TEST',
                'variant_id': 'base', 'path': image.name, 'sha256': image_sha, 'prompt_sha256': prompt_sha,
                'approval': {'operator': 'test:synthetic-legacy', 'image_sha256': image_sha, 'review_sha256': review_sha}})
            anchors[stage] = image_sha
        (self.project / 'project.json').write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
        package = copy.deepcopy(self.package)
        package.pop('design_basis')
        package.pop('reference_attire')
        package.update(stage='costume_design', variant_name='基础形象', design_card_sha256=card_sha,
                       anchor_images=anchors, prompts=[{'id': 'main', 'text': '机械信鸟正式服饰设计，保留中央镜眼和圆弧翼壳。'}],
                       acceptance_checks=['核对已批准机械信鸟的服饰结构与三张身份锚图。'])
        inputs = dict(self.inputs, stage='costume_design')
        self.assertEqual(len(self.check(package, inputs)), 2)


if __name__ == '__main__':
    unittest.main()

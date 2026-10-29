"""Explicit human-confirmation protocol fixtures, never real image approvals."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as Args
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from prompt_fixture import cp, make_avatar_project


def record(root, state, key, data):
    path = root / 'records' / (key.replace(':', '_') + '.json')
    cp.write_json(path, data)
    sha = cp.digest(data)
    state['records'][key] = {'path': str(path.relative_to(root)), 'sha256': sha, 'stale': False,
                            'approval': {'operator': 'test:synthetic-only', 'sha256': sha}}
    cp.write_json(root / 'project.json', state)
    return sha


class HumanImageApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'project'
        self.state, self.package, _ = make_avatar_project(self.root)
        self.file = self.base / 'prompt.json'
        cp.write_json(self.file, self.package)
        cp.cmd_submit(Args(project_root=self.root, kind='prompt-package', character_id='CHR-TEST',
                           variant_id='base', stage='avatar', file=self.file))
        self.picture = self.base / 'synthetic-image.png'
        self.picture.write_bytes(b'synthetic pixels; no real visual judgement is claimed')
        self.image = cp.cmd_import_image(Args(project_root=self.root, path=self.picture,
            character_id='CHR-TEST', variant_id='base', stage='avatar'))

    def args(self, **extra):
        values = {'project_root': self.root, 'image_id': self.image['id'],
                  'operator': 'test:synthetic-human-confirmation-only', 'human_reviewed': True,
                  'confirmation_ref': 'synthetic:test-driver-confirmation, not a real user message'}
        values.update(extra)
        return Args(**values)

    def test_explicit_human_confirmation_is_inline_and_usable_downstream(self):
        result = cp.cmd_approve_image(self.args())
        self.assertEqual(result['approval_method'], 'human_confirmation')
        self.assertFalse(result['automatic_visual_verdict'])
        state = cp.read_json(self.root / 'project.json')
        self.assertFalse(state['reviews'])
        self.assertFalse((self.root / 'reviews').exists())
        image = cp._checked_image(self.root, state, 'avatar', 'CHR-TEST', 'base')
        approval = image['approval']
        self.assertNotIn('verdict', approval)
        self.assertNotIn('review_sha256', approval)
        self.assertEqual(approval['image_sha256'], image['sha256'])
        self.assertEqual(approval['prompt_sha256'], image['prompt_sha256'])
        self.assertEqual(cp.image_delivery_files(state, image), (image,))

    def test_default_legacy_still_requires_report_and_human_flag_needs_confirmation(self):
        before = (self.root / 'project.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'reviewed first'):
            cp.cmd_approve_image(self.args(human_reviewed=False))
        with self.assertRaisesRegex(ValueError, 'confirmation_ref'):
            cp.cmd_approve_image(self.args(confirmation_ref=''))
        self.assertEqual((self.root / 'project.json').read_bytes(), before)

    def test_human_confirmation_does_not_bypass_current_source_or_image_bytes(self):
        for kind in ('image', 'source'):
            with self.subTest(kind=kind):
                state = cp.read_json(self.root / 'project.json')
                path = self.root / (state['images'][0]['path'] if kind == 'image' else state['inputs']['screenplay']['path'])
                original = path.read_bytes()
                path.write_bytes(original + b'changed')
                with self.assertRaisesRegex(ValueError, 'changed'):
                    cp.cmd_approve_image(self.args())
                self.assertIsNone(cp.read_json(self.root / 'project.json')['images'][0]['approval'])
                path.write_bytes(original)

    def test_changed_prompt_parent_and_upstream_impact_block_human_adoption(self):
        for kind in ('prompt', 'parent', 'impact'):
            with self.subTest(kind=kind):
                state = cp.read_json(self.root / 'project.json')
                original = copy.deepcopy(state)
                if kind == 'prompt':
                    state['images'][0]['prompt_sha256'] = '0' * 64
                elif kind == 'parent':
                    state['records']['stage-design:identity:CHR-TEST:base']['approval'] = None
                else:
                    state['pending_impact'] = {'reason': 'synthetic upstream change'}
                cp.write_json(self.root / 'project.json', state)
                with self.assertRaises(ValueError):
                    cp.cmd_approve_image(self.args())
                self.assertIsNone(cp.read_json(self.root / 'project.json')['images'][0]['approval'])
                cp.write_json(self.root / 'project.json', original)

    def test_downstream_rejects_tampered_confirmation_and_post_approval_source(self):
        cp.cmd_approve_image(self.args())
        state = cp.read_json(self.root / 'project.json')
        image = state['images'][0]
        original = copy.deepcopy(image['approval'])
        for field in ('confirmation_ref', 'human_reviewed', 'prompt_sha256', 'image_sha256'):
            with self.subTest(field=field):
                image['approval'] = copy.deepcopy(original)
                image['approval'][field] = ''
                with self.assertRaises(ValueError):
                    cp._checked_image(self.root, state, 'avatar', 'CHR-TEST', 'base')
        image['approval'] = original
        source = self.root / state['inputs']['screenplay']['path']
        source.write_bytes(source.read_bytes() + b' changed after approval')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            cp._checked_image(self.root, state, 'avatar', 'CHR-TEST', 'base')

    def test_preview_can_be_promoted_by_real_human_confirmation_without_review(self):
        state = cp.read_json(self.root / 'project.json')
        self.package['purpose'] = 'preview'
        self.package['preview_mode'] = 'direction_first'
        sha = record(self.root, state, 'prompt-package:avatar:CHR-TEST:base', self.package)
        state = cp.read_json(self.root / 'project.json')
        state['images'][0].update(purpose='preview', prompt_sha256=sha)
        cp.write_json(self.root / 'project.json', state)
        with self.assertRaisesRegex(ValueError, 'promote-candidate'):
            cp.cmd_approve_image(self.args())
        command = [sys.executable, str(ROOT / 'scripts/character_project.py'), 'promote-candidate',
                   '--project-root', str(self.root), '--image-id', self.image['id'],
                   '--operator', 'test:synthetic-only', '--human-reviewed', '--confirmation-ref',
                   'synthetic:test-driver-confirmation']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['promoted'])
        state = cp.read_json(self.root / 'project.json')
        self.assertFalse(state['reviews'])
        self.assertEqual(state['images'][0]['purpose'], 'production')
        cp._checked_image(self.root, state, 'avatar', 'CHR-TEST', 'base')

    def test_human_image_choice_cannot_silently_adopt_unapproved_design(self):
        state = cp.read_json(self.root / 'project.json')
        self.package.update(purpose='preview', preview_mode='direction_first')
        sha = record(self.root, state, 'prompt-package:avatar:CHR-TEST:base', self.package)
        state = cp.read_json(self.root / 'project.json')
        state['images'][0].update(purpose='preview', prompt_sha256=sha)
        state['records']['stage-design:identity:CHR-TEST:base']['approval'] = None
        cp.write_json(self.root / 'project.json', state)
        before = (self.root / 'project.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Required approved record'):
            cp.cmd_human_image_approval(self.args(), promote=True)
        self.assertEqual((self.root / 'project.json').read_bytes(), before)

    def test_human_confirmation_retains_exact_upstream_image_binding(self):
        cp.cmd_approve_image(self.args())
        state = cp.read_json(self.root / 'project.json')
        package = copy.deepcopy(self.package)
        package['stage'] = 'expression'
        package['anchor_images'] = {'avatar': '0' * 64}
        record(self.root, state, 'prompt-package:expression:CHR-TEST:base', package)
        image = cp.cmd_import_image(Args(project_root=self.root, path=self.picture, stage='expression',
                                        character_id='CHR-TEST', variant_id='base'))
        before = (self.root / 'project.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'anchor versions'):
            cp.cmd_approve_image(self.args(image_id=image['id']))
        self.assertEqual((self.root / 'project.json').read_bytes(), before)

    def test_complete_legacy_pack_uses_inline_confirmations_without_review_files(self):
        state = cp.read_json(self.root / 'project.json')
        state.update(pipeline_version=1, design_progression='complete', images=[], reviews={})
        card_sha = record(self.root, state, 'design-card:CHR-TEST:base',
                          {'schema_version': 'CharacterDesignCardV1', 'synthetic_test_only': True})
        for stage in cp.LEGACY_STAGES:
            state = cp.read_json(self.root / 'project.json')
            anchors = {s: cp._checked_image(self.root, state, s, 'CHR-TEST', 'base')['sha256']
                       for s in cp.image_predecessors(state, stage)}
            package = {'schema_version': 'CharacterPromptPackageV1', 'character_id': 'CHR-TEST',
                       'variant_id': 'base', 'stage': stage, 'design_card_sha256': card_sha,
                       'anchor_images': anchors, 'prompts': [{'id': 'main', 'text': f'Synthetic historical {stage} prompt.'}]}
            record(self.root, state, f'prompt-package:{stage}:CHR-TEST:base', package)
            picture = self.base / f'{stage}-fixture.png'
            picture.write_bytes(f'synthetic {stage} bytes'.encode())
            image = cp.cmd_import_image(Args(project_root=self.root, path=picture, stage=stage,
                                            character_id='CHR-TEST', variant_id='base'))
            cp.cmd_approve_image(self.args(image_id=image['id']))
        output = self.base / 'legacy-pack'
        result = cp.cmd_package(Args(project_root=self.root, character_id='CHR-TEST', variant_id='base', output=output))
        self.assertTrue(result['asset_pack'])
        manifest = cp.read_json(output / 'manifest.json')
        self.assertEqual(len(manifest['approved_images']), 4)
        self.assertFalse((output / 'reviews').exists())
        for image in manifest['approved_images'].values():
            self.assertEqual(image['approval']['method'], 'human_confirmation')
            self.assertNotIn('verdict', image['approval'])
        for item in manifest['files']:
            self.assertEqual(cp.digest(output / item['path']), item['sha256'])

    def test_speaking_extra_pack_does_not_require_a_fake_review(self):
        from test_ensemble_design_coverage import make_project, extra_prompt
        root = self.base / 'extra'
        state, design, sha, store_record = make_project(root)
        package = extra_prompt(design)
        package['design_basis']['records'] = {'extra-design:CHR-EXTRA:S01': sha}
        store_record('prompt-package:execution:CHR-EXTRA:S01', package)
        cp.write_json(root / 'project.json', state)
        image = cp.cmd_import_image(Args(project_root=root, path=self.picture, stage='execution',
                                        character_id='CHR-EXTRA', variant_id='S01'))
        cp.cmd_approve_image(self.args(project_root=root, image_id=image['id']))
        output = self.base / 'extra-pack'
        result = cp.cmd_package(Args(project_root=root, character_id='CHR-EXTRA', variant_id='S01', output=output))
        self.assertTrue(result['asset_pack'])
        self.assertFalse((output / 'reviews').exists())
        self.assertFalse(cp.read_json(root / 'project.json')['reviews'])


if __name__ == '__main__':
    unittest.main()

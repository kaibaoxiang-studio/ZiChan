"""Synthetic state transitions; no production approvals or actual image claims."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace as Args
import unittest

from test_design_execution_gate import cp, phased, current_identity
from prompt_fixture import make_avatar_project


def state_matrix():
    state = {'pipeline_version': 3, 'design_progression': 'phased', 'records': {}, 'images': []}
    for character in ('CHR-A', 'CHR-B'):
        keys = [f'design-brief:{character}:base', f'stage-design:identity:{character}:base',
                f'stage-design:body:{character}:base', f'costume-bible:{character}:base']
        for variant in ('S01', 'S02'):
            keys.extend([f'stage-design:costume:{character}:{variant}', f'design-card:{character}:{variant}',
                         f'prompt-package:execution:{character}:{variant}'])
            state['images'].append({'id': f'{character}-{variant}', 'stage': 'execution', 'character_id': character,
                                    'variant_id': variant, 'approval': {'operator': 'test:fixture-only'}})
        for stage in ('avatar', 'expression', 'full_body'):
            keys.append(f'prompt-package:{stage}:{character}:base')
            state['images'].append({'id': f'{character}-{stage}', 'stage': stage, 'character_id': character,
                                    'variant_id': 'base', 'approval': {'operator': 'test:fixture-only'}})
        for key in keys:
            state['records'][key] = {'approval': {'operator': 'test:fixture-only'}, 'stale': False}
    return state


class ScopedInvalidation(unittest.TestCase):
    def test_costume_change_only_invalidates_affected_state(self):
        state = state_matrix()
        other = copy.deepcopy({key: value for key, value in state['records'].items() if 'CHR-B' in key})
        phased.invalidate(cp, state, 'CHR-A', 'costume', 'S01')
        for key in ('stage-design:costume:CHR-A:S01', 'design-card:CHR-A:S01', 'prompt-package:execution:CHR-A:S01'):
            self.assertTrue(state['records'][key]['stale'])
        for key in ('stage-design:identity:CHR-A:base', 'stage-design:body:CHR-A:base',
                    'costume-bible:CHR-A:base', 'stage-design:costume:CHR-A:S02', 'prompt-package:avatar:CHR-A:base'):
            self.assertFalse(state['records'][key]['stale'])
        self.assertEqual(other, {key: value for key, value in state['records'].items() if 'CHR-B' in key})

    def test_body_change_keeps_identity_and_invalidates_body_descendants(self):
        state = state_matrix()
        phased.invalidate(cp, state, 'CHR-A', 'body')
        for key in ('stage-design:identity:CHR-A:base', 'design-brief:CHR-A:base',
                    'prompt-package:avatar:CHR-A:base', 'prompt-package:expression:CHR-A:base'):
            self.assertFalse(state['records'][key]['stale'])
        for key in ('stage-design:body:CHR-A:base', 'costume-bible:CHR-A:base',
                    'stage-design:costume:CHR-A:S01', 'stage-design:costume:CHR-A:S02',
                    'prompt-package:full_body:CHR-A:base'):
            self.assertTrue(state['records'][key]['stale'])
        self.assertTrue(all(not image.get('stale') for image in state['images'] if image['character_id'] == 'CHR-B'))

    def test_style_bible_change_keeps_identity_and_body(self):
        state = state_matrix()
        phased.invalidate_bible(cp, state, 'CHR-A')
        self.assertFalse(state['records']['stage-design:body:CHR-A:base']['stale'])
        self.assertFalse(state['records']['prompt-package:full_body:CHR-A:base']['stale'])
        self.assertTrue(state['records']['stage-design:costume:CHR-A:S01']['stale'])
        self.assertTrue(state['records']['stage-design:costume:CHR-A:S02']['stale'])


class PreviewPromotion(unittest.TestCase):
    def test_current_identity_draft_requires_explicit_approval_and_reuses_same_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            base, root = Path(folder), Path(folder) / 'project'
            state, identity = current_identity(root)
            identity_record = phased._store(cp, root, state, 'stage-design:identity:CHR-TEST:base', identity)
            cp.write_json(root / 'project.json', state)
            _, package, _ = make_avatar_project(base / 'prompt-source')
            package.update(purpose='preview', preview_mode='direction_first')
            package['design_basis']['records']['stage-design:identity:CHR-TEST:base'] = identity_record['sha256']
            file = base / 'package.json'
            cp.write_json(file, package)
            cp.cmd_submit(Args(project_root=root, kind='prompt-package', character_id='CHR-TEST', variant_id='base',
                               stage='avatar', file=file))
            picture = base / 'synthetic.png'
            picture.write_bytes(b'synthetic picture bytes, not real image review')
            image = cp.cmd_import_image(Args(project_root=root, path=picture, character_id='CHR-TEST',
                                            variant_id='base', stage='avatar'))
            report = {'schema_version': 'CharacterImageReviewV1', 'image_sha256': image['sha256'], 'stage': 'avatar',
                      'verdict': 'pass', **{name: [] for name in ('factual_conflicts', 'identity_issues', 'layout_issues',
                      'label_issues', 'blocking_issues', 'adoption_proposals')}}
            review = base / 'review.json'
            cp.write_json(review, report)
            cp.cmd_submit_review(Args(project_root=root, image_id=image['id'], file=review))
            with self.assertRaisesRegex(ValueError, 'promote-candidate'):
                cp.cmd_approve_image(Args(project_root=root, image_id=image['id'], operator='test:fixture-only'))
            args = Args(project_root=root, image_id=image['id'], operator='test:fixture-only', approve_design_basis=False)
            with self.assertRaisesRegex(ValueError, 'approved'):
                phased.promote(cp, args)
            self.assertIsNone(cp.read_json(root / 'project.json')['records']['stage-design:identity:CHR-TEST:base']['approval'])
            args.approve_design_basis = True
            result = phased.promote(cp, args)
            self.assertEqual(result['same_image_sha256'], image['sha256'])
            current = cp.read_json(root / 'project.json')
            anchor = cp._checked_image(root, current, 'avatar', 'CHR-TEST', 'base')
            self.assertEqual(anchor['id'], image['id'])
            self.assertEqual(anchor['purpose'], 'production')
            self.assertEqual(cp.digest(root / anchor['path']), cp.digest(picture))


if __name__ == '__main__':
    unittest.main()

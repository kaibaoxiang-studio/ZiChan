from pathlib import Path
import tempfile
import unittest

from prompt_fixture import cp


class HandoffPathGate(unittest.TestCase):
    def test_regular_project_proposal_is_read(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root / 'drafts/specialists/proposal.json'
            cp.write_json(file, {'design': '具体原稿'})
            self.assertEqual(cp.checked_handoff_file(root, 'drafts/specialists/proposal.json', cp.digest(file), 'proposal'),
                             {'design': '具体原稿'})

    def test_specialists_directory_symlink_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root, outside = base / 'project', base / 'outside'
            (root / 'drafts').mkdir(parents=True)
            cp.write_json(outside / 'proposal.json', {'design': '外部文件'})
            try:
                (root / 'drafts/specialists').symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('This platform/account cannot create symlinks')
            with self.assertRaisesRegex(ValueError, 'outside project'):
                cp.checked_handoff_file(root, 'drafts/specialists/proposal.json', cp.digest(outside / 'proposal.json'), 'proposal')

    def test_proposal_file_symlink_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root = base / 'project'
            (root / 'drafts/specialists').mkdir(parents=True)
            cp.write_json(base / 'outside.json', {'design': '外部文件'})
            try:
                (root / 'drafts/specialists/proposal.json').symlink_to(base / 'outside.json')
            except OSError:
                self.skipTest('This platform/account cannot create symlinks')
            with self.assertRaisesRegex(ValueError, 'outside project'):
                cp.checked_handoff_file(root, 'drafts/specialists/proposal.json', cp.digest(base / 'outside.json'), 'proposal')


if __name__ == '__main__':
    unittest.main()

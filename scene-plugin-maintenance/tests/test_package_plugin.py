import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('package_plugin', ROOT / 'scene-plugin-maintenance/package_plugin.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'scene-assets', self.root / 'scene-assets')
        shutil.copytree(ROOT / '.agents', self.root / '.agents')

    def test_valid_package(self):
        files, market = package.validate(self.root)
        self.assertEqual(market['name'], 'scene-assets-local')
        self.assertIn('skills/sence-prompts/SKILL.md', files)

    def test_reject_mismatched_version(self):
        path = self.root / 'scene-assets/.codex-plugin/plugin.json'
        data = json.loads(path.read_text())
        data['version'] = '1.0.0'
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            package.validate(self.root)

    def test_reject_missing_resource(self):
        (self.root / 'scene-assets/skills/sence-prompts/agents/openai.yaml').unlink()
        with self.assertRaises(ValueError):
            package.validate(self.root)

    def test_reject_symlink(self):
        (self.root / 'scene-assets/external').symlink_to(self.root / '.agents', target_is_directory=True)
        with self.assertRaises(ValueError):
            package.validate(self.root)

    def test_reject_wrong_marketplace_path(self):
        path = self.root / '.agents/plugins/marketplace.json'
        data = json.loads(path.read_text())
        data['plugins'][0]['source']['path'] = '../unrelated'
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            package.validate(self.root)

    def test_reproducible_zips_and_corruption_detection(self):
        files, market = package.validate(self.root)
        for name, entries in package.zip_entries(files, market).items():
            target = self.root / name
            package.write_zip(target, entries)
            first = target.read_bytes()
            package.write_zip(target, entries)
            self.assertEqual(first, target.read_bytes())
            package.verify_zip(target, entries)
            changed = dict(entries)
            changed[next(iter(changed))] = b'changed'
            with self.assertRaises(ValueError):
                package.verify_zip(target, changed)


if __name__ == '__main__':
    unittest.main()

"""Real offline venv execution, including shared-base symlink identities."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]


class LauncherEnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plugin = self.root / 'plugin'
        self.plugin.mkdir()
        shutil.copyfile(ROOT / 'harness.py', self.plugin / 'harness.py')
        (self.plugin / 'requirements.lock').write_text('offline-launcher-fixture\n', encoding='utf-8')
        runtime = self.plugin / 'runtime/harness_core'
        runtime.mkdir(parents=True)
        (runtime / '__init__.py').write_text('', encoding='utf-8')
        (runtime / 'cli.py').write_text(
            'import json, sys\ndef main(root):\n'
            '    print(json.dumps({"marker":"actual-fallback-runtime", "prefix":sys.prefix, '
            '"executable":sys.executable, "arguments":sys.argv[1:]}))\n    return 0\n', encoding='utf-8')
        self.fake_user_home = self.root / 'user-home'
        self.fake_user_home.mkdir()
        # Isolate Path.home() only inside these child test processes. No cache
        # under the real user home, installed plugin or Codex config is touched.
        self.env = {**os.environ, 'HOME': str(self.fake_user_home), 'USERPROFILE': str(self.fake_user_home), 'PYTHONDONTWRITEBYTECODE': '1'}
        self.env.pop('HARNESS_LAUNCHER_TRIED_ENVIRONMENTS', None)
        self.env.pop('PYTHONPATH', None)
        self.env.pop('PYTHONHOME', None)
        self.suffix = Path('Scripts/python.exe') if os.name == 'nt' else Path('bin/python')
        self.caller_root = self.root / 'caller'
        self.fallback_root = self.plugin / '.venv'
        # No pip, network, mocks or copied binaries: actual environments share
        # their underlying base interpreter but own distinct site-packages.
        for environment in (self.caller_root, self.fallback_root):
            venv.EnvBuilder(with_pip=False, symlinks=os.name != 'nt').create(environment)
        self.caller = self.caller_root / self.suffix
        self.fallback = self.fallback_root / self.suffix

    def dependencies(self, executable):
        purelib = subprocess.check_output([str(executable), '-B', '-c',
            'import sysconfig; print(sysconfig.get_path("purelib"))'], text=True, env=self.env).strip()
        for name in ('yaml', 'jsonschema', 'xlsxwriter'):
            (Path(purelib) / (name + '.py')).write_text('OFFLINE_LAUNCHER_FIXTURE = True\n', encoding='utf-8')

    def launch(self, executable=None):
        return subprocess.run([str(executable or self.caller), '-B', str(self.plugin / 'harness.py'), 'validate'],
                              text=True, capture_output=True, env=self.env, timeout=10)

    def test_shared_binary_different_venv_reaches_actual_fallback_runtime(self):
        if os.name != 'nt':
            self.assertEqual(self.caller.resolve(), self.fallback.resolve())
        self.dependencies(self.fallback)
        missing = subprocess.check_output([str(self.caller), '-B', '-c',
            'import importlib.util,json; print(json.dumps([importlib.util.find_spec(n) is None for n in ("yaml","jsonschema","xlsxwriter")]))'],
            text=True, env=self.env)
        self.assertEqual(json.loads(missing), [True, True, True])
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence['marker'], 'actual-fallback-runtime')
        self.assertEqual(Path(evidence['prefix']).resolve(), self.fallback_root.resolve())
        self.assertEqual(evidence['arguments'], ['validate'])

    def test_same_environment_alias_does_not_reexec_forever(self):
        executable = self.fallback_root / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python3')
        result = self.launch(executable)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Dependencies are missing', result.stderr)
        self.assertNotIn('actual-fallback-runtime', result.stdout)

    def test_two_incomplete_environments_fail_controlled_instead_of_bouncing(self):
        key = hashlib.sha256((self.plugin / 'requirements.lock').read_bytes()).hexdigest()[:16]
        cache_root = self.fake_user_home / '.cache/harness-runtime' / key / f'py{sys.version_info.major}{sys.version_info.minor}'
        cache_root.parent.mkdir(parents=True)
        # Reuse the already-created second real environment as the cache choice;
        # local .venv and cache then both lack dependencies.
        shutil.move(self.caller_root, cache_root)
        result = self.launch(self.fallback)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Dependencies are missing', result.stderr)
        self.assertNotIn('actual-fallback-runtime', result.stdout)


if __name__ == '__main__':
    unittest.main()

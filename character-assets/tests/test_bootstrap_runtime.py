"""Create a real cached interpreter without fetching any dependency packages."""
from pathlib import Path
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('character_bootstrap', ROOT / 'scripts/bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)

class BootstrapRuntimeTest(unittest.TestCase):
    def test_created_cache_can_locate_its_real_standard_library(self):
        # The source launcher may itself be a symlink to an independently
        # installed interpreter. A copied standalone binary can retain /install
        # as its prefix even though its package is elsewhere on the machine.
        with tempfile.TemporaryDirectory() as folder:
            real_run = subprocess.run
            created = []
            def offline_install(command, *args, **kwargs):
                if len(command) >= 4 and command[1:4] == ['-m', 'pip', 'install']:
                    created.append(Path(command[0]))
                    self.assertIn('--require-hashes', command)
                    self.assertIn('--only-binary=:all:', command)
                    return subprocess.CompletedProcess(command, 0)
                if command[-2:] == ['-c', 'import yaml,jsonschema']:
                    return subprocess.CompletedProcess(command, 0)
                return real_run(command, *args, **kwargs)
            with mock.patch.object(Path, 'home', return_value=Path(folder)), \
                 mock.patch.object(sys, 'argv', ['bootstrap.py', '--install']), \
                 mock.patch.object(subprocess, 'run', side_effect=offline_install):
                bootstrap.main()
            self.assertEqual(len(created), 1)
            executable = created[0]
            checked = real_run([str(executable), '-c', 'import encodings,sys; print(sys.version_info[:2])'],
                               capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(checked.stdout.strip(), str(sys.version_info[:2]))
            if os.name != 'nt':
                self.assertTrue(executable.is_symlink())

if __name__ == '__main__':
    unittest.main()

"""Run simulated Windows API control flow on real files; no Windows-host claim."""
import builtins
import ctypes
from ctypes import wintypes
import errno
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
sys.path.insert(0, str(ROOT / 'scripts'))
import character_project as cp
from harness_core import engine as runtime


def windows_os():
    proxy = SimpleNamespace(**dict(vars(os), name='nt'))
    proxy.kill = mock.Mock(side_effect=AssertionError('Windows probe must never call kill'))
    return proxy


class WindowsProjectLock(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'project.json'
        self.state = {'schema_version': cp.SCHEMA, 'revision': 7,
                      'records': {'approved-old': {'sha256': 'old-sha', 'approval': {'operator': 'old'}}}}
        self.path.write_text(json.dumps(self.state), encoding='utf-8')
        self.calls = []
        self.busy = False
        def locking(fd, mode, count):
            self.calls.append((fd, mode, count, os.lseek(fd, 0, os.SEEK_CUR), os.fstat(fd).st_size))
            if self.busy and mode == 2:
                raise BlockingIOError(errno.EACCES, 'fixture: already locked')
        self.msvcrt = SimpleNamespace(LK_NBLCK=2, LK_UNLCK=0, locking=locking)
        self.os_patch = mock.patch.object(cp, 'os', windows_os())
        self.os_patch.start()
        self.addCleanup(self.os_patch.stop)
        self.module_patch = mock.patch.dict(sys.modules, {'msvcrt': self.msvcrt})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)

    def test_success_uses_same_existing_byte_and_releases_without_changing_old_approvals(self):
        legacy_lock = b'legacy lock content\r\n'
        (self.root / '.lock').write_bytes(legacy_lock)
        actual_import = builtins.__import__
        def reject_fcntl(name, *args, **kwargs):
            if name == 'fcntl':
                raise AssertionError('Windows must not import fcntl')
            return actual_import(name, *args, **kwargs)
        with mock.patch('builtins.__import__', side_effect=reject_fcntl):
            with cp.locked_project(self.root) as (_, state):
                state['new_value'] = 'changed under lock'
        self.assertEqual([(mode, count, offset) for _, mode, count, offset, _ in self.calls],
                         [(2, 1, 0), (0, 1, 0)])
        self.assertEqual(self.calls[0][0], self.calls[1][0])
        with self.assertRaises(OSError):
            os.fstat(self.calls[0][0])  # descriptor is closed after unlock
        current = cp.read_json(self.path)
        self.assertEqual(current['revision'], 8)
        self.assertEqual(current['records'], self.state['records'])
        self.assertEqual((self.root / '.lock').read_bytes(), legacy_lock)

    def test_new_lock_has_a_real_first_byte_before_locking(self):
        with cp.locked_project(self.root):
            self.assertEqual((self.root / '.lock').read_bytes(), b'\0')
        self.assertTrue(all(size >= 1 for _, _, _, _, size in self.calls))

    def test_body_failure_unlocks_and_preserves_entire_old_project(self):
        original = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'business failed'):
            with cp.locked_project(self.root) as (_, state):
                state['records'].clear()
                raise RuntimeError('business failed')
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual([call[1] for call in self.calls], [2, 0])
        with self.assertRaises(OSError):
            os.fstat(self.calls[-1][0])

    def test_busy_lock_never_enters_or_writes_old_project(self):
        original = self.path.read_bytes()
        (self.root / '.lock').write_bytes(b'old-lock')
        self.busy = True
        with self.assertRaises(BlockingIOError):
            with cp.locked_project(self.root):
                self.fail('busy project entered its write transaction')
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual((self.root / '.lock').read_bytes(), b'old-lock')
        self.assertEqual([call[1] for call in self.calls], [2])
        with self.assertRaises(OSError):
            os.fstat(self.calls[-1][0])

    @unittest.skipIf(os.name == 'nt', 'Real POSIX branch is exercised on a POSIX host')
    def test_posix_still_uses_exclusive_flock(self):
        import fcntl
        with mock.patch.object(cp, 'os', os), mock.patch.object(fcntl, 'flock', wraps=fcntl.flock) as flock:
            with cp.locked_project(self.root):
                pass
        self.assertEqual(flock.call_args.args[1], fcntl.LOCK_EX)
        self.assertEqual(cp.read_json(self.path)['records'], self.state['records'])


class WindowsSchedulerProbe(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / '.harness/run-old'
        self.base.mkdir(parents=True)
        self.lock = self.base / 'scheduler.lock'
        self.lock.write_text('12345', encoding='ascii')
        self.old_record = self.base / 'approved-result.json'
        self.old_record.write_bytes(b'{"approved":true,"sha256":"old"}\n')
        self.old_bytes = self.old_record.read_bytes()
        self.engine = runtime.Engine.__new__(runtime.Engine)
        self.engine.workspace = self.root
        self.engine.executor = SimpleNamespace(close=mock.Mock())
        self.engine._execute = mock.Mock(return_value={'status': 'fixture-success'})
        self.win = windows_os()
        self.kernel = SimpleNamespace(OpenProcess=mock.Mock(return_value=0x1234567887654321),
                                      WaitForSingleObject=mock.Mock(return_value=0x102),
                                      CloseHandle=mock.Mock(return_value=1))
        self.error = mock.Mock(return_value=5)
        self.patches = [mock.patch.object(runtime, 'os', self.win),
                        mock.patch.object(ctypes, 'WinDLL', return_value=self.kernel, create=True),
                        mock.patch.object(ctypes, 'get_last_error', self.error, create=True)]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def assert_old_unchanged(self):
        self.assertEqual(self.old_record.read_bytes(), self.old_bytes)
        self.win.kill.assert_not_called()

    def test_active_scheduler_is_not_killed_and_lock_is_preserved(self):
        with self.assertRaisesRegex(RuntimeError, 'already owns'):
            self.engine.execute('run-old')
        self.assertEqual(self.lock.read_text(), '12345')
        self.engine._execute.assert_not_called()
        self.kernel.OpenProcess.assert_called_once_with(0x00100000, False, 12345)
        handle = self.kernel.OpenProcess.return_value
        self.kernel.WaitForSingleObject.assert_called_once_with(handle, 0)
        self.kernel.CloseHandle.assert_called_once_with(handle)
        self.assertIs(self.kernel.OpenProcess.restype, wintypes.HANDLE)
        self.assertEqual(self.kernel.WaitForSingleObject.argtypes, [wintypes.HANDLE, wintypes.DWORD])
        self.assert_old_unchanged()

    def test_terminated_scheduler_can_recover_and_releases_own_lock_even_on_failure(self):
        self.kernel.WaitForSingleObject.return_value = 0
        def failed(*args):
            self.assertEqual(self.lock.read_text(), str(os.getpid()))
            raise RuntimeError('fixture work failed')
        self.engine._execute.side_effect = failed
        with self.assertRaisesRegex(RuntimeError, 'work failed'):
            self.engine.execute('run-old')
        self.assertFalse(self.lock.exists())
        self.kernel.CloseHandle.assert_called_once()
        self.engine.executor.close.assert_called_once()
        self.assert_old_unchanged()

    def test_missing_process_recovers_without_waiting_or_closing_a_null_handle(self):
        self.kernel.OpenProcess.return_value = 0
        self.error.return_value = 87
        self.assertEqual(self.engine.execute('run-old'), {'status': 'fixture-success'})
        self.assertFalse(self.lock.exists())
        self.kernel.WaitForSingleObject.assert_not_called()
        self.kernel.CloseHandle.assert_not_called()
        self.assert_old_unchanged()

    def test_denied_or_unknown_process_state_preserves_lock_and_old_records(self):
        self.kernel.OpenProcess.return_value = 0
        for error in (5, 6, 0):
            self.error.return_value = error
            with self.subTest(error=error), self.assertRaises(OSError):
                self.engine.execute('run-old')
            self.assertEqual(self.lock.read_text(), '12345')
        self.kernel.CloseHandle.assert_not_called()
        self.engine._execute.assert_not_called()
        self.assert_old_unchanged()

    def test_failed_wait_still_closes_handle_and_does_not_recover_lock(self):
        self.kernel.WaitForSingleObject.return_value = 0xffffffff
        with self.assertRaises(OSError):
            self.engine.execute('run-old')
        self.kernel.CloseHandle.assert_called_once_with(self.kernel.OpenProcess.return_value)
        self.assertEqual(self.lock.read_text(), '12345')
        self.engine._execute.assert_not_called()
        self.assert_old_unchanged()

    def test_failed_handle_close_cannot_be_treated_as_safe_recovery(self):
        self.kernel.WaitForSingleObject.return_value = 0
        self.kernel.CloseHandle.return_value = 0
        with self.assertRaises(OSError):
            self.engine.execute('run-old')
        self.kernel.CloseHandle.assert_called_once()
        self.assertEqual(self.lock.read_text(), '12345')
        self.engine._execute.assert_not_called()
        self.assert_old_unchanged()

    def test_invalid_or_malformed_old_pid_is_preserved_without_any_process_call(self):
        for pid in ('0', '-7', str(0x100000000), 'broken-pid'):
            self.lock.write_text(pid, encoding='ascii')
            with self.subTest(pid=pid), self.assertRaises(ValueError):
                self.engine.execute('run-old')
            self.assertEqual(self.lock.read_text(), pid)
        self.kernel.OpenProcess.assert_not_called()
        self.engine._execute.assert_not_called()
        self.assert_old_unchanged()

    def test_posix_probe_keeps_signal_zero_behavior(self):
        posix = SimpleNamespace(**dict(vars(os), name='posix'))
        posix.kill = mock.Mock()
        with mock.patch.object(runtime, 'os', posix):
            self.assertTrue(runtime._scheduler_pid_alive(12345))
            posix.kill.assert_called_once_with(12345, 0)
            posix.kill.side_effect = ProcessLookupError()
            self.assertFalse(runtime._scheduler_pid_alive(12345))
            posix.kill.side_effect = PermissionError()
            with self.assertRaises(PermissionError):
                runtime._scheduler_pid_alive(12345)


if __name__ == '__main__':
    unittest.main()

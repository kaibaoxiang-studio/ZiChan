"""Real local protocol stubs: UTF-8, process cleanup, cancellation and reentry.

These tests never open a model connection or create a visible Codex chat.
"""
import json
import locale
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
from harness_core.appserver import AppServer, envelope_schema
from harness_core.engine import Engine, Executor

SERVER = r'''
import json, sys, uuid
from pathlib import Path
log, behavior = Path(sys.argv[1]), sys.argv[2]
active = None
def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)
for line in sys.stdin:
    message = json.loads(line)
    with log.open('a', encoding='utf-8') as output:
        output.write(json.dumps(message, ensure_ascii=False) + '\n')
    method, identifier = message.get('method'), message.get('id')
    params = message.get('params', {})
    if method == 'initialize':
        if behavior == 'startup-fail':
            print('启动失败：无法写入会话数据库。', file=sys.stderr, flush=True)
            raise SystemExit(2)
        emit({'id': identifier, 'result': {}})
    elif method == 'thread/start':
        active = 'ephemeral-' + uuid.uuid4().hex
        emit({'id': identifier, 'result': {'thread': {'id': active, 'ephemeral': True}}})
    elif method == 'thread/resume':
        raise RuntimeError('No persistent resume is permitted')
    elif method == 'turn/start':
        raw = params['input'][0]['text']
        task = json.loads(raw.split('<task>\n', 1)[1].rsplit('\n</task>', 1)[0])
        turn = 'turn-' + uuid.uuid4().hex
        emit({'id': identifier, 'result': {'turn': {'id': turn}}})
        if behavior == 'hang':
            continue
        blocked = behavior == 'blocked' and not task.get('answers')
        output = {'status': 'blocked' if blocked else 'succeeded', 'result': {'value': '中文与🙂'},
                  'artifacts': [], 'questions': ['确认方向？'] if blocked else [], 'error': None}
        emit({'method': 'item/completed', 'params': {'threadId': active, 'turnId': turn,
              'item': {'type': 'agentMessage', 'id': 'answer', 'text': json.dumps(output, ensure_ascii=False)}}})
        emit({'method': 'turn/completed', 'params': {'threadId': active,
              'turn': {'id': turn, 'status': 'failed' if behavior == 'turn-fail' else 'completed',
                       'error': '真实执行失败' if behavior == 'turn-fail' else None}}})
    elif method == 'turn/interrupt':
        emit({'id': identifier, 'result': {}})
'''


class RuntimeLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.server = self.root / 'stub.py'
        self.server.write_text(SERVER, encoding='utf-8')
        self.log = self.root / 'protocol.jsonl'
        self.plugin = self.root / 'plugin'
        self.skill = self.plugin / 'skills/isolated/SKILL.md'
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text('人物设计能力中文协议夹具🙂，不得调用模型。', encoding='utf-8')
        self.schema = {'type': 'object', 'properties': {'value': {'type': 'string'}}, 'required': ['value'],
                       'additionalProperties': False}

    def client(self, behavior='normal'):
        client = AppServer([sys.executable, str(self.server), str(self.log), behavior])
        self.addCleanup(client.close)
        return client

    def run_client(self, client, **kwargs):
        return client.run(self.skill, {'inputs': {'request': '中文人物小传🙂'}, 'answers': {}},
                          envelope_schema(self.schema), self.root / 'artifacts', timeout=2, **kwargs)

    def messages(self):
        return [json.loads(line) for line in self.log.read_text(encoding='utf-8').splitlines()]

    def test_utf8_stdio_is_explicit_even_under_non_utf8_host_locale(self):
        actual = subprocess.Popen
        with mock.patch.object(locale, 'getencoding', return_value='cp1252'), \
             mock.patch('harness_core.appserver.subprocess.Popen', wraps=actual) as spawn:
            client = self.client()
            result, _ = self.run_client(client)
            self.assertEqual(result['result']['value'], '中文与🙂')
            self.assertEqual(spawn.call_args.kwargs['encoding'], 'utf-8')
            self.assertEqual(spawn.call_args.kwargs['env']['PYTHONIOENCODING'], 'utf-8')
            self.assertEqual(client.process.stdin.encoding, 'utf-8')

    def test_startup_failure_includes_bounded_stderr_and_discards_process(self):
        client = self.client('startup-fail')
        with self.assertRaisesRegex(RuntimeError, '启动失败：无法写入会话数据库') as raised:
            client.start()
        self.assertLess(len(str(raised.exception)), 16500)
        self.assertIsNone(client.process)
        self.assertEqual(client.readers, [])
        client.command[-1] = 'normal'
        result, _ = self.run_client(client)
        self.assertEqual(result['status'], 'succeeded')

    def test_closed_client_can_start_again_with_a_fresh_ephemeral_thread(self):
        client = self.client()
        _, first = self.run_client(client)
        client.close()
        self.assertIsNone(client.process)
        self.assertEqual(client.readers, [])
        _, second = self.run_client(client, thread_id=first)
        self.assertNotEqual(first, second)
        starts = [row for row in self.messages() if row.get('method') == 'thread/start']
        self.assertEqual(len(starts), 2)
        self.assertTrue(all(row['params']['ephemeral'] is True for row in starts))
        self.assertFalse(any(row.get('method') == 'thread/resume' for row in self.messages()))

    def test_failed_model_turn_cannot_reuse_a_succeeded_message(self):
        with self.assertRaisesRegex(RuntimeError, 'Agent ended failed'):
            self.run_client(self.client('turn-fail'))

    def test_cancel_interrupts_only_the_ephemeral_active_turn(self):
        canceled = threading.Event()
        timer = threading.Timer(0.15, canceled.set)
        timer.start()
        self.addCleanup(timer.cancel)
        with self.assertRaises(InterruptedError):
            self.run_client(self.client('hang'), cancel=canceled)
        self.assertTrue(any(row.get('method') == 'turn/interrupt' for row in self.messages()))

    def test_same_engine_blocked_resume_creates_another_client_not_persistent_resume(self):
        cap = {'id': 'isolated', 'skill_name': 'isolated', 'input_schema': {'type': 'object'},
               'output_schema': self.schema, 'execution': {'kind': 'agent'}}
        (self.plugin / 'capabilities.json').write_text(json.dumps({'capabilities': [cap]}), encoding='utf-8')
        created = []
        def factory():
            value = self.client('blocked')
            created.append(value)
            return value
        with mock.patch('harness_core.engine.AppServer', side_effect=factory):
            engine = Engine(self.plugin, self.root / 'workspace')
            workflow = {'nodes': [{'id': 'design', 'capability': 'isolated', 'depends_on': [],
                                   'bindings': {'request': {'from': 'inputs.request'}}, 'retries': 0}]}
            run_id = engine.create(workflow, {'request': '人物设计🙂'})
            first = engine.execute(run_id)
            self.assertEqual(first['status'], 'awaiting_input')
            self.assertIsNone(engine.executor.client)
            second = engine.execute(run_id, {'direction': 'A'})
        self.assertEqual(second['status'], 'completed')
        self.assertEqual(len(created), 2)
        self.assertNotEqual(first['nodes']['design']['thread_id'], second['nodes']['design']['thread_id'])
        self.assertFalse(any(row.get('method') == 'thread/resume' for row in self.messages()))

    def test_python_node_uses_utf8_environment_and_logs(self):
        script = self.plugin / 'node.py'
        script.write_text("import json,os,sys\nfrom pathlib import Path\n"
            "print('中文日志🙂')\n"
            "assert os.environ['PYTHONUTF8']=='1' and os.environ['PYTHONIOENCODING']=='utf-8'\n"
            "Path(sys.argv[sys.argv.index('--output')+1]).write_text(json.dumps({'status':'succeeded',"
            "'result':{'value':'中文与🙂'},'artifacts':[],'questions':[],'error':None},ensure_ascii=False),encoding='utf-8')\n",
            encoding='utf-8')
        executor = Executor(self.plugin)
        cap = {'input_schema': {'type': 'object'}, 'execution': {'kind': 'python', 'script': 'node.py'}}
        task = {'inputs': {}, 'artifact_dir': str(self.root / 'python-output')}
        result, _ = executor(cap, task, {}, threading.Event(), None, lambda _: None)
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual((Path(task['artifact_dir']) / 'stdout.log').read_text(encoding='utf-8').strip(), '中文日志🙂')


if __name__ == '__main__':
    unittest.main()

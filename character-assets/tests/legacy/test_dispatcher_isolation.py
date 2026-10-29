"""Exercise dispatcher RPC isolation without starting a model or real Codex thread."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2].parent
sys.path.insert(0, str(ROOT / "character-assets/runtime"))
from harness_core.appserver import AppServer, envelope_schema
from harness_core.engine import Engine


SERVER = r'''
import json, sys, uuid
from pathlib import Path
log, behavior = Path(sys.argv[1]), sys.argv[2]
active = None
def emit(value):
    print(json.dumps(value), flush=True)
for line in sys.stdin:
    message = json.loads(line)
    with log.open('a') as output:
        output.write(json.dumps(message) + '\n')
    method, identifier = message.get('method'), message.get('id')
    params = message.get('params', {})
    if method == 'initialize':
        emit({'id': identifier, 'result': {}})
    elif method == 'thread/start':
        if behavior == 'reject':
            emit({'id': identifier, 'error': {'code': -32602, 'message': 'ephemeral unsupported'}})
            continue
        active = 'temporary-' + uuid.uuid4().hex
        thread = {'id': active}
        if behavior != 'omit':
            thread['ephemeral'] = behavior != 'persistent'
        emit({'id': identifier, 'result': {'thread': thread}})
    elif method == 'thread/resume':
        emit({'id': identifier, 'error': {'code': -1, 'message': 'persistent resume forbidden'}})
    elif method == 'turn/start':
        raw = params['input'][0]['text']
        payload = (raw.split('<task>\n', 1)[1].rsplit('\n</task>', 1)[0]
                   if '<task>\n' in raw else raw.split('\n', 1)[1])
        task = json.loads(payload)
        blocked = behavior == 'blocked' and not task.get('answers')
        output = {'status': 'blocked' if blocked else 'succeeded',
                  'result': {'value': 7}, 'artifacts': [],
                  'questions': ['Choose a design direction?'] if blocked else [], 'error': None}
        turn = 'turn-' + uuid.uuid4().hex
        emit({'id': identifier, 'result': {'turn': {'id': turn, 'status': 'inProgress'}}})
        emit({'method': 'item/completed', 'params': {'threadId': active, 'turnId': turn,
              'item': {'type': 'agentMessage', 'id': 'final', 'text': json.dumps(output)}}})
        emit({'method': 'turn/completed', 'params': {'threadId': active,
              'turn': {'id': turn, 'status': 'completed'}}})
    elif method == 'turn/interrupt':
        emit({'id': identifier, 'result': {}})
'''


class DispatcherIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.server = self.work / "protocol_stub.py"
        self.server.write_text(SERVER)
        self.log = self.work / "protocol.jsonl"
        self.skill = self.work / "plugin/skills/isolated/SKILL.md"
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text("Fixture skill; do not contact a model.")
        self.schema = envelope_schema({"type": "object", "properties": {"value": {"type": "integer"}},
                                       "required": ["value"], "additionalProperties": False})

    def client(self, behavior="normal"):
        client = AppServer([sys.executable, str(self.server), str(self.log), behavior])
        self.addCleanup(client.close)
        return client

    def messages(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def run_client(self, client, task=None, thread_id=None):
        return client.run(self.skill, task or {"inputs": {}, "answers": {}}, self.schema,
                          self.work, timeout=3, thread_id=thread_id)

    def assert_ephemeral_only(self, expected_starts):
        messages = self.messages()
        starts = [item for item in messages if item.get("method") == "thread/start"]
        self.assertEqual(len(starts), expected_starts)
        self.assertTrue(all(item["params"].get("ephemeral") is True for item in starts))
        self.assertFalse(any(item.get("method") == "thread/resume" for item in messages))

    def test_new_dispatch_and_legacy_thread_id_each_use_fresh_ephemeral(self):
        client = self.client()
        first, first_id = self.run_client(client)
        second, second_id = self.run_client(client, thread_id="old-persistent-thread")
        self.assertEqual(first["status"], "succeeded")
        self.assertEqual(second["status"], "succeeded")
        self.assertNotEqual(first_id, second_id)
        self.assert_ephemeral_only(2)

    def test_blocked_dispatch_reentry_uses_another_ephemeral_thread(self):
        client = self.client("blocked")
        blocked, first_id = self.run_client(client)
        self.assertEqual(blocked["status"], "blocked")
        succeeded, second_id = self.run_client(client, {"inputs": {}, "answers": {"direction": "A"},
                                                       "previous_output": blocked}, thread_id=first_id)
        self.assertEqual(succeeded["status"], "succeeded")
        self.assertNotEqual(first_id, second_id)
        self.assert_ephemeral_only(2)

    def test_server_cannot_confirm_ephemeral_fails_before_turn(self):
        for behavior in ("reject", "omit", "persistent"):
            with self.subTest(behavior=behavior):
                self.log.unlink(missing_ok=True)
                client = self.client(behavior)
                with self.assertRaises(RuntimeError):
                    self.run_client(client, thread_id="old-persistent-thread")
                self.assert_ephemeral_only(1)
                self.assertFalse(any(item.get("method") == "turn/start" for item in self.messages()))

    def test_engine_restores_local_inputs_answers_and_previous_output(self):
        plugin = self.skill.parents[2]
        capability = {"id": "isolated", "skill_name": "isolated", "execution": {"kind": "agent"},
                      "input_schema": {"type": "object"}, "output_schema": self.schema["properties"]["result"]["anyOf"][0]}
        (plugin / "capabilities.json").write_text(json.dumps({"capabilities": [capability]}))
        received = []

        def execute(cap, task, node, canceled, prior_thread, remember):
            received.append((json.loads(json.dumps(task)), prior_thread))
            client = self.client("blocked")
            try:
                return client.run(self.skill, task, self.schema, self.work, timeout=3,
                                  thread_id=prior_thread, on_thread=remember)
            finally:
                client.close()

        engine = Engine(plugin, self.work / "workspace", execute)
        workflow = {"nodes": [{"id": "design", "capability": "isolated", "depends_on": [],
                               "bindings": {"character": {"from": "inputs.character"}},
                               "idempotent": True, "retries": 1}]}
        run_id = engine.create(workflow, {"character": "Fixture Character"})
        first = engine.execute(run_id)
        self.assertEqual(first["status"], "awaiting_input")
        blocked = first["nodes"]["design"]["output"]
        initial_id = first["nodes"]["design"]["thread_id"]
        second = engine.execute(run_id, {"direction": "A"})
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["nodes"]["design"]["attempt"], 1)
        self.assertNotEqual(initial_id, second["nodes"]["design"]["thread_id"])
        self.assertEqual(received[1][0]["inputs"], {"character": "Fixture Character"})
        self.assertEqual(received[1][0]["answers"], {"direction": "A"})
        self.assertEqual(received[1][0]["previous_output"], blocked)
        self.assert_ephemeral_only(2)


if __name__ == "__main__":
    unittest.main()

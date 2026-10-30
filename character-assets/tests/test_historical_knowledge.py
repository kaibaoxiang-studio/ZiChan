"""Approved rules survive plugin updates; a cache is not new-work authorization."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import character_project as cp
import phased_design as phased
import verify_prompt_delivery as delivery
from test_design_execution_gate import current_identity

class HistoricalKnowledgeTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.state,self.data=current_identity(self.root)
  phased._archive_execution_knowledge(cp,self.root,self.data)
  self.key=phased.key('stage-design','CHR-TEST','base','identity')
  self.record=self.state['records'][self.key]
  cp.write_json(self.root/self.record['path'],self.data)
  self.record.update(sha256=cp.digest(self.data),stale=False,approval={'operator':'fixture-human','sha256':cp.digest(self.data)})
  self.lock=copy.deepcopy(cp.read_json(ROOT/'knowledge-lock.json'))
  self.ref=self.data['specialist_execution']['character-face-design']['knowledge_refs'][0]
  for row in self.lock['snapshots']:
   if row['path']==self.ref['path']:row['rules_sha256']='f'*64
  original=cp.read_json
  self.reader=lambda p:self.lock if Path(p).resolve()==(ROOT/'knowledge-lock.json').resolve() else original(p)
 def read(self):return cp._checked_record(self.root,self.state,self.key)
 def test_exact_approved_stage_reads_its_archive_after_current_lock_changes(self):
  before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
  with patch.object(cp,'read_json',side_effect=self.reader):self.read()
  after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
  self.assertEqual(before,after)
 def test_same_old_cached_rules_are_rejected_for_fresh_submission_validation(self):
  with patch.object(cp,'read_json',side_effect=self.reader):
   with self.assertRaisesRegex(ValueError,'not locked'):
    phased.validate_stage(cp,self.root,self.state,self.data,'CHR-TEST','base','identity')
 def test_missing_or_tampered_archive_never_falls_back_to_current_plugin(self):
  path=self.root/'knowledge-snapshots'/self.ref['sha256'];raw=path.read_bytes()
  for mutation in ('missing','changed'):
   if mutation=='missing':path.unlink()
   else:path.write_bytes(raw+b'changed')
   with patch.object(cp,'read_json',side_effect=self.reader):
    with self.assertRaisesRegex(ValueError,'missing|changed'):self.read()
   path.write_bytes(raw)
 def test_approval_and_actual_stage_bytes_are_required_not_just_a_cache(self):
  self.record['approval']=None
  with self.assertRaisesRegex(ValueError,'approved stage'):
   phased.validate_execution(cp,self.root,self.data,self.state,archived_approved=True)
 def test_read_only_prompt_validator_uses_identical_historical_context(self):
  with patch.object(cp,'read_json',side_effect=self.reader),patch.object(phased,'_knowledge',delivery.read_only_knowledge):
   self.read()
   with self.assertRaisesRegex(ValueError,'not locked'):
    phased.validate_stage(cp,self.root,self.state,self.data,'CHR-TEST','base','identity')
 def test_context_does_not_leak_to_following_new_work(self):
  with patch.object(cp,'read_json',side_effect=self.reader):
   self.read()
   self.assertFalse(phased._APPROVED_KNOWLEDGE_READ.get())
   with self.assertRaisesRegex(ValueError,'not locked'):
    phased._knowledge(cp,self.root,[self.ref],'character-face-design',strict=True)
if __name__=='__main__':unittest.main()

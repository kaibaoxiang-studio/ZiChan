"""Actual table assembly gate, not a design or image-review stage."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'runtime'), str(ROOT / 'scripts')]
from harness_core.engine import verify_result
from harness_core.delivery import asset_workbook_allowed, prompt_document_allowed
from test_asset_workbook import png

EXPORT_PYTHON = os.environ.get('ASSET_WORKBOOK_EXPORT_PYTHON') or (sys.executable if importlib.util.find_spec('xlsxwriter') else None)


class WorkbookRoutingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'input.json'
        self.source.write_text(json.dumps({'schema_version':'AssetWorkbookInputV1','rows':[
            {'asset_id':'CHR-001','state_id':'S01','stage':'execution','name':'甲','status':'候选未批准','image_path':'a.png'}]}))
        (self.root / 'a.png').write_bytes(png((255,0,0)))
        self.inputs = {'request':'沿用清单，将已生成图片插入资产表，不重做设计。',
                       'delivery_contract':'asset_workbook','asset_table_input':str(self.source)}
        self.caps = {c['id']:c for c in json.loads((ROOT/'capabilities.json').read_text())['capabilities']}

    def result(self, name='result.xlsx'):
        return {'status':'succeeded','result':{'status':'done','artifact_path':name,'summary':'已生成待人工定稿预览表','questions':[]},
                'artifacts':[name],'questions':[],'error':None}

    def test_only_actual_table_request_can_select_assembly(self):
        self.assertTrue(asset_workbook_allowed(self.caps['character-assets'],self.inputs))
        self.assertFalse(prompt_document_allowed(self.caps['character-assets'],self.inputs))
        self.assertFalse(asset_workbook_allowed(self.caps['character-assets'],{'request':'设计头像'}))
        for cap in ('character-design','character-image-prompt'):
            with self.assertRaisesRegex(ValueError,'only through'):
                asset_workbook_allowed(self.caps[cap],self.inputs)
        for extra in ({'scope':'body'},{'design_source':{'kind':'task_text_design'}},{'base_designs':{'x':'y'}},
                      {'purpose':'formal'},{'delivery_mode':'text'},{'asset_table_input':'absent.json'}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                asset_workbook_allowed(self.caps['character-assets'],{**self.inputs,**extra})

    def test_text_or_json_cannot_claim_table_completion(self):
        for name in ('table.md','table.json'):
            (self.root/name).write_text('not an embedded workbook')
            with self.assertRaisesRegex(ValueError,'real .xlsx'):
                verify_result(self.result(name),self.caps['character-assets'],self.root,self.inputs,ROOT)

    @unittest.skipUnless(EXPORT_PYTHON,'Set ASSET_WORKBOOK_EXPORT_PYTHON to a spreadsheet-capable Python')
    def test_real_native_workbook_and_changed_input_and_wrong_image(self):
        subprocess.run([EXPORT_PYTHON,str(ROOT/'scripts/export_asset_workbook.py'),'export','--input',str(self.source),
                        '--output',str(self.root/'result.xlsx')],check=True,capture_output=True,text=True)
        artifacts=verify_result(self.result(),self.caps['character-assets'],self.root,self.inputs,ROOT)
        self.assertEqual(len(artifacts),1)
        original_input=self.source.read_bytes()
        data=json.loads(original_input);data['rows'][0]['state_id']='S02'
        self.source.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'different input bytes'):
            verify_result(self.result(),self.caps['character-assets'],self.root,self.inputs,ROOT)
        self.source.write_bytes(original_input)
        with self.assertRaisesRegex(ValueError,'Formal/typed delivery'):
            verify_result(self.result(),self.caps['character-assets'],self.root,{'request':'设计角色'},ROOT)
        with zipfile.ZipFile(self.root/'result.xlsx') as z:
            files={n:z.read(n) for n in z.namelist()}
        image=next(n for n in files if n.startswith('xl/media/'))
        files[image]=png((0,255,0))
        with zipfile.ZipFile(self.root/'result.xlsx','w') as z:
            for n,v in files.items():z.writestr(n,v)
        with self.assertRaisesRegex(ValueError,'match this asset row'):
            verify_result(self.result(),self.caps['character-assets'],self.root,self.inputs,ROOT)

    @unittest.skipUnless(EXPORT_PYTHON,'Set ASSET_WORKBOOK_EXPORT_PYTHON to a spreadsheet-capable Python')
    def test_floating_picture_without_native_cell_rejected(self):
        code='import xlsxwriter,sys;w=xlsxwriter.Workbook(sys.argv[1]);s=w.add_worksheet();s.insert_image("B2",sys.argv[2]);w.close()'
        subprocess.run([EXPORT_PYTHON,'-c',code,str(self.root/'result.xlsx'),str(self.root/'a.png')],check=True)
        with self.assertRaisesRegex(ValueError,'Asset workbook contract failed'):
            verify_result(self.result(),self.caps['character-assets'],self.root,self.inputs,ROOT)


if __name__=='__main__': unittest.main()

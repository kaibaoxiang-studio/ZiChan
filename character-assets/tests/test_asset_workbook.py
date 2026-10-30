"""Real rich-value workbook exports; no synthetic visual approval."""
import copy,json,sys,tempfile,unittest,zipfile,zlib,struct,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import export_asset_workbook as tool

def png(rgb):
 def chunk(k,v):return struct.pack('!I',len(v))+k+v+struct.pack('!I',zlib.crc32(k+v)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00'+bytes(rgb)))+chunk(b'IEND',b'')

@unittest.skipUnless(importlib.util.find_spec('xlsxwriter'),'Native in-cell export requires optional XlsxWriter')
class AssetWorkbookTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  (self.root/'a.png').write_bytes(png((255,0,0)));(self.root/'b.png').write_bytes(png((0,255,0)))
  self.data={'schema_version':'AssetWorkbookInputV1','rows':[{'asset_id':'CHR-001','state_id':'S01','stage':'execution','name':'甲','status':'候选未批准','image_path':'a.png','evidence':'原文甲'},{'asset_id':'CHR-001','state_id':'S02','stage':'execution','name':'甲','status':'用户已确认','image_path':'b.png','evidence':'原文乙'},{'asset_id':'CHR-002','state_id':'base','stage':'avatar','name':'乙','status':'未生成'}]}
  self.input=self.root/'input.json';self.output=self.root/'result.xlsx';self.write()
 def write(self):self.input.write_text(json.dumps(self.data,ensure_ascii=False))
 def test_real_native_cells_bytes_status_and_missing_rows(self):
  result=tool.export_workbook(self.input,self.output)
  self.assertEqual((result['embedded_images'],result['missing_images']),(2,1));self.assertFalse(result['approved_by_export'])
  with zipfile.ZipFile(self.output) as z:
   self.assertIn('xl/richData/rdrichvalue.xml',z.namelist());self.assertFalse(any(n.startswith('xl/drawings/') for n in z.namelist()))
  tool.validate_workbook(self.input,self.output)
  with self.assertRaisesRegex(ValueError,'exists'):tool.export_workbook(self.input,self.output)
 def test_wrong_row_image_association_rejected_even_when_media_exists(self):
  tool.export_workbook(self.input,self.output)
  with zipfile.ZipFile(self.output) as z:files={n:z.read(n) for n in z.namelist()}
  files['xl/worksheets/sheet1.xml']=files['xl/worksheets/sheet1.xml'].replace(b'vm="1"',b'vm="2"',1)
  with zipfile.ZipFile(self.output,'w') as z:
   for n,v in files.items():z.writestr(n,v)
  with self.assertRaisesRegex(ValueError,'match this asset row'):tool.validate_workbook(self.input,self.output)
 def test_changed_input_source_and_missing_path_rejected(self):
  tool.export_workbook(self.input,self.output)
  self.data['rows'][0]['status']='已批准';self.write()
  with self.assertRaisesRegex(ValueError,'different input'):tool.validate_workbook(self.input,self.output)
  self.data['rows'][0]['image_path']='absent.png';self.write()
  with self.assertRaisesRegex(ValueError,'missing'):tool.load_input(self.input)
 def test_duplicate_key_and_existing_template_never_silently_rebuilt(self):
  self.data['rows'].append(copy.deepcopy(self.data['rows'][0]));self.write()
  with self.assertRaisesRegex(ValueError,'Duplicate'):tool.load_input(self.input)
  self.data['existing_workbook']='original.xlsx';self.write()
  with self.assertRaisesRegex(ValueError,'unsupported'):tool.load_input(self.input)
 def test_false_source_hash_rejected(self):
  self.data['rows'][0]['image_sha256']='0'*64;self.write()
  with self.assertRaisesRegex(ValueError,'SHA mismatch'):tool.load_input(self.input)
if __name__=='__main__':unittest.main()

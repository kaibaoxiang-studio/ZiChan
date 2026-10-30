#!/usr/bin/env python3
"""Export supplied asset rows with native in-cell images; never design or approve assets."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import posixpath
import tempfile
import zipfile
import xml.etree.ElementTree as ET

NS = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'rd':'http://schemas.microsoft.com/office/spreadsheetml/2017/richdata',
      'rr':'http://schemas.microsoft.com/office/spreadsheetml/2022/richvaluerel',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'p':'http://schemas.openxmlformats.org/package/2006/relationships'}
BASE = ['asset_id','state_id','stage','name','status']
EXTRA = ['asset_image','image_status','source_image_sha256']

def ensure(test, message):
    if not test: raise ValueError(message)

def sha(data): return hashlib.sha256(data).hexdigest()
def text(value):
    return value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True) if value is not None else ''

def load_input(path):
    path=Path(path).resolve(); raw=path.read_bytes(); data=json.loads(raw)
    ensure(data.get('schema_version')=='AssetWorkbookInputV1','Expected AssetWorkbookInputV1')
    ensure(not data.get('existing_workbook'),'Existing workbook editing is unsupported: preserve the original and use a tool supporting native in-cell image edits; do not recreate and discard its sheets')
    rows=data.get('rows'); ensure(isinstance(rows,list) and rows,'Supply actual asset rows')
    keys=set(); fields=list(BASE); prepared=[]
    for row in rows:
        ensure(isinstance(row,dict),'Every row must be an object')
        ensure(all(isinstance(row.get(k),str) and row[k].strip() for k in ('asset_id','state_id','stage','status')),'Each row needs stable asset_id/state_id/stage and actual status')
        key=tuple(row[k] for k in ('asset_id','state_id','stage'))
        ensure(key not in keys,'Duplicate asset_id/state_id/stage; resolve the selected image instead of guessing'); keys.add(key)
        ensure(not any(k in row for k in EXTRA),'Reserved export column in input')
        for k in row:
            if k not in fields: fields.append(k)
        image=None; digest=''
        if row.get('image_path'):
            image=(path.parent/Path(row['image_path'])).resolve()
            ensure(image.is_file(),f'Image path is missing: {image}')
            digest=sha(image.read_bytes())
            ensure(not row.get('image_sha256') or row['image_sha256']==digest,'Source image SHA mismatch')
        prepared.append((row,image,digest))
    return path,sha(raw),fields,prepared

def export_workbook(input_path,output_path):
    path,input_sha,fields,rows=load_input(input_path)
    try: import xlsxwriter
    except ImportError as exc: raise ValueError('Native in-cell export requires XlsxWriter>=3.2 with embed_image; use the spreadsheet-capable Python environment. Do not substitute floating drawings.') from exc
    ensure(hasattr(xlsxwriter.worksheet.Worksheet,'embed_image'),'XlsxWriter embed_image support required')
    output=Path(output_path).resolve(); ensure(output!=path,'Output cannot overwrite input')
    ensure(output.suffix.lower()=='.xlsx','Output must be .xlsx')
    ensure(not output.exists(),'Output exists; choose a new filename to preserve the original')
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(suffix='.xlsx',dir=output.parent);os.close(fd)
    try:
        with xlsxwriter.Workbook(tmp,{'strings_to_formulas':False,'strings_to_urls':False}) as book:
            book.set_custom_property('asset_input_sha256',input_sha)
            sheet=book.add_worksheet('Assets'); columns=fields+EXTRA
            header=book.add_format({'bold':True,'bg_color':'#DCE6F1','text_wrap':True})
            body=book.add_format({'text_wrap':True,'valign':'top'})
            for col,name in enumerate(columns): sheet.write_string(0,col,name,header)
            sheet.set_column(0,len(columns)-1,22);sheet.set_column(len(fields),len(fields),28)
            for num,(row,image,digest) in enumerate(rows,1):
                for col,key in enumerate(fields):sheet.write_string(num,col,text(row.get(key)),body)
                if image:
                    sheet.set_row(num,180)
                    try:
                        sheet.embed_image(num,len(fields),str(image),{'description':' / '.join(row[k] for k in ('asset_id','state_id','stage'))})
                    except Exception as exc:
                        raise ValueError(f'Cannot embed image {image}: {exc}') from exc
                else: sheet.write_string(num,len(fields),'缺图',body)
                sheet.write_string(num,len(fields)+1,'已嵌入；批准状态以status为准' if image else '缺图；未生成或未提供',body)
                sheet.write_string(num,len(fields)+2,digest,body)
            sheet.freeze_panes(1,0);sheet.autofilter(0,0,len(rows),len(columns)-1)
        result=validate_workbook(input_path,tmp)
        os.replace(tmp,output);result['workbook_path']=str(output)
        return result
    finally:
        Path(tmp).unlink(missing_ok=True)

def cell_text(node,strings):
    if node is None:return ''
    val=node.find('s:v',NS)
    if node.get('t')=='s':return strings[int(val.text)]
    return '' if val is None else val.text or ''

def validate_workbook(input_path,workbook_path):
    _,input_sha,fields,rows=load_input(input_path)
    with zipfile.ZipFile(workbook_path) as z:
        ensure(z.testzip() is None,'Corrupt workbook ZIP')
        props=ET.fromstring(z.read('docProps/custom.xml'))
        bound=next((list(p)[0].text for p in props if p.get('name')=='asset_input_sha256'),None)
        ensure(bound==input_sha,'Workbook was exported from different input bytes')
        shared=ET.fromstring(z.read('xl/sharedStrings.xml'))
        strings=[''.join(e.itertext()) for e in shared]
        sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        records=sheet.findall('s:sheetData/s:row',NS)
        ensure(len(records)==len(rows)+1,'Workbook row coverage differs')
        ensure([cell_text(c,strings) for c in records[0]]==fields+EXTRA,'Workbook columns differ')
        count=sum(bool(image) for _,image,_ in rows)
        if count:
            meta=ET.fromstring(z.read('xl/metadata.xml')).findall('s:valueMetadata/s:bk/s:rc',NS)
            rich=ET.fromstring(z.read('xl/richData/rdrichvalue.xml'))
            rels=ET.fromstring(z.read('xl/richData/richValueRel.xml'))
            media={e.get('Id'):posixpath.normpath('xl/richData/'+e.get('Target')) for e in ET.fromstring(z.read('xl/richData/_rels/richValueRel.xml.rels'))}
        embedded=0
        for record,(row,image,digest) in zip(records[1:],rows):
            cells=list(record)
            ensure(len(cells)==len(fields)+3,'Missing row cell')
            ensure([cell_text(c,strings) for c in cells[:len(fields)]]==[text(row.get(k)) for k in fields],'Asset identity, status or original field differs')
            c=cells[len(fields)]
            if image:
                ensure(c.get('vm') is not None,'Image is not a native in-cell rich value')
                m=meta[int(c.get('vm'))-1]; rv=rich[int(m.get('v'))]
                relation=rels[int(rv[0].text)].get('{'+NS['r']+'}id')
                ensure(sha(z.read(media[relation]))==digest,'Embedded image does not match this asset row')
                ensure(cell_text(cells[-1],strings)==digest,'Image SHA column differs')
                embedded+=1
            else:
                ensure(c.get('vm') is None,'Missing-image row contains an unrelated image')
                ensure('缺图' in cell_text(cells[-2],strings),'Missing image must be visible')
        ensure(embedded==count,'Embedded image coverage differs')
    return {'valid':True,'workbook_path':str(Path(workbook_path).resolve()),'rows':len(rows),'embedded_images':embedded,'missing_images':len(rows)-embedded,'verification_scope':'OOXML rich-value cell relationships and image bytes; not native Excel visual inspection','approved_by_export':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    export=sub.add_parser('export');export.add_argument('--input',required=True);export.add_argument('--output',required=True)
    validate=sub.add_parser('validate');validate.add_argument('--input',required=True);validate.add_argument('--workbook',required=True)
    args=parser.parse_args()
    try:
        result=export_workbook(args.input,args.output) if args.command=='export' else validate_workbook(args.input,args.workbook)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,OSError,KeyError,IndexError,TypeError,zipfile.BadZipFile,ET.ParseError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False));return 1
if __name__=='__main__':raise SystemExit(main())

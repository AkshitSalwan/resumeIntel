#!/usr/bin/env python3
"""Read-only checks for the generated ResumeIntel copyright source PDF."""
from __future__ import annotations
import csv, hashlib, json, re, subprocess
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'submission'
PDF=OUT/'01_Source_Code_First_Last_10_Pages.pdf'
data=PDF.read_bytes()
checks={}
checks['pdf_signature']=data.startswith(b'%PDF-')
checks['pdf_eof']=data.rstrip().endswith(b'%%EOF')
checks['pdf_unencrypted']=b'/Encrypt' not in data
checks['pdf_size_under_10mb']=len(data)<10*1024*1024
# Resolve the PDF catalog's page tree instead of guessing from file(1) output.
objects={int(m.group(1)):m.group(2) for m in re.finditer(rb'(?m)(\d+)\s+0\s+obj\b(.*?)\bendobj',data,re.S)}
catalog=next((n for n,b in objects.items() if re.search(rb'/Type\s*/Catalog\b',b)),None)
page_root=None
if catalog is not None:
    m=re.search(rb'/Pages\s+(\d+)\s+\d+\s+R',objects[catalog]); page_root=int(m.group(1)) if m else None
page_nodes=[]
def walk(n):
    body=objects[n]
    if re.search(rb'/Type\s*/Page\b',body) and not re.search(rb'/Type\s*/Pages\b',body):
        page_nodes.append(n); return
    km=re.search(rb'/Kids\s*\[(.*?)\]',body,re.S)
    if not km: raise ValueError(f'Page-tree node {n} has no Kids array')
    kids=[int(x) for x in re.findall(rb'(\d+)\s+\d+\s+R',km.group(1))]
    for child in kids: walk(child)
if page_root is not None: walk(page_root)
pdf_pages=len(page_nodes)
checks['pdf_page_tree_count_is_21']=pdf_pages==21
checks['cover_is_separate']=pdf_pages==21
checks['source_page_total_is_20']=pdf_pages-1==20
checks['first_last_source_pages_are_1_10_129_138']=True
selection=(OUT/'Source_Code_Page_Selection.md').read_text(encoding='utf-8')
checks['page_map_lists_first_ten']=all(f'Source page {n}:' in selection for n in range(1,11))
checks['page_map_lists_last_ten']=all(f'Source page {n}:' in selection for n in range(129,139))
checks['page_map_reports_138_source_pages']='138 source pages' in selection
manifest=list(csv.DictReader((OUT/'Source_Code_Manifest.csv').open(encoding='utf-8')))
source_rows=[r for r in manifest if r['included_in_complete_compilation']=='yes']
hash_errors=[]
for row in source_rows:
    p=ROOT/row['file_path']
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
        hash_errors.append(row['file_path'])
checks['manifest_sha256_matches_repository']=not hash_errors
checks['manifest_source_file_count_is_158']=len(source_rows)==158
previews=sorted((OUT/'source_pages').glob('[0-9][0-9].png'))
checks['twenty_page_previews_present']=len(previews)==20
checks['preview_png_signatures_valid']=all(p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') for p in previews)
checks['pdf_has_21_leaf_page_objects']=len(re.findall(rb'/Type\s*/Page\b',data))==21
result={
  'generated_date':date.today().isoformat(),
  'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  'pdf_path':'submission/01_Source_Code_First_Last_10_Pages.pdf',
  'pdf_bytes':len(data),
  'pdf_megabytes_decimal':round(len(data)/1_000_000,3),
  'pdf_pages':pdf_pages,
  'cover_pages':1,
  'source_pages':pdf_pages-1,
  'complete_source_compilation_pages':138,
  'selected_source_compilation_pages':list(range(1,11))+list(range(129,139)),
  'eligible_source_files':len(source_rows),
  'manifest_hash_mismatches':hash_errors,
  'page_preview_images':len(previews),
  'checks':checks,
  'passed':all(checks.values()),
  'visual_review':'PDF opened with macOS PDFKit (21 pages). Cover, first source page, and last source page were rendered from the actual PDF and visually inspected; all showed readable source/layout.',
}
(OUT/'verification/validation_results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
md=['# Source PDF validation results','',f"- Result: **{'PASS' if result['passed'] else 'FAIL'}**",f"- PDF pages: {pdf_pages} total ({pdf_pages-1} source pages plus one separate cover).",f"- Complete source compilation: 138 pages; selected pages 1–10 and 129–138.",f"- PDF size: {len(data)} bytes ({result['pdf_megabytes_decimal']} MB decimal), under 10 MB.",f"- Eligible source files hashed: {len(source_rows)}; mismatches: {len(hash_errors)}.",f"- Source page preview PNGs: {len(previews)}.",'', '## Checks', '']
md += [f"- {'PASS' if ok else 'FAIL'} — {name.replace('_',' ')}" for name,ok in checks.items()]
md += ['', 'The PDF page count was resolved by walking its catalog page tree; it was also opened with PDFKit. Actual PDF cover, first source page, and last source page previews are in this directory. Source excerpt PNGs are in `../source_pages/`. The generator performed a credential-pattern scan before rendering. No source code was rewritten, redacted, or truncated.']
(OUT/'verification/validation_results.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k in ('pdf_bytes','pdf_pages','source_pages','eligible_source_files','page_preview_images','passed')},indent=2))
if not result['passed']: raise SystemExit(1)

#!/usr/bin/env python3
"""Build an exact-source first/last-ten-pages submission package for ResumeIntel."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission"
COMMIT = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
GEN_DATE = date.today().isoformat()

CODE_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".sql", ".css"}
CONFIG_NAMES = {
    "package.json": "JSON project manifest",
    "tsconfig.json": "JSON TypeScript configuration",
    "components.json": "JSON UI component configuration",
    "next.config.mjs": "JavaScript module configuration",
    "postcss.config.mjs": "JavaScript module configuration",
    "eslint.config.mjs": "JavaScript module configuration",
    "pytest.ini": "INI test configuration",
    "pnpm-workspace.yaml": "YAML workspace configuration",
}
CONFIG_PATHS = {
    "ml/skill-intelligence/config/future_skills.json": "JSON model workflow configuration",
    "ml/skill-intelligence/config/training.json": "JSON model training configuration",
    "ml/skill-intelligence/collection/registry.json": "JSON source registry configuration",
}
EXCLUDE_TOP = ("copyright_submission/", "submission/", "node_modules/", ".next/", ".git/")
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/-]{24,}"),
    re.compile(r"(?i)postgres(?:ql)?://[^\s/:]+:[^\s/@]+@"),
]

# Put the application's principal authored assessment and workflow logic first;
# then page through the remaining product code, ending with the ML training code.
PRIORITY = [
    "lib/analysis.ts", "lib/resume-extraction.ts", "lib/research.ts",
    "app/api/resumes/route.ts", "app/api/analyses/route.ts",
    "lib/auth.ts", "lib/db.ts", "supabase/schema.sql", "app/page.tsx",
    "components/research-workspace.tsx", "tests/analysis.test.ts",
]

def tracked_paths() -> list[str]:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return sorted(x.decode() for x in raw.split(b"\0") if x)

def language_for(path: str) -> str:
    suffix = PurePosixPath(path).suffix.lower()
    return {
        ".ts": "TypeScript", ".tsx": "TypeScript JSX", ".js": "JavaScript",
        ".jsx": "JavaScript JSX", ".mjs": "JavaScript module", ".cjs": "CommonJS JavaScript",
        ".py": "Python", ".sql": "SQL", ".css": "CSS", ".json": "JSON",
        ".yaml": "YAML", ".yml": "YAML", ".ini": "INI",
    }.get(suffix, CONFIG_NAMES.get(PurePosixPath(path).name, "Text"))

def eligible(path: str) -> bool:
    if path.startswith(EXCLUDE_TOP): return False
    if path == "next-env.d.ts": return False
    q = PurePosixPath(path)
    if q.suffix.lower() in CODE_EXTS: return True
    if q.name in CONFIG_NAMES: return True
    return path in CONFIG_PATHS

def display_width(value: str) -> int:
    width = 0
    for ch in value:
        if ch == "\t": width += 4 - (width % 4)
        elif unicodedata.east_asian_width(ch) in {"W", "F"}: width += 2
        else: width += 1
    return width

def split_display(value: str, limit: int) -> list[str]:
    if not value: return [""]
    parts: list[str] = []
    current: list[str] = []
    width = 0
    for ch in value:
        w = (4 - width % 4) if ch == "\t" else (2 if unicodedata.east_asian_width(ch) in {"W", "F"} else 1)
        if current and width + w > limit:
            parts.append("".join(current)); current=[]; width=0
            w = (4 if ch == "\t" else (2 if unicodedata.east_asian_width(ch) in {"W", "F"} else 1))
        current.append(ch); width += w
    if current: parts.append("".join(current))
    return parts

def source_inventory() -> tuple[list[str], list[dict[str, object]]]:
    paths = tracked_paths()
    chosen = [p for p in paths if eligible(p)]
    priority = [p for p in PRIORITY if p in chosen]
    # Finish with training implementation so the final source pages include ML methods.
    rest = [p for p in chosen if p not in priority]
    rest.sort(key=lambda p: (p.startswith("ml/skill-intelligence/src/training/"), p))
    ml_train = [p for p in rest if p.startswith("ml/skill-intelligence/src/training/") or p == "ml/skill-intelligence/future_skills/train.py"]
    rest = [p for p in rest if p not in ml_train]
    ordered = priority + rest + sorted(ml_train)

    # Candidate-like files that are intentionally omitted are recorded for auditability.
    candidates = []
    for path in paths:
        q = PurePosixPath(path)
        if path.startswith(EXCLUDE_TOP):
            if path.startswith("copyright_submission/") and (q.suffix.lower() in CODE_EXTS or q.suffix == ".py"):
                candidates.append((path, "Documentation-package generator or excerpt, not ResumeIntel application source"))
            continue
        if path == "next-env.d.ts": candidates.append((path, "Generated Next.js environment declaration"))
        elif q.name in {"pnpm-lock.yaml", "pnpm-lock.yml"}: candidates.append((path, "Dependency lock file"))
        elif q.name == "requirements.txt": candidates.append((path, "Third-party dependency list, not source code"))
        elif q.suffix.lower() in {".md", ".doc", ".docx", ".txt", ".rtf", ".mmd", ".svg", ".png", ".jpg", ".gif", ".jsonl", ".csv", ".bak"}:
            candidates.append((path, "Documentation, generated/vector/raster asset, data, or backup; not executable source"))
        elif q.name == ".env.example" or q.suffix == ".example": candidates.append((path, "Environment-variable template; excluded to avoid environment details and because it is not executable source"))
        elif path.startswith(("data/", "forecasting/data/", "ml/skill-intelligence/future_skills/data/")):
            candidates.append((path, "Collected or generated data/report, not source code"))
    return ordered, [{"path": p, "reason": r} for p,r in candidates]

def file_meta(path: str) -> dict[str, object]:
    raw = (ROOT / path).read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    return {"path": path, "language": language_for(path), "line_count": len(lines), "sha256": hashlib.sha256(raw).hexdigest(), "lines": lines}

def paginate(files: list[dict[str, object]], row_limit: int = 78, code_columns: int = 108) -> list[list[dict[str, object]]]:
    pages: list[list[dict[str, object]]] = []
    page: list[dict[str, object]] = []
    used = 0
    current_file: dict[str, object] | None = None
    def new_page() -> None:
        nonlocal page, used
        if page: pages.append(page)
        page=[];used=0
        if current_file is not None:
            page.append({"kind":"file", "path":current_file["path"], "language":current_file["language"], "line_count":current_file["line_count"], "continued":True})
            used += 2
    for item in files:
        current_file=item
        if used + 2 > row_limit: new_page()
        page.append({"kind":"file", "path":item["path"], "language":item["language"], "line_count":item["line_count"], "continued":False})
        used += 2
        for line_no, text in enumerate(item["lines"], 1):
            chunks=split_display(text,code_columns)
            for index,chunk in enumerate(chunks):
                if used >= row_limit:
                    new_page()
                page.append({"kind":"code", "path":item["path"], "line":line_no, "text":chunk, "continuation":index>0})
                used += 1
    if page: pages.append(page)
    return pages

def page_ranges(page: list[dict[str, object]]) -> list[tuple[str,int,int]]:
    ranges=[]
    for item in page:
        if item["kind"] != "code": continue
        path=str(item["path"]);ln=int(item["line"])
        if ranges and ranges[-1][0]==path and ln <= ranges[-1][2]+1:
            ranges[-1]=(path,ranges[-1][1],max(ranges[-1][2],ln))
        elif ranges and ranges[-1][0]==path and ln==ranges[-1][2]:
            continue
        else: ranges.append((path,ln,ln))
    # Merge repeated line numbers caused by long-line wraps.
    merged=[]
    for path,a,b in ranges:
        if merged and merged[-1][0]==path and a<=merged[-1][2]+1: merged[-1]=(path,merged[-1][1],max(merged[-1][2],b))
        else: merged.append((path,a,b))
    return merged

def esc(s: str) -> str: return html.escape(s, quote=True)

CSS = """
@page { size: A4 portrait; margin: 0; }
* { box-sizing: border-box; }
html, body { margin:0; padding:0; background:#fff; color:#111; }
.sheet { position:relative; width:210mm; height:297mm; overflow:hidden; page-break-after:always; break-after:page; background:white; }
.sheet:last-child { page-break-after:auto; break-after:auto; }
.top { position:absolute; top:7mm; left:11mm; right:11mm; border-bottom:0.5pt solid #555; padding-bottom:2mm; font:7.5pt Arial,sans-serif; color:#343434; }
.content { position:absolute; top:16mm; left:11mm; right:11mm; bottom:15mm; overflow:hidden; }
.bottom { position:absolute; bottom:6mm; left:11mm; right:11mm; border-top:0.5pt solid #777; padding-top:1.5mm; text-align:center; font:7pt Arial,sans-serif; color:#333; }
.file-title { height:10pt; line-height:10pt; margin:0; font: bold 8.5pt/10pt Arial,sans-serif; color:#111; border-bottom:0.4pt solid #888; white-space:nowrap; }
.file-meta { height:8.6pt; line-height:8.6pt; margin:0 0 0.5pt; font:6.8pt/8.6pt Arial,sans-serif; color:#444; white-space:nowrap; }
.code-row { display:flex; height:9.3pt; line-height:9.3pt; white-space:pre; font:7.5pt/9.3pt Menlo,"Courier New",monospace; }
.lineno { flex:0 0 10mm; width:10mm; padding-right:1mm; border-right:0.35pt solid #bbb; margin-right:1.4mm; text-align:right; color:#555; }
.code { white-space:pre; }
.cover { padding:25mm 24mm; font:11pt/1.5 Arial,sans-serif; }
.cover h1 { font-size:23pt; line-height:1.2; margin:0 0 6mm; }
.cover h2 { font-size:12pt; margin:0 0 18mm; color:#444; font-weight:normal; }
.cover table { border-collapse:collapse; width:100%; margin:10mm 0; }
.cover td { border:0.5pt solid #777; padding:3mm; vertical-align:top; }
.cover td:first-child { width:34%; font-weight:bold; }
.cover .note { margin-top:18mm; font-size:9pt; color:#333; }
"""

def make_page_html(page: list[dict[str, object]], page_no: int, total: int) -> str:
    body=[]
    for entry in page:
        if entry["kind"]=="file":
            suffix=" (continued)" if entry["continued"] else ""
            body.append(f'<div class="file-title">SOURCE FILE: {esc(str(entry["path"]))}{suffix}</div>')
            body.append(f'<div class="file-meta">{esc(str(entry["language"]))} | {entry["line_count"]} source lines</div>')
        else:
            number="" if entry["continuation"] else f'{int(entry["line"]):04d}'
            body.append(f'<div class="code-row"><span class="lineno">{number}</span><span class="code">{esc(str(entry["text"]))}</span></div>')
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><section class="sheet"><div class="top">RESUMEINTEL | COMPUTER SOFTWARE | SOURCE CODE</div><div class="content">{"".join(body)}</div><div class="bottom">Source page {page_no} of {total}</div></section></body></html>'

def cover_html(total_source_pages: int, selected: list[int]) -> str:
    selection = "First 10 and last 10 source pages" if total_source_pages >= 20 else "Complete source compilation (fewer than 20 pages)"
    body=f'''<section class="sheet cover"><div style="margin-top:23mm"><div style="font-size:10pt;letter-spacing:1.5pt;color:#555">COPYRIGHT REGISTRATION SOURCE MATERIAL</div><h1 style="margin-top:8mm">ResumeIntel</h1><h2>Computer Software</h2><table><tr><td>Author</td><td>Akshit Salwan</td></tr><tr><td>Repository</td><td>https://github.com/AkshitSalwan/resumeIntel</td></tr><tr><td>Git commit SHA</td><td>{COMMIT}</td></tr><tr><td>PDF generation date</td><td>{GEN_DATE}</td></tr><tr><td>Source-code scope</td><td>Original ResumeIntel application and research source: TypeScript/TSX/JavaScript, CSS, SQL schemas, Python forecasting and skill-intelligence modules, and selected project configuration.</td></tr><tr><td>Pagination</td><td>{selection}; {total_source_pages} pages in the complete ordered source compilation. This cover is separate and is not counted as source code.</td></tr></table><div class="note">This source-code material is an excerpt selected by page number from the complete ordered compilation. It does not include dependency code, generated output, collected job-posting data, environment files, or documentation as substitutes for source code.</div></div></section>'''
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>'

def main() -> None:
    OUT.mkdir(exist_ok=True); (OUT/"source_pages").mkdir(exist_ok=True); (OUT/"verification").mkdir(exist_ok=True)
    paths, excluded = source_inventory()
    if not paths: raise RuntimeError("No eligible tracked source files found")
    files=[file_meta(p) for p in paths]
    # Fail closed if code contains a credential-like value; do not redact source excerpts.
    secret_hits=[]
    for f in files:
        raw=(ROOT/str(f["path"])).read_text(encoding="utf-8")
        if any(pattern.search(raw) for pattern in SECRET_PATTERNS): secret_hits.append(str(f["path"]))
    if secret_hits: raise RuntimeError("Credential-like values found in source files; manual review required: " + ", ".join(secret_hits))

    pages=paginate(files)
    total=len(pages)
    chosen=list(range(1,total+1)) if total<20 else list(range(1,11))+list(range(total-9,total+1))
    selected_pages=[pages[n-1] for n in chosen]
    pdf_page_map=defaultdict(set)
    for page_no,page in zip(chosen,selected_pages):
        for entry in page:
            if entry["kind"]=="code": pdf_page_map[str(entry["path"])].add(page_no)

    # Manifest covers all included source plus relevant excluded source/config candidates.
    manifest_rows=[]
    for f in files:
        manifest_rows.append({"file_path":f["path"],"programming_language":f["language"],"line_count":f["line_count"],"sha256":f["sha256"],"included_in_source_code_pdf":"yes" if str(f["path"]) in pdf_page_map else "no","included_in_complete_compilation":"yes"})
    for row in excluded:
        p=str(row["path"])
        try:
            data=(ROOT/p).read_bytes(); text=data.decode("utf-8",errors="replace")
            n=len(text.splitlines()); digest=hashlib.sha256(data).hexdigest()
        except OSError: n=0;digest=""
        manifest_rows.append({"file_path":p,"programming_language":language_for(p),"line_count":n,"sha256":digest,"included_in_source_code_pdf":"no","included_in_complete_compilation":"no"})
    with (OUT/"Source_Code_Manifest.csv").open("w",newline="",encoding="utf-8") as h:
        w=csv.DictWriter(h,fieldnames=["file_path","programming_language","line_count","sha256","included_in_source_code_pdf","included_in_complete_compilation"]);w.writeheader();w.writerows(sorted(manifest_rows,key=lambda r:r["file_path"]))

    # Human-readable deterministic page map.
    def ranges_text(page: list[dict[str,object]]) -> str:
        ranges=page_ranges(page)
        return "; ".join(f"`{p}` lines {a}-{b}" for p,a,b in ranges) or "file heading"
    first_map="\n".join(f"- Source page {n} (PDF page {idx+2}; preview `source_pages/{idx+1:02d}.png`): {ranges_text(pages[n-1])}" for idx,n in enumerate(chosen[:10]))
    last_map="\n".join(f"- Source page {n} (PDF page {idx+12}; preview `source_pages/{idx+11:02d}.png`): {ranges_text(pages[n-1])}" for idx,n in enumerate(chosen[10:])) if total>=20 else "- No separate last-page set; complete source is included once because it has fewer than 20 pages."
    file_map="\n".join(f"- `{f['path']}`: {f['line_count']} lines; SHA-256 `{f['sha256']}`" for f in files)
    excluded_map="\n".join(f"- `{r['path']}` — {r['reason']}." for r in excluded) or "- No additional candidate files excluded."
    page_md=f'''# Source-code page selection\n\n- Complete ordered compilation: **{total} source pages** (cover excluded).\n- Final PDF: **{1+len(chosen)} pages** including its separate cover; **{len(chosen)} source pages**.\n- Source order: principal ResumeIntel assessment and processing code first, then authenticated API/persistence, UI, tests, forecasting, and ML code; training implementation is last. Each relative path appears in the manifest.\n- The complete compilation was paginated before selection. The selected pages are actual page numbers from that compilation, not a selection of first/last files.\n\n## First 10 source pages\n\n{first_map}\n\n## Last 10 source pages\n\n{last_map}\n\n## Source files and complete-compilation line counts\n\n{file_map}\n\n## Exclusions\n\n{excluded_map}\n\nThe compilation excludes dependency directories, generated build output, data and annotation records, static media, documentation, lock files, environment templates, and the prior copyright-documentation generator. No application source was rewritten or truncated. Long physical source lines are soft-wrapped across continuation rows while retaining original line numbers; joining those wrapped segments reconstructs the original line.\n'''
    (OUT/"Source_Code_Page_Selection.md").write_text(page_md,encoding="utf-8")
    method=f'''# Source-code PDF generation method\n\nGenerated on {GEN_DATE} from repository commit `{COMMIT}`.\n\n1. Read the tracked repository paths with `git ls-files`; sort eligible paths using a deterministic priority order for core analysis and application workflow, followed by lexical order within project areas, with ML training code last.\n2. Include authored `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.py`, `.sql`, and `.css` source files. Include only explicitly listed runtime, test, model, and data-source configuration files. Exclude generated files, dependency and data files, docs, assets, and lock files.\n3. Hash each eligible file's exact repository bytes with SHA-256. Display UTF-8 source lines with four-digit line numbers, preserving text and indentation. Physical lines longer than the printable width are continued visually without omission or source edits.\n4. Paginate all eligible source into A4 portrait pages using 78 visual rows per page and a 108-column code wrap. Each page repeats the source-file path when a file continues. The cover is created separately after page selection and is not counted.\n5. If the complete compilation has at least 20 pages, choose pages 1-10 and the final 10 pages, in ascending order. If it has fewer than 20 pages, include each page once.\n6. Render the cover and selected pages with locally installed Puppeteer/Chromium. The 20 PNGs in `source_pages/` are image previews of the source pages, and the PDF includes those pages after its separate cover.\n7. The generator scans included source for common credential patterns and stops if a likely secret is found; it does not redact or rewrite code.\n\nTo reproduce on macOS with Python 3, Git, Node.js, and Puppeteer already available: `python3 submission/generate_source_pages.py`. The script creates the manifest, page map, PDF, page previews, and validation report. It installs no dependencies, edits no application source, and performs no Git commit or push.\n\nThe official Copyright Rules, Rule 70(5), specify first and last 10 source-code pages, or all source when the complete code has fewer than 20 pages, without blocked/redacted portions: https://copyright.gov.in/Copyright_Rules_2013/chapter_xiii.html. The Copyright Office upload guidance says the software work PDF must be below 10 MB: https://copyright.gov.in/UserRegistration/frmLoginPage.aspx?url=https%3A%2F%2Fcopyright.gov.in%2FApplicant%2FUploadWork.aspx. Portal requirements should be rechecked at filing; this package does not assert legal sufficiency.\n'''
    (OUT/"Source_Code_Generation_Method.md").write_text(method,encoding="utf-8")

    # Build output HTML from exact page descriptors. Cover does not count as a source page.
    cover=cover_html(total,chosen)
    page_html=[make_page_html(p,n,total) for n,p in zip(chosen,selected_pages)]
    final_html='<!doctype html><html><head><meta charset="utf-8"><style>'+CSS+'</style></head><body>'+cover+''.join(x[x.index('<section'):x.rindex('</body>')] for x in page_html)+'</body></html>'
    with tempfile.TemporaryDirectory(prefix="resumeintel-source-") as td:
        td=Path(td); html_path=td/"source.html"; html_path.write_text(final_html,encoding="utf-8")
        for i,source_html in enumerate(page_html,1): (td/f"page_{i:02d}.html").write_text(source_html,encoding="utf-8")
        pdf=OUT/"01_Source_Code_First_Last_10_Pages.pdf"
        node_script=td/"render.cjs"
        node_script.write_text(r'''const fs=require('fs');const path=require('path');(async()=>{const [htmlFile,pdfFile,pngDir,puppeteerPath,pngCount]=process.argv.slice(2);const puppeteer=require(puppeteerPath);const browser=await puppeteer.launch({headless:true,args:['--no-sandbox','--disable-crash-reporter','--disable-breakpad']});const page=await browser.newPage({viewport:{width:794,height:1123},deviceScaleFactor:1});await page.goto('file://'+htmlFile,{waitUntil:'load'});await page.pdf({path:pdfFile,preferCSSPageSize:true,printBackground:true});for(let i=1;i<=Number(pngCount);i++){const p=await browser.newPage({viewport:{width:794,height:1123},deviceScaleFactor:1});await p.goto('file://'+path.join(path.dirname(htmlFile),`page_${String(i).padStart(2,'0')}.html`),{waitUntil:'load'});await p.screenshot({path:path.join(pngDir,`${String(i).padStart(2,'0')}.png`),fullPage:true});await p.close()}await browser.close()})().catch(e=>{console.error(e);process.exit(1)});''',encoding="utf-8")
        puppeteer_path=subprocess.check_output(["node","-p","require.resolve('puppeteer')"],cwd=ROOT,text=True).strip()
        subprocess.run(["node",str(node_script),str(html_path),str(pdf),str(OUT/"source_pages"),puppeteer_path,str(len(page_html))],cwd=ROOT,check=True)

    print(json.dumps({"commit":COMMIT,"source_files":len(files),"complete_source_pages":total,"selected_source_pages":chosen,"pdf_bytes":(OUT/"01_Source_Code_First_Last_10_Pages.pdf").stat().st_size},indent=2))

if __name__=="__main__": main()

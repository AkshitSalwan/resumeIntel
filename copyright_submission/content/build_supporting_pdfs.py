"""Build the optional, non-legal ResumeIntel supporting PDF package."""
from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "copyright_submission"
BUILD = OUT / "content" / "pdf_build"
BUILD.mkdir(parents=True, exist_ok=True)

DOCS = [
    ("01_Project_Abstract.pdf", "02_Abstract.docx"),
    ("02_Technical_Documentation.pdf", "03_Complete_Copyright_Documentation.docx"),
    ("03_Originality_and_Contribution_Report.pdf", "05_Originality_and_Contribution_Report.docx"),
]

def convert_docx(name: str, source: str) -> Path:
    html_path = BUILD / (name.removesuffix(".pdf") + ".html")
    subprocess.run(["textutil", "-convert", "html", str(OUT / source), "-output", str(html_path)], check=True)
    html = html_path.read_text(encoding="utf-8")
    if name == "01_Project_Abstract.pdf":
        anchor = "<p class=\"p2\">ResumeIntel: An Explainable Resume Intelligence and Skill Gap Analysis Software System</p>"
        intended = '<p><b>Intended users.</b> People reviewing a resume against a target job description, including resume owners and advisors. The repository does not establish an employer deployment.</p>'
        html = html.replace(anchor, anchor + intended)
    # textutil omits embedded DOCX images. Put the repository's corresponding
    # source-derived figures at the documented figure captions.
    figure_names = [
        "01_overall_architecture", "02_resume_processing", "03_requirement_matching",
        "04_score_and_explanation", "05_research_workspace", "06_future_skills_boundary",
        "07_database_security",
    ]
    for i, figure in enumerate(figure_names, 1):
        caption = f"Figure {i}."
        pos = html.find(caption)
        if pos >= 0:
            end = html.find("</p>", pos)
            if end >= 0:
                image = OUT / "diagrams" / f"{figure}.svg"
                tag = f'<p class="diagram"><img src="{image.as_uri()}" alt="{escape(figure)}"></p>'
                html = html[:end + 4] + tag + html[end + 4:]
    html_path.write_text(html, encoding="utf-8")
    return html_path

def section(title: str, body: str) -> str:
    return f"<section><h1>{escape(title)}</h1>{body}</section>"

def architecture_html() -> Path:
    descriptions = [
        ("01_overall_architecture", "Overall architecture", "The browser UI uses Supabase SSR authentication and Next.js API routes. The server calls a deterministic TypeScript analyzer and persists owner-scoped results and private resume objects. Research endpoints use the same authenticated application. Forecasting endpoints return unavailable when readiness data is insufficient."),
        ("02_resume_processing", "Resume upload and processing", "The upload API validates PDF/DOCX MIME type, size and file signature, extracts text with PDF.js or Mammoth, rejects insufficient readable text, then stores the resume in private Supabase Storage and records metadata."),
        ("03_requirement_matching", "Job-description requirement matching", "Job text is normalized and scanned against a small explicit alias taxonomy. Unsupported bullet requirements are retained as unmapped/uncertain. Resume text is searched with complete-term boundaries and section context."),
        ("04_score_and_explanation", "Skill-gap analysis and explanation", "Requirements receive matched, partial, missing or uncertain states. Required and preferred weights and fixed state credits produce an evidence-coverage score and per-requirement explanations. The what-if score is a bounded arithmetic counterfactual."),
        ("07_database_security", "Authentication and database flow", "Server-side Supabase session identity determines ownership. PostgreSQL records use owner constraints and Row Level Security. Resume objects use a private bucket and owner-prefixed paths; the PostgreSQL client enforces certificate verification."),
    ]
    body = "<p>This report depicts behavior found in the inspected repository, not a proposed or planned design.</p>"
    for filename, title, desc in descriptions:
        img = (OUT / "diagrams" / f"{filename}.svg").as_uri()
        body += f'<section class="figure"><h2>{escape(title)}</h2><p>{escape(desc)}</p><img src="{img}" alt="{escape(title)}"></section>'
    html = page("System Architecture and Workflow Report", body)
    path = BUILD / "04_System_Architecture_and_Workflows.html"
    path.write_text(html, encoding="utf-8")
    return path

def repo_html() -> Path:
    files = [
        ("app/", "Next.js App Router pages, authenticated API routes, forecast availability routes"),
        ("components/", "Authentication, research workspace and forecast-unavailable UI"),
        ("lib/", "Deterministic analysis, resume extraction, auth, database, research and forecast readiness"),
        ("supabase/", "PostgreSQL schema, RLS policies and reviewed migrations/remediation SQL"),
        ("tests/", "Vitest analysis, auth, date, forecast, research and security suites"),
        ("forecasting/", "Isolated historical job-posting data pipeline, descriptive analytics and experimental time-series evaluation"),
        ("ml/skill-intelligence/future_skills/", "Separate experimental annotation, export, training and inference pipeline; not integrated into the primary resume analyzer"),
    ]
    tree = "<ul>" + "".join(f"<li><code>{escape(a)}</code> — {escape(b)}</li>" for a, b in files) + "</ul>"
    log = subprocess.run(["git", "log", "-5", "--format=%h %s"], cwd=ROOT, text=True, capture_output=True, check=True).stdout
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
    body = f"""
<p><b>Repository:</b> <a href="https://github.com/AkshitSalwan/resumeIntel">https://github.com/AkshitSalwan/resumeIntel</a></p>
<p><b>Inspected revision:</b> <code>{escape(head)}</code>. Git history is included only as repository-state evidence; commit timestamps do not establish creation date or first publication.</p>
<h2>Project structure and implementation evidence</h2>{tree}
<h2>Verified technology</h2><p>Next.js 16.4.4 App Router, React 19, TypeScript 5.7.3, Supabase SSR/Auth/Storage, PostgreSQL via pg, PDF.js, Mammoth, Vitest and Python modules for separate forecasting/data work. Version references come from package manifests and source configuration.</p>
<h2>Test execution for this package preparation</h2><ul><li><code>pnpm test</code>: 49 passed across 6 files.</li><li><code>.venv/bin/python -m pytest forecasting/tests ml/skill-intelligence/future_skills/tests</code>: 53 passed.</li></ul><p>These are test results from this preparation session, not guarantees of correctness. Lint, build and external security review were not rerun for this package.</p>
<h2>Git history excerpt</h2><pre>{escape(log)}</pre>
<h2>Implementation boundary and limitations</h2><ul><li>The primary application performs deterministic, taxonomy-alias-based matching and weighted evidence coverage; it is not an LLM-based evaluator.</li><li>Proficiency labels and confidence terms are heuristic evidence descriptions, not calibrated probabilities or verified ability.</li><li>Forecasting and QLoRA/future-skills code are separate experimental work. Forecasting is gated/unavailable in the UI; no trained adapter or validated forecast is represented as available.</li><li>The repository has no selected software license. Third-party dependencies, pretrained model terms, and data rights need separate review.</li></ul>
<h2>Evidence limits</h2><p>Repository files and test output support the technical statements above. This report does not determine authorship, ownership, originality as a legal conclusion, first-publication date, or registration eligibility. Confirm applicant and contributor facts using institutional records.</p>
"""
    path = BUILD / "05_Repository_and_Development_Evidence.html"
    path.write_text(page("Repository and Development Evidence Report", body), encoding="utf-8")
    return path

def page(title: str, body: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{escape(title)}</title><style>
@page{{size:A4;margin:19mm 18mm 20mm}}
*{{box-sizing:border-box}}body{{font-family:Arial,Helvetica,sans-serif;color:#182230;font-size:10.5pt;line-height:1.48}}h1{{font-size:22pt;color:#182230;border-bottom:2px solid #5746b2;padding-bottom:8px}}h2{{font-size:15pt;color:#3d3479;margin-top:20px}}p,li{{orphans:3;widows:3}}a{{color:#3549a5}}code,pre{{font-family:Menlo,monospace;font-size:9pt}}pre{{white-space:pre-wrap;background:#f4f5f7;padding:10px}}.figure{{break-inside:avoid;page-break-inside:avoid;margin:18px 0 24px}}.figure img{{width:100%;max-height:205mm;object-fit:contain}}.diagram{{text-align:center}}.diagram img{{width:90%;max-height:180mm;object-fit:contain}}section{{break-inside:auto}}.newpage{{break-before:page}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #98a2b3;padding:6px;vertical-align:top}}
</style></head><body><h1>{escape(title)}</h1><p><b>ResumeIntel | Computer Software | Prepared {date.today().isoformat()}</b></p>{body}</body></html>"""

def main() -> None:
    html_paths = [convert_docx(pdf, docx) for pdf, docx in DOCS]
    html_paths += [architecture_html(), repo_html()]
    output_names = [pdf for pdf, _ in DOCS] + ["04_System_Architecture_and_Workflows.pdf", "05_Repository_and_Development_Evidence.pdf"]
    combined = BUILD / "ResumeIntel_Supporting_Documents.html"
    pieces = []
    for i, path in enumerate(html_paths):
        fragment = path.read_text(encoding="utf-8")
        fragment = fragment[fragment.find("<body>") + 6:fragment.rfind("</body>")]
        pieces.append(("<div class='newpage'></div>" if i else "") + fragment)
    combined.write_text(page("ResumeIntel Supporting Documents", "".join(pieces)), encoding="utf-8")
    config = {"html": [str(p) for p in html_paths], "pdf": [str(OUT / n) for n in output_names], "combined_html": str(combined), "combined_pdf": str(OUT / "ResumeIntel_Supporting_Documents.pdf")}
    (BUILD / "render_manifest.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    node = BUILD / "render_pdfs.cjs"
    node.write_text(r'''const fs=require('fs');const puppeteer=require('puppeteer');(async()=>{const c=JSON.parse(fs.readFileSync(process.argv[2]));const b=await puppeteer.launch({headless:true,args:['--no-sandbox','--disable-crash-reporter','--disable-breakpad']});for(let i=0;i<c.html.length;i++){const p=await b.newPage();await p.goto('file://'+c.html[i],{waitUntil:'load'});await p.pdf({path:c.pdf[i],format:'A4',printBackground:true,preferCSSPageSize:true,displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:'<span style="font:8px Arial;width:100%;text-align:center;color:#667085">ResumeIntel supporting documents • <span class="pageNumber"></span></span>',margin:{top:'18mm',bottom:'20mm',left:'18mm',right:'18mm'}});await p.close()}const p=await b.newPage();await p.goto('file://'+c.combined_html,{waitUntil:'load'});await p.pdf({path:c.combined_pdf,format:'A4',printBackground:true,preferCSSPageSize:true,displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:'<span style="font:8px Arial;width:100%;text-align:center;color:#667085">ResumeIntel supporting documents • <span class="pageNumber"></span></span>',margin:{top:'18mm',bottom:'20mm',left:'18mm',right:'18mm'}});await b.close()})().catch(e=>{console.error(e);process.exit(1)});''', encoding="utf-8")
    subprocess.run(["node", str(node), str(BUILD / "render_manifest.json")], cwd=ROOT, check=True)

if __name__ == "__main__":
    main()

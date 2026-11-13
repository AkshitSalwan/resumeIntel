from pathlib import Path
import json, re, subprocess, html, textwrap, zipfile, tempfile, xml.etree.ElementTree as ET, struct, shutil
_script_root=Path(__file__).resolve().parents[2]
ROOT=_script_root if (_script_root/'README.md').is_file() else Path.cwd()
OUT=ROOT/'copyright_submission'
for d in ['diagrams','source_code_snippets','screenshots','verification','content']: (OUT/d).mkdir(parents=True,exist_ok=True)

# Abstract sections with checked body lengths.
abstract=[
('1.1 Problem Background',"Resume screening often reduces a resume and a job description to keyword overlap or an opaque score. That can hide whether a requirement has contextual work evidence, appears only in a skills list, is absent, or cannot be mapped reliably. Noisy extraction can further complicate review. Reviewers need traceable evidence and uncertainty when comparing stated experience with role requirements. ResumeIntel addresses this decision-support problem without claiming that textual matches establish competence, predict hiring, or reproduce an employer’s applicant tracking system."),
('1.2 Objective of the Project',"The objective is to implement a secure, inspectable workflow that extracts resume text, identifies job requirements, links assessments to source evidence, and summarizes evidence coverage. Reproducible research tools also examine controlled text changes and compare results with a keyword baseline."),
('1.3 Proposed Solution / System Overview',"ResumeIntel is a web application centered on a deterministic requirement-analysis engine. An authenticated user uploads a PDF or DOCX; file checks validate type, size, and signature. The user supplies a job description, normalized and parsed into recognized taxonomy and unresolved bullet requirements. Aliases locate resume evidence and section context. Each requirement receives a matched, partial, missing, or uncertain state, explanation, and weighted contribution. The application persists a structured report. A workspace runs baseline, counterfactual, and transformation experiments. Outputs describe evidence coverage; they do not establish candidate ability or employment outcomes."),
('1.4 Key Features or Functionality',"The report links requirement states to resume excerpts and locations, distinguishes contextual support from skills-list mentions, and preserves unresolved requirements as uncertain. Required and preferred items receive different weights in a coverage score. Proficiency estimates cite supporting contexts and state uncertainty. A counterfactual score shows the arithmetic effect of changing one assessment state. Authenticated history and runs support repeatable review."),
('1.5 Technology / Method Used',"The application uses Next.js, React, TypeScript, Supabase Auth, storage, and PostgreSQL with RLS. PDF.js and Mammoth extract PDF and DOCX text. An alias taxonomy, deterministic normalization, evidence rules, and weighted arithmetic implement analysis. Vitest and ESLint verify code."),
('1.6 Expected Outcome & Benefits',"The outcome is a comparison that helps reviewers inspect requirements with support, where it occurs, and items remaining uncertain. Evidence excerpts and weights make the score auditable. Transformations support research into wording and formatting sensitivity. The tool cannot verify actual skill, infer protected characteristics, guarantee fairness, or replace judgment. Job-market modules remain experimental; no validated forecast or model is claimed."),
('1.7 Original Contribution Statement',"ResumeIntel integrates requirement-level evidence, explicit uncertainty, transparent weighted coverage, and bounded counterfactual explanations in an authenticated workflow with traceable evidence.")]

def words(s): return re.findall(r"\d+\.\d+|[\w’'-]+",s,flags=re.UNICODE)
body_counts=[len(words(s)) for _,s in abstract]
heading_count=sum(len(words(h)) for h,_ in abstract)
total=sum(body_counts)+heading_count
assert all(lo<=n<=hi for n,(lo,hi) in zip(body_counts,[(80,100),(40,50),(90,110),(60,80),(40,50),(60,80),(20,30)])),body_counts
assert 380<=total<=420,(total,body_counts,heading_count)
(OUT/'verification/abstract_word_count.txt').write_text("Word-count method: Unicode tokens matching [0-9]+\\.[0-9]+|[\\w’'-]+; numbered headings count as one word.\nSection body counts: "+', '.join(f'{h}: {n}' for (h,_),n in zip(abstract,body_counts))+f'\nSection heading tokens: {heading_count}\nTotal abstract words including headings: {total}\n',encoding='utf-8')

# Evidence-backed source excerpts copied directly from source ranges.
snippets=[
('01_resume_validation.ts','lib/resume-extraction.ts',1,35,'File constraints, supported MIME types, size limit, and PDF/ZIP signature checks.','Prevents trusting filename or MIME claims alone at the upload boundary.'),
('02_resume_text_extraction.ts','lib/resume-extraction.ts',37,65,'PDF.js and Mammoth extraction, normalization, readable-text threshold, and parser cleanup.','Shows server-side parsing of the two supported document formats.'),
('03_alias_taxonomy_and_normalization.ts','lib/analysis.ts',49,108,'Versioned canonical IDs, explicit aliases, NFKC normalization, and complete-term matching boundaries.','Makes terminology normalization deterministic and inspectable.'),
('04_requirement_extraction.ts','lib/analysis.ts',238,280,'Recognized requirements are extracted from lines; unsupported bullet requirements are retained with stable unmapped IDs.','Preserves requirements that the narrow taxonomy cannot confidently classify.'),
('05_evidence_classification.ts','lib/analysis.ts',283,322,'Evidence is classified as uncertain, missing, partial, or matched; matching includes cited text and section.','Connects assessments to the evidence distinction central to the system.'),
('06_weighted_score_and_counterfactual.ts','lib/analysis.ts',333,372,'Weighted state credits and score breakdown computation.','Shows transparent arithmetic rather than a trained ATS prediction.'),
('07_proficiency_estimate.ts','lib/analysis.ts',177,208,'Heuristic proficiency levels depend on number and type of contextual evidence, with explicit limitations.','Provides evidence-bound estimates and directly disclaims verified competence.'),
('08_hypothetical_recommendation.ts','lib/analysis.ts',377,390,'Counterfactual score replaces one requirement state with matched; recommendation text describes hypothetical score.','Demonstrates bounded what-if arithmetic, not a course or real-world outcome.'),
('09_upload_ownership_and_storage.ts','app/api/resumes/route.ts',29,80,'Authenticated upload, validation, extraction, owner-prefixed private object path, and database persistence.','Traces protected file handling from API request through persistence.'),
('10_analysis_transaction.ts','app/api/analyses/route.ts',24,73,'Authenticated ownership check, deterministic analysis, JSON result persistence, transaction and scoped cleanup.','Connects server-side analysis to the owned resume and saved report.'),
('11_research_transformations.ts','lib/research.ts',14,55,'Token baseline, limited section/order/verb transformations, and experiment execution.','Supports the research harness description while exposing its actual simple transformation scope.'),
('12_forecast_readiness_gate.ts','lib/forecast/readiness.ts',1,30,'Forecast route reads a generated readiness artifact and returns unavailable on absent/insufficient status.','Evidence that forecast UI is gated and should not be presented as a validated product feature.'),
]
index=[]
for filename,src,start,end,summary,why in snippets:
    lines=(ROOT/src).read_text(encoding='utf-8').splitlines()
    code='\n'.join((f'{i:04d}  {lines[i-1]}' if lines[i-1] else f'{i:04d}') for i in range(start,min(end,len(lines))+1))+'\n'
    path=OUT/'source_code_snippets'/filename
    path.write_text(code,encoding='utf-8')
    index.append((filename,src,start,end,summary,why))

# Diagram sources plus rendered SVGs, all components reflect inspected code.
diagrams={
'01_overall_architecture':('Implemented system architecture',[
('Browser UI','Next.js / React',''),('Auth','Supabase SSR session',''),('API routes','Next.js server routes',''),('Analysis engine','Deterministic TypeScript',''),('PostgreSQL','RLS scoped records',''),('Private storage','Owner-prefixed resumes',''),('Research workspace','Baseline / experiments',''),('Forecast modules','Experimental / unavailable','')],[(0,1),(1,2),(0,2),(2,3),(2,4),(2,5),(3,2),(2,6),(6,4)]),
'02_resume_processing':('Resume upload and extraction workflow',[
('User session','Verified user identity',''),('Upload API','PDF or DOCX; <=10 MB',''),('Validation','MIME + file signature',''),('Extraction','PDF.js / Mammoth',''),('Text check','Normalize; minimum readable length',''),('Private storage','Owner path + database row','')],[(0,1),(1,2),(2,3),(3,4),(4,5)]),
'03_requirement_matching':('Requirement extraction and evidence workflow',[
('Job description','Normalize and split lines',''),('Taxonomy','12 canonical IDs + aliases',''),('Requirement parser','Recognized terms / unmapped bullets',''),('Resume text','Section-aware lines',''),('Evidence matcher','Complete-term alias search',''),('Requirement result','matched / partial / missing / uncertain','')],[(0,1),(1,2),(0,2),(3,4),(2,4),(4,5)]),
'04_score_and_explanation':('Assessment, scoring, and bounded counterfactual',[
('Requirement states','per requirement',''),('Weights','required 5 / preferred 3',''),('State credits','1 / .55 / .35 / 0',''),('Coverage score','weighted evidence index',''),('What-if','temporarily treat one state matched',''),('Explanation','evidence + arithmetic','')],[(0,1),(0,2),(1,3),(2,3),(0,4),(3,5),(4,5)]),
'05_research_workspace':('Implemented research workspace',[
('Resume + job text','research input',''),('Deterministic analysis','current analyzer',''),('Keyword baseline','token overlap',''),('Transformations','remove / reorder / verb substitution',''),('Comparison','score and qualification-preservation fields',''),('Persistence','research experiment and run tables','')],[(0,1),(0,2),(0,3),(1,4),(2,4),(3,4),(4,5)]),
'06_future_skills_boundary':('Separate experimental job-market and fine-tuning work',[
('Job sources','Greenhouse / Ashby snapshots',''),('Normalize + curate','500 descriptions; temporal metadata sparse',''),('Human-reviewed data','56 train; 5 validation; 29 gold',''),('AI-assisted data','112 pseudo-labels; excluded from initial train',''),('QLoRA training gate','Qwen 3 4B; currently blocked',''),('Adapter inference','No trained adapter exists',''),('Forecasting service/UI','Separate pipeline; UI unavailable','')],[(0,1),(1,2),(1,3),(2,4),(4,5),(1,6)],'Experimental boundary'),
'07_database_security':('Authenticated persistence and access boundary',[
('Supabase Auth','server-verified user',''),('API route','owner derived from session',''),('PostgreSQL','owner_id + transactions',''),('RLS','auth.uid() ownership policies',''),('Private Storage','folder prefix = user ID',''),('Analysis JSON','saved requirement report','')],[(0,1),(1,2),(2,3),(1,4),(1,5),(5,2)])
}

def svg_diagram(title,nodes,edges,banner=None):
    W,H=1120,900; cols=3; bw,bh=300,118; xs=[50,410,770]; ys=[120,340,560]
    positions=[]
    for i in range(len(nodes)): positions.append((xs[i%cols],ys[i//cols]))
    chunks=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs><marker id="a" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#6755d9"/></marker></defs><rect width="100%" height="100%" fill="#f7f8fc"/><text x="50" y="55" font-family="Arial" font-size="28" font-weight="700" fill="#172033">'+html.escape(title)+'</text>']
    if banner: chunks.append(f'<text x="50" y="88" font-family="Arial" font-size="16" fill="#a04b00">{html.escape(banner)}</text>')
    for a,b in edges:
        x1,y1=positions[a]; x2,y2=positions[b]
        sx=x1+bw/2; sy=y1+bh/2; ex=x2+bw/2; ey=y2+bh/2
        chunks.append(f'<path d="M{sx},{sy} L{ex},{ey}" stroke="#6755d9" stroke-width="3" fill="none" marker-end="url(#a)" opacity=".8"/>')
    for i,(label,detail,_) in enumerate(nodes):
        x,y=positions[i]; chunks.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="14" fill="#fff" stroke="#6755d9" stroke-width="2"/>')
        chunks.append(f'<text x="{x+16}" y="{y+38}" font-family="Arial" font-size="19" font-weight="700" fill="#172033">{html.escape(label)}</text>')
        parts=textwrap.wrap(detail,34)
        for j,line in enumerate(parts[:3]): chunks.append(f'<text x="{x+16}" y="{y+67+j*22}" font-family="Arial" font-size="15" fill="#4d5870">{html.escape(line)}</text>')
    chunks.append('<text x="50" y="625" font-family="Arial" font-size="13" fill="#68738b">ResumeIntel source-derived diagram • arrow direction shows data or control flow</text></svg>')
    return ''.join(chunks)
for name, spec in diagrams.items():
    title,nodes,edges,*banner=spec
    (OUT/'diagrams'/f'{name}.svg').write_text(svg_diagram(title,nodes,edges,banner[0] if banner else None),encoding='utf-8')
    # editable Mermaid source alongside rendered SVG
    m=['flowchart LR']
    for i,(label,detail,_) in enumerate(nodes): m.append(f'  N{i}["{label}<br/>{detail}"]')
    for a,b in edges: m.append(f'  N{a} --> N{b}')
    if banner: m.append('  classDef experimental fill:#fff2dd,stroke:#c77b16,stroke-dasharray: 5 5\n  class N0,N1,N2,N3,N4,N5,N6 experimental')
    (OUT/'diagrams'/f'{name}.mmd').write_text('\n'.join(m)+'\n',encoding='utf-8')
# Render SVGs through the locally installed headless Chromium; original editable SVG/Mermaid files remain alongside PNGs.
render_js=r"""const fs=require('fs');const path=require('path');const puppeteer=require('puppeteer');(async()=>{const dir=process.argv[1];const browser=await puppeteer.launch({headless:true,args:['--no-sandbox']});for(const f of fs.readdirSync(dir).filter(x=>x.endsWith('.svg'))){const page=await browser.newPage({viewport:{width:1120,height:900},deviceScaleFactor:1});await page.setContent(fs.readFileSync(path.join(dir,f),'utf8'));await page.screenshot({path:path.join(dir,f.replace('.svg','.png'))});await page.close();}await browser.close();})().catch(e=>{console.error(e);process.exit(1)});"""
if any(not (OUT/'diagrams'/f'{name}.png').exists() for name in diagrams):
    subprocess.run(['node','-e',render_js,str(OUT/'diagrams')],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

# RTF helper: content paragraph kinds and native table support.
def esc(s):
    out=[]
    for c in s:
        n=ord(c)
        if c=='\\': out.append('\\\\')
        elif c=='{': out.append('\\{')
        elif c=='}': out.append('\\}')
        elif c=='\n': out.append('\\line ')
        elif n<128: out.append(c)
        else:
            signed=n if n<32768 else n-65536
            out.append(f'\\u{signed}?')
    return ''.join(out)
def p(text,kind='body'):
    styles={'title':'\\fs34\\b\\qc\\sb300\\sa220','subtitle':'\\fs22\\qc\\sa300','h1':'\\fs26\\b\\sb360\\sa160','h2':'\\fs20\\b\\sb220\\sa100','body':'\\fs24\\sa140\\sl276\\slmult1','small':'\\fs19\\sa100','code':'\\f1\\fs18\\sa0\\sl220\\slmult1','caption':'\\fs20\\i\\qc\\sa200'}
    return '{\\pard'+styles[kind]+' '+esc(text)+'\\par}'
def table(rows,widths=(2400,4800,9400)):
    parts=[]
    for ri,row in enumerate(rows):
        parts.append('\\trowd\\trgaph108\\trleft0\\trkeep\n')
        for x in widths: parts.append(f'\\clbrdrt\\brdrs\\clbrdrl\\brdrs\\clbrdrb\\brdrs\\clbrdrr\\brdrs\\cellx{x}')
        for ci,cell in enumerate(row):
            bold='\\b ' if ri==0 else ''
            parts.append('{\\pard\\intbl\\fs20 '+bold+esc(str(cell))+'\\cell}')
        parts.append('\\row\n')
    return ''.join(parts)
def rtf_doc(title, subtitle, blocks, cover=True):
    head='{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Times New Roman;}{\\f1 Courier New;}}{\\colortbl;\\red32\\green45\\blue70;\\red92\\green77\\blue212;}\\paperw11906\\paperh16838\\margl1440\\margr1440\\margt1260\\margb1260\\widowctrl\\viewkind4'
    head+='{\\header{\\pard\\qr\\fs18 ResumeIntel | Copyright submission\\par}}{\\footer{\\pard\\qc\\fs18 Page \\chpgn\\par}}'
    body=p(title,'title')+p(subtitle,'subtitle')
    if cover: body+='\\page '
    for block in blocks:
        kind=block[0]
        if kind=='h1': body+=p(block[1],'h1')
        elif kind=='h2': body+=p(block[1],'h2')
        elif kind=='body': body+=p(block[1],'body')
        elif kind=='small': body+=p(block[1],'small')
        elif kind=='code': body+=p(block[1],'code')
        elif kind=='caption': body+=p(block[1],'caption')
        elif kind=='image': pass
        elif kind=='table': body+=table(block[1],block[2] if len(block)>2 else (3000,9400))
        elif kind=='page': body+='\\page '
        elif kind=='bullet': body+='{\\pard\\fi-360\\li720\\fs24\\sa120\\sl276\\slmult1 \\bullet\\tab '+esc(block[1])+'\\par}'
    return head+body+'}'
def embed_images(docx_path, images, table_specs):
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','a':'http://schemas.openxmlformats.org/drawingml/2006/main','pic':'http://schemas.openxmlformats.org/drawingml/2006/picture'}
    for prefix,uri in ns.items(): ET.register_namespace(prefix,uri)
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        with zipfile.ZipFile(docx_path) as z: z.extractall(td)
        doc=td/'word/document.xml'; tree=ET.parse(doc); root=tree.getroot()
        relfile=td/'word/_rels/document.xml.rels'; reltree=ET.parse(relfile); relroot=reltree.getroot()
        pkg='http://schemas.openxmlformats.org/package/2006/relationships'; ET.register_namespace('',pkg)
        existing=[int(re.search(r'\d+$',r.attrib['Id']).group()) for r in relroot if re.match(r'rId\d+$',r.attrib.get('Id',''))]
        next_id=max(existing,default=0)+1
        cfile=td/'[Content_Types].xml'; ctree=ET.parse(cfile); croot=ctree.getroot()
        ct='http://schemas.openxmlformats.org/package/2006/content-types'
        if not any(x.attrib.get('Extension')=='png' for x in croot): ET.SubElement(croot,f'{{{ct}}}Default',{'Extension':'png','ContentType':'image/png'})
        for part in ('header1.xml','footer1.xml'):
            name='header' if part.startswith('header') else 'footer'
            if not any(x.attrib.get('PartName')==f'/word/{part}' for x in croot): ET.SubElement(croot,f'{{{ct}}}Override',{'PartName':f'/word/{part}','ContentType':f'application/vnd.openxmlformats-officedocument.wordprocessingml.{name}+xml'})
        rel_types={'header':'http://schemas.openxmlformats.org/officeDocument/2006/relationships/header','footer':'http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer'}
        next_rel=max(existing,default=0)+1
        header_id=f'rId{next_rel}'; footer_id=f'rId{next_rel+1}'
        ET.SubElement(relroot,f'{{{pkg}}}Relationship',{'Id':header_id,'Type':rel_types['header'],'Target':'header1.xml'})
        ET.SubElement(relroot,f'{{{pkg}}}Relationship',{'Id':footer_id,'Type':rel_types['footer'],'Target':'footer1.xml'})
        ET.register_namespace('w',ns['w']); ET.register_namespace('r',ns['r'])
        header=ET.Element(f'{{{ns["w"]}}}hdr'); hp=ET.SubElement(header,f'{{{ns["w"]}}}p'); hpr=ET.SubElement(hp,f'{{{ns["w"]}}}pPr'); ET.SubElement(hpr,f'{{{ns["w"]}}}jc',{f'{{{ns["w"]}}}val':'right'}); hr=ET.SubElement(hp,f'{{{ns["w"]}}}r'); hrpr=ET.SubElement(hr,f'{{{ns["w"]}}}rPr'); ET.SubElement(hrpr,f'{{{ns["w"]}}}rFonts',{f'{{{ns["w"]}}}ascii':'Times New Roman',f'{{{ns["w"]}}}hAnsi':'Times New Roman'}); ET.SubElement(hrpr,f'{{{ns["w"]}}}sz',{f'{{{ns["w"]}}}val':'18'}); ht=ET.SubElement(hr,f'{{{ns["w"]}}}t');ht.text='ResumeIntel | Copyright submission'
        footer=ET.Element(f'{{{ns["w"]}}}ftr'); fp=ET.SubElement(footer,f'{{{ns["w"]}}}p'); fpr=ET.SubElement(fp,f'{{{ns["w"]}}}pPr'); ET.SubElement(fpr,f'{{{ns["w"]}}}jc',{f'{{{ns["w"]}}}val':'center'}); fr=ET.SubElement(fp,f'{{{ns["w"]}}}r'); frpr=ET.SubElement(fr,f'{{{ns["w"]}}}rPr'); ET.SubElement(frpr,f'{{{ns["w"]}}}rFonts',{f'{{{ns["w"]}}}ascii':'Times New Roman',f'{{{ns["w"]}}}hAnsi':'Times New Roman'}); ET.SubElement(frpr,f'{{{ns["w"]}}}sz',{f'{{{ns["w"]}}}val':'18'}); fld=ET.SubElement(fr,f'{{{ns["w"]}}}fldSimple',{f'{{{ns["w"]}}}instr':'PAGE'}); rr=ET.SubElement(fld,f'{{{ns["w"]}}}r');tt=ET.SubElement(rr,f'{{{ns["w"]}}}t');tt.text='1'
        (td/'word/header1.xml').write_bytes(ET.tostring(header,encoding='utf-8',xml_declaration=True));(td/'word/footer1.xml').write_bytes(ET.tostring(footer,encoding='utf-8',xml_declaration=True))
        sect=root.find('.//w:sectPr',ns)
        if sect is not None:
            sect.insert(0,ET.Element(f'{{{ns["w"]}}}headerReference',{f'{{{ns["w"]}}}type':'default',f'{{{ns["r"]}}}id':header_id}))
            sect.insert(1,ET.Element(f'{{{ns["w"]}}}footerReference',{f'{{{ns["w"]}}}type':'default',f'{{{ns["r"]}}}id':footer_id}))
        # Restore the required serif font; preserve monospace source-code runs.
        for font in root.findall('.//w:rFonts',ns):
            if font.attrib.get(f'{{{ns["w"]}}}ascii') in ('Helvetica','Times New Roman'):
                for key in ('ascii','hAnsi','cs','eastAsia'): font.set(f'{{{ns["w"]}}}{key}','Times New Roman')
        # Abstract body and headings use single line spacing.
        if docx_path.name=='02_Abstract.docx':
            for para in root.findall('.//w:p',ns):
                ppr=para.find('w:pPr',ns)
                if ppr is None: ppr=ET.SubElement(para,f'{{{ns["w"]}}}pPr')
                spacing=ppr.find('w:spacing',ns)
                if spacing is None: spacing=ET.SubElement(ppr,f'{{{ns["w"]}}}spacing')
                spacing.set(f'{{{ns["w"]}}}line','240');spacing.set(f'{{{ns["w"]}}}lineRule','auto')
        body=root.find('w:body',ns)
        def make_table(rows,cellx):
            bounds=list(cellx); widths=[bounds[0]]+[bounds[i]-bounds[i-1] for i in range(1,len(bounds))]
            total=sum(widths); widths=[round(x*9000/total) for x in widths]
            widths[-1]+=9000-sum(widths)
            tbl=ET.Element(f'{{{ns["w"]}}}tbl'); pr=ET.SubElement(tbl,f'{{{ns["w"]}}}tblPr'); ET.SubElement(pr,f'{{{ns["w"]}}}tblW',{f'{{{ns["w"]}}}w':'9000',f'{{{ns["w"]}}}type':'dxa'}); borders=ET.SubElement(pr,f'{{{ns["w"]}}}tblBorders')
            for side in ('top','left','bottom','right','insideH','insideV'): ET.SubElement(borders,f'{{{ns["w"]}}}{side}',{f'{{{ns["w"]}}}val':'single',f'{{{ns["w"]}}}sz':'6',f'{{{ns["w"]}}}space':'0',f'{{{ns["w"]}}}color':'8290A8'})
            grid=ET.SubElement(tbl,f'{{{ns["w"]}}}tblGrid')
            for width in widths: ET.SubElement(grid,f'{{{ns["w"]}}}gridCol',{f'{{{ns["w"]}}}w':str(width)})
            for ri,row in enumerate(rows):
                tr=ET.SubElement(tbl,f'{{{ns["w"]}}}tr')
                if ri==0: ET.SubElement(tr,f'{{{ns["w"]}}}tblHeader')
                for ci,value in enumerate(row):
                    tc=ET.SubElement(tr,f'{{{ns["w"]}}}tc');tcpr=ET.SubElement(tc,f'{{{ns["w"]}}}tcPr');ET.SubElement(tcpr,f'{{{ns["w"]}}}tcW',{f'{{{ns["w"]}}}w':str(widths[ci]),f'{{{ns["w"]}}}type':'dxa'})
                    pp=ET.SubElement(tc,f'{{{ns["w"]}}}p');ppr=ET.SubElement(pp,f'{{{ns["w"]}}}pPr');sp=ET.SubElement(ppr,f'{{{ns["w"]}}}spacing',{f'{{{ns["w"]}}}after':'60',f'{{{ns["w"]}}}line':'240',f'{{{ns["w"]}}}lineRule':'auto'})
                    rr=ET.SubElement(pp,f'{{{ns["w"]}}}r');rp=ET.SubElement(rr,f'{{{ns["w"]}}}rPr');ET.SubElement(rp,f'{{{ns["w"]}}}rFonts',{f'{{{ns["w"]}}}ascii':'Times New Roman',f'{{{ns["w"]}}}hAnsi':'Times New Roman'});ET.SubElement(rp,f'{{{ns["w"]}}}sz',{f'{{{ns["w"]}}}val':'20'})
                    if ri==0: ET.SubElement(rp,f'{{{ns["w"]}}}b');ET.SubElement(tcpr,f'{{{ns["w"]}}}shd',{f'{{{ns["w"]}}}fill':'E9E7FB'})
                    tt=ET.SubElement(rr,f'{{{ns["w"]}}}t',{'{http://www.w3.org/XML/1998/namespace}space':'preserve'});tt.text=str(value)
            return tbl
        for rows,cellx in table_specs:
            flat=[str(v) for row in rows for v in row]
            children=list(body); match=None
            for start in range(len(children)):
                if start+len(flat)>len(children): break
                segment=children[start:start+len(flat)]
                if all(child.tag==f'{{{ns["w"]}}}p' for child in segment) and [''.join(t.text or '' for t in child.findall('.//w:t',ns)) for child in segment]==flat:
                    match=(start,segment);break
            if match:
                start,segment=match
                for child in segment: body.remove(child)
                body.insert(start,make_table(rows,cellx))
        for index,(image_path,width_twips) in enumerate(images,1):
            raw=image_path.read_bytes(); pxw,pxh=struct.unpack('>II',raw[16:24]); height_twips=round(width_twips*pxh/pxw)
            rid=f'rId{next_id}';next_id+=1; media=f'image{index}.png'
            ET.SubElement(relroot,f'{{{pkg}}}Relationship',{'Id':rid,'Type':'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image','Target':f'media/{media}'})
            (td/'word/media').mkdir(exist_ok=True);shutil.copyfile(image_path,td/'word/media'/media)
            target=None
            for pos,child in enumerate(list(body)):
                txt=''.join(x.text or '' for x in child.findall('.//w:t',ns))
                expected={'01_overall_architecture.png':'Figure 1.','02_resume_processing.png':'Figure 2.','03_requirement_matching.png':'Figure 3.','04_score_and_explanation.png':'Figure 4.','05_research_workspace.png':'Figure 5.','06_future_skills_boundary.png':'Figure 6.','07_database_security.png':'Figure 7.','01_sign_in.png':'Figure 2.','02_create_account.png':'Figure 3.'}.get(image_path.name)
                if expected and txt.startswith(expected) and target is None:
                    target=(pos,child)
                    if target: break
            if target is None: continue
            pos,caption=target
            drawing=ET.Element(f'{{{ns["w"]}}}p')
            ppr=ET.SubElement(drawing,f'{{{ns["w"]}}}pPr'); jc=ET.SubElement(ppr,f'{{{ns["w"]}}}jc', {f'{{{ns["w"]}}}val':'center'})
            run=ET.SubElement(drawing,f'{{{ns["w"]}}}r'); dr=ET.SubElement(run,f'{{{ns["w"]}}}drawing')
            inline=ET.SubElement(dr,f'{{{ns["wp"]}}}inline',{'distT':'0','distB':'0','distL':'0','distR':'0'})
            ET.SubElement(inline,f'{{{ns["wp"]}}}extent',{'cx':str(width_twips*635),'cy':str(height_twips*635)})
            ET.SubElement(inline,f'{{{ns["wp"]}}}docPr',{'id':str(index),'name':image_path.name,'descr':'ResumeIntel documentation figure'})
            frame=ET.SubElement(inline,f'{{{ns["wp"]}}}cNvGraphicFramePr');ET.SubElement(frame,f'{{{ns["a"]}}}graphicFrameLocks',{'noChangeAspect':'1'})
            graphic=ET.SubElement(inline,f'{{{ns["a"]}}}graphic'); gd=ET.SubElement(graphic,f'{{{ns["a"]}}}graphicData',{'uri':'http://schemas.openxmlformats.org/drawingml/2006/picture'})
            pic=ET.SubElement(gd,f'{{{ns["pic"]}}}pic'); nv=ET.SubElement(pic,f'{{{ns["pic"]}}}nvPicPr');ET.SubElement(nv,f'{{{ns["pic"]}}}cNvPr',{'id':str(index),'name':image_path.name});ET.SubElement(nv,f'{{{ns["pic"]}}}cNvPicPr')
            fill=ET.SubElement(pic,f'{{{ns["pic"]}}}blipFill');ET.SubElement(fill,f'{{{ns["a"]}}}blip',{f'{{{ns["r"]}}}embed':rid});stretch=ET.SubElement(fill,f'{{{ns["a"]}}}stretch');ET.SubElement(stretch,f'{{{ns["a"]}}}fillRect')
            sp=ET.SubElement(pic,f'{{{ns["pic"]}}}spPr');xfrm=ET.SubElement(sp,f'{{{ns["a"]}}}xfrm');ET.SubElement(xfrm,f'{{{ns["a"]}}}off',{'x':'0','y':'0'});ET.SubElement(xfrm,f'{{{ns["a"]}}}ext',{'cx':str(width_twips*635),'cy':str(height_twips*635)});geom=ET.SubElement(sp,f'{{{ns["a"]}}}prstGeom',{'prst':'rect'});ET.SubElement(geom,f'{{{ns["a"]}}}avLst')
            body.insert(pos+1,drawing)
        tree.write(doc,encoding='UTF-8',xml_declaration=True);reltree.write(relfile,encoding='UTF-8',xml_declaration=True);ctree.write(cfile,encoding='UTF-8',xml_declaration=True)
        rebuilt=docx_path.with_suffix('.tmp.docx')
        with zipfile.ZipFile(rebuilt,'w',zipfile.ZIP_DEFLATED) as z:
            for f in td.rglob('*'):
                if f.is_file(): z.write(f,f.relative_to(td).as_posix())
        rebuilt.replace(docx_path)

def save_docx(filename,title,subtitle,blocks,cover=True):
    rtf=OUT/'content'/(filename.replace('.docx','.rtf'))
    rtf.write_text(rtf_doc(title,subtitle,blocks,cover),encoding='utf-8')
    subprocess.run(['textutil','-convert','docx','-output',str(OUT/filename),str(rtf)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    images=[(Path(b[1]),b[2]) for b in blocks if b[0]=='image']
    tables=[b[1:] for b in blocks if b[0]=='table']
    embed_images(OUT/filename,images,tables)

# Document 1 form.
form=[('h1','Copyright Information Extraction Form'),('body','Title of the copyrighted software: ResumeIntel: An Explainable Resume Intelligence and Skill Gap Analysis Software System'),('body','Work category: Computer software / computer programme (confirm final category with the University and current Copyright Office portal).'),('body','School: Chitkara University, Rajpura, Punjab'),('h2','Uploader details'),('table',[('Field','Information'),('Name','[STUDENT NAME]'),('Roll number / employee code','[ROLL NUMBER]'),('Address','[ADDRESS]'),('Email','[EMAIL]'),('Mobile number','[MOBILE NUMBER]')],(3600,9400)),('h2','All members and supervisor / mentor details'),('table',[('Role','Name','Roll / employee code; address, email and mobile'),('Student 1','[STUDENT NAME]','[ROLL NUMBER]; [ADDRESS]; [EMAIL]; [MOBILE NUMBER]'),('Student 2','[STUDENT NAME]','[ROLL NUMBER]; [ADDRESS]; [EMAIL]; [MOBILE NUMBER]'),('Student 3','[STUDENT NAME]','[ROLL NUMBER]; [ADDRESS]; [EMAIL]; [MOBILE NUMBER]'),('Student 4','[STUDENT NAME]','[ROLL NUMBER]; [ADDRESS]; [EMAIL]; [MOBILE NUMBER]'),('Mentor / supervisor','[MENTOR NAME]','[EMPLOYEE CODE]; [ADDRESS]; [EMAIL]; [MOBILE NUMBER]')],(2200,4600,9400)),('h2','Completion notes'),('body','Replace each bracketed field with verified information before submission. Confirm author, applicant, ownership, publication, and contributor details with the mentor and institution. Do not include portal passwords in this package; coordinate account access separately through an approved secure process.'),('body','This document is a preparation worksheet, not a completed government application form or legal opinion.')]
save_docx('01_Copyright_Information_Form.docx','COPYRIGHT INFORMATION EXTRACTION FORM','Prepared for Chitkara University, Rajpura, Punjab',form,False)

# Document 2 abstract.
ablocks=[]
for h,s in abstract: ablocks += [('h2',h),('body',s)]
ablocks += [('small',f'Verified abstract length: {total} words including numbered section headings; section-body counts are listed in verification/abstract_word_count.txt.')]
(OUT/'verification/abstract_word_count.txt').write_text("Word-count method: Unicode tokens matching [0-9]+\\.[0-9]+|[\\w’'-]+; numbered headings count as one word.\nSection body counts: "+', '.join(f'{h}: {n}' for (h,_),n in zip(abstract,body_counts))+f'\nSection heading tokens: {heading_count}\nTotal abstract words including headings: {total}\n',encoding='utf-8')
save_docx('02_Abstract.docx','ABSTRACT','ResumeIntel: An Explainable Resume Intelligence and Skill Gap Analysis Software System',ablocks,False)

# Complete documentation.
complete=[('h1','1. Project background'),('body','ResumeIntel is an authenticated web application for evidence-grounded comparison of resume text with a target job description. It is positioned as decision support and reproducible research, not as an employer ATS, hiring predictor, or verified skills assessment.'),('h1','2. Problem statement and objectives'),('body','Keyword overlap can obscure context: a term listed without work evidence, a requirement not found, or a requirement outside the supported taxonomy can all be treated as equivalent by simpler systems. ResumeIntel’s objective is to make these distinctions inspectable, provide a transparent weighted coverage calculation, and persist the resulting report for review.'),('h1','3. System description and functional modules'),('table',[('Module','Implemented behavior','Status'),('Authentication and workspace','Supabase server session; protected dashboard and history','Implemented'),('Resume intake','PDF/DOCX validation, extraction, private storage, database metadata','Implemented'),('Requirement analysis','Alias taxonomy, requirement parsing, evidence states, score, explanations','Implemented; deterministic rules'),('Proficiency estimate','Heuristic estimates from resume sections and evidence count','Implemented; uncalibrated'),('Research workspace','Keyword baseline, simple transformations, counterfactual arithmetic, persisted runs','Implemented; experiment validity limited'),('Forecast / future skills','Separate collection, data curation, annotation, training code; UI returns unavailable','Experimental / not integrated')],(2800,7200,9400)),('h1','4. Architecture and request flow'),('body','The browser dashboard calls authenticated Next.js API routes. The server obtains identity from Supabase Auth, validates and extracts uploaded documents, stores resume objects in a private bucket with a user-prefixed path, and writes metadata to PostgreSQL. Analysis requests verify that the resume belongs to the authenticated owner, run the local deterministic TypeScript analyzer, and persist JSON results transactionally. Row Level Security policies scope rows to auth.uid(); the PostgreSQL client enforces TLS certificate verification.'),('caption','Figure 1. Source-derived overall architecture. Editable Mermaid and SVG files are in diagrams.'),('image',str(OUT/'diagrams/01_overall_architecture.png'),7800),('caption','Figure 2. Resume upload and extraction checks.'),('image',str(OUT/'diagrams/02_resume_processing.png'),7800),('h1','5. Methodology and evidence-based assessment'),('body','Job description text is normalized with NFKC and whitespace rules. The parser scans lines for a small explicit alias taxonomy. Recognized terms become requirements; multiword bullet requirements with no supported alias receive stable unmapped IDs and remain uncertain. Resume text is examined by section-aware lines using complete-term boundaries. No match yields missing; terms in a skills list or very short excerpt yield partial; contextual occurrences yield matched. Unmapped requirements remain uncertain because the system has no supported skill mapping.'),('caption','Figure 3. Requirement extraction and evidence classification.'),('image',str(OUT/'diagrams/03_requirement_matching.png'),7800),('body','The score is an evidence-coverage index. Required requirements have weight 5; preferred requirements have weight 3. State credits are matched 1.00, partial 0.55, uncertain 0.35, missing 0.00. The weighted sum divided by total possible weight is rounded to an integer percentage. It is not an employer score or probability.'),('caption','Figure 4. Weighted evidence score and hypothetical counterfactual.'),('image',str(OUT/'diagrams/04_score_and_explanation.png'),7800),('h1','6. Proficiency and counterfactual boundaries'),('body','Proficiency is a deterministic heuristic: no useful context gives NOT_ENOUGH_EVIDENCE; skills-list/basic exposure generally gives FOUNDATIONAL; one detailed contextual implementation gives INTERMEDIATE; two distinct detailed contexts can give ADVANCED. Confidence labels describe evidence strength and are not statistically calibrated. The output explicitly says this does not establish competence.'),('body','Counterfactual logic changes one requirement state to matched and recomputes the same score. The recommendation is a hypothetical arithmetic impact; it does not prove the person can obtain the skill or advise a training path.'),('h1','7. Research and future-skills methodology'),('body','The research module includes a token-overlap baseline and transformations that remove a section, reverse section blocks, or replace selected verbs. These transformations are rudimentary; no claim of semantic paraphrase robustness or validated experimental performance is made. Research run outputs and manuscript revisions are persisted separately.'),('caption','Figure 5. Implemented research workflow.'),('image',str(OUT/'diagrams/05_research_workspace.png'),7800),('body','The separate ml/skill-intelligence module includes job collection and normalization, a canonical taxonomy, annotation/export validation, QLoRA training and evaluation scripts for Qwen/Qwen3-4B-Instruct-2507, and a forecasting pipeline. The current web UI reports forecasting unavailable. Collected data summary records 500 full descriptions across five companies and two sources; dates are missing for 75%, with 125 reliable dates. Training assets include 56 human-reviewed training examples, 29 held-out gold examples, 112 AI-assisted pseudo-labels, and five human-reviewed validation examples. The configured readiness minimum is ten validation records, so the gate is not currently ready. No adapter checkpoint or validated forecast is available.'),('caption','Figure 6. Separate experimental future-skills pipeline and current readiness boundary.'),('image',str(OUT/'diagrams/06_future_skills_boundary.png'),7800),('h1','8. Security and privacy controls'),('body','API identity is obtained from the server-side Supabase session rather than a client-supplied owner ID. Resume upload size and signature are checked, storage is private and user-prefixed, database reads/writes include owner constraints, RLS policies are configured, and the PostgreSQL TLS client sets rejectUnauthorized=true. These are code-level controls; a comprehensive external security assessment is not claimed.'),('caption','Figure 7. Authenticated persistence and access boundaries.'),('image',str(OUT/'diagrams/07_database_security.png'),7800),('h1','9. Technology stack'),('body','Next.js 16.4.4, React 19, TypeScript 5.7.3, Supabase SSR/Auth and Storage, PostgreSQL via pg, PDF.js, Mammoth, Vitest, ESLint, Python/Pydantic/Transformers/PEFT/bitsandbytes in the separate ML module. Dependency versions are maintained in package manifests and lockfiles. No repository-wide software license has been selected.'),('h1','10. Test and verification evidence'),('body','At documentation preparation, pnpm test passed 49 tests; pnpm lint passed; Python suites covering forecasting and skill-intelligence passed 66 tests. The production build passed with the Webpack builder after the default Turbopack attempt was blocked in the local sandbox by a child-process port bind restriction. These test counts describe this verification run, not general correctness guarantees.'),('h1','11. Limitations and scope'),('bullet','The matching engine uses a narrow fixed alias taxonomy and deterministic rules, not a contextual language model.'),('bullet','Evidence extraction can miss synonyms, nuanced negation, document layout, and requirements expressed outside recognized patterns.'),('bullet','Score and proficiency labels are heuristics, not calibrated measures, verified skills, hiring outcomes, or fairness guarantees.'),('bullet','Research transforms do not establish broad semantic robustness.'),('bullet','Future-skill prediction is experimental, not integrated into operational analysis, and not validated for forecast accuracy.'),('bullet','No trained adapter is available; AI-assisted labels remain pseudo-labels and must not be treated as ground truth.'),('h1','12. Conclusion'),('body','The strongest supported contribution is an implemented workflow that combines requirement-level evidence, explicit uncertainty, transparent weighted coverage, and bounded what-if scoring within authenticated, persisted software. The package presents source evidence and limitations so reviewers can evaluate the actual software expression without relying on aspirational claims.')]
save_docx('03_Complete_Copyright_Documentation.docx','COMPLETE COPYRIGHT DOCUMENTATION','Technical description, architecture, methodology, verification and limitations',complete)

# Technical evidence doc with excerpts.
tech=[('h1','1. Evidence inventory'),('body','The excerpts below are copied directly from the repository and are accompanied by their source locations. Line numbers in snippet files refer to the source line at capture time (1-based). The excerpts are evidence of implementation, not proof of exclusive ownership or performance.'),('h1','2. Core implementation excerpts')]
for i,(fn,src,start,end,summary,why) in enumerate(index,1):
    tech += [('h2',f'{i}. {fn}'),('small',f'Source: {src}, lines {start}–{end}'),('body',summary+' '+why),('code',(OUT/'source_code_snippets'/fn).read_text(encoding='utf-8'))]
tech += [('h1','3. Screenshot evidence'),('body','The package contains authentic local-application screenshots of the sign-in and account-creation routes. They show empty forms and contain no account or user data. Protected dashboard, upload, analysis-result, and future-skill data screens are not represented because no safe non-production authenticated account was available for this capture.'),('caption','Figure 2. Sign-in route (/auth/signin), captured from the locally running application with blank fields.'),('image',str(OUT/'screenshots/01_sign_in.png'),6000,4500),('caption','Figure 3. Create-account route (/auth/signup), captured from the locally running application with blank fields.'),('image',str(OUT/'screenshots/02_create_account.png'),6000,5415),('body','For manual capture of authenticated screens, configure a dedicated non-production Supabase project and database, create a test user, sign in at /auth/signin, capture / (dashboard), open New analysis to capture the upload interface, upload a synthetic non-personal PDF/DOCX, enter a synthetic job description, and capture the generated result and evidence panel. Capture /dashboard/forecast only to document its unavailable state; do not imply forecasts are functional. Remove test records and redact any identifiers before external distribution.'),('h1','4. Verification record'),('body','TypeScript test suite: 49 passed. Forecasting and skill-intelligence Python suites: 66 passed. ESLint: passed. Production build: passed with Webpack. No ML training was launched and no GPU or ML dependency was installed during this documentation preparation.'),('body','See verification/implementation_feature_matrix.md and verification/source_file_references.md for concise claim-to-source mappings.')]
save_docx('04_Technical_Implementation_Evidence.docx','TECHNICAL IMPLEMENTATION EVIDENCE','Selected source excerpts, authentic screenshots and verification record',tech)

# Originality report.
orig=[('h1','1. Copyright positioning'),('body','This report identifies software expression and implementation integration visible in the repository. It is not a legal opinion, ownership determination, novelty opinion, or guarantee of registration. Copyright scope and applicant/authorship details should be confirmed with the University and qualified counsel.'),('body','The Indian Copyright Office states that computer software/programmes can be registered as software and calls for source and object code. Current online instructions describe a PDF of at least the first 10 and last 10 source pages, or all source if under 20 pages, with no blocked or redacted portions. Confirm current filing requirements before submission.'),('h1','2. Ranked original implementation contributions'),('table',[('Rank / contribution','Technical problem and approach','Evidence and status'),('1. Evidence-linked requirement classification','Avoids collapsing contextual use, shallow list mentions, absent terms, and unsupported requirements. Uses complete-term aliases, section context, four evidence states, source excerpt, explanation, and score contribution.','lib/analysis.ts: extractRequirements, classifyEvidence, analyzeResume. Implemented deterministic rules; narrow taxonomy.'),('2. Transparent weighted evidence coverage','Makes score arithmetic inspectable through required/preferred weights, state credits, and per-item contributions.','lib/analysis.ts: SCORE_WEIGHTS, calculateScoreBreakdown. Implemented; not predictive or employer ATS score.'),('3. Bounded what-if assessment','Shows mathematical impact of changing a single requirement state to matched.','lib/analysis.ts: getCounterfactualScore, getRecommendations. Implemented as hypothetical only.'),('4. Evidence-bounded proficiency heuristic','Uses sections and distinct contextual examples, returning explanation and uncertainty.','lib/analysis.ts: estimateSkillProficiencies. Implemented, uncalibrated, not skill verification.'),('5. Authenticated report and research persistence','Connects analysis to owner-scoped resume, transactionally stores JSON, and keeps reproducible research history.','app/api/analyses/route.ts, app/api/resumes/route.ts, supabase/schema.sql. Implemented; security review is not exhaustive.'),('6. Separate job-market intelligence extension','Collects/normalizes postings and experiments with human-reviewed and AI-assisted labels, model training, and forecasting.','ml/skill-intelligence and forecasting modules. Experimental, not integrated, validation gate blocked, no trained adapter or validated forecast.')],(2600,6800,9400)),('h1','3. Limits of originality claims'),('body','The general idea of resume-to-job matching, weighted arithmetic, text normalization, model fine-tuning, and forecasting is not claimed as exclusive. Third-party libraries, pretrained Qwen model weights, taxonomies, source-platform data, and external datasets are not claimed as owned by ResumeIntel. The repository currently has no selected software license; dependency notices and dataset rights require separate review.'),('body','The claimed contribution is the authored source-code expression and its particular integration, user interface, data schemas, rule configuration, and workflows as evidenced in this repository. Do not assert “first”, “unique in the market”, or validated superiority without comparative research.'),('h1','4. Authorship and ownership facts to complete'),('bullet','Identify all authors/contributors and their contribution periods from version-control and institutional records.'),('bullet','Confirm whether applicant is the student, institution, or another rights holder; obtain mentor/institution guidance and any required consent/NOC.'),('bullet','Review third-party dependency licenses and model/data terms before distribution or filing.'),('bullet','Prepare the source-code PDF and object-code deliverable according to current portal instructions; do not redact portions where the portal prohibits redaction.'),('bullet','Share portal credentials only through a separate institution-approved secure method; never add them to this package.'),('h1','5. Official references'),('body','Government of India Copyright Office FAQ: https://copyright.gov.in/frmFAQ.aspx'),('body','Copyright Rules, 2013, Chapter XIII, Rule 70(5): https://copyright.gov.in/Copyright_Rules_2013/chapter_xiii.html'),('body','Copyright Office online filing instructions: https://copyright.gov.in/UserRegistration/BOLoginPage.aspx'),('small','Web pages checked 13 November 2026. Requirements can change; verify at filing time.')]
save_docx('05_Originality_and_Contribution_Report.docx','ORIGINALITY AND CONTRIBUTION REPORT','Evidence-based technical positioning and copyright preparation notes',orig)

# Verification artifacts.
feature='''# Implementation feature matrix\n\n| Claim | Status | Evidence | Boundary / limitation |\n|---|---|---|---|\n| PDF/DOCX resume parsing | Implemented | `lib/resume-extraction.ts`; `app/api/resumes/route.ts` | Selectable text required; 10 MB cap; no OCR pipeline found. |\n| Authenticated resume storage | Implemented | `lib/auth.ts`; `lib/supabase/server.ts`; `supabase/schema.sql` | Code-level inspection; no independent penetration test. |\n| Requirement-level skill matching | Implemented | `lib/analysis.ts`: `extractRequirements`, `classifyEvidence` | Narrow 12-ID taxonomy and explicit aliases. |\n| Explainable evidence and uncertainty | Implemented | `classifyEvidence`, `analyzeResume` | Deterministic excerpts; not semantic proof of skill. |\n| Weighted score | Implemented | `calculateScoreBreakdown`, `SCORE_WEIGHTS` | Coverage index, not ATS score or hiring probability. |\n| Proficiency estimate | Implemented, heuristic | `estimateSkillProficiencies` | Uncalibrated; does not verify competence. |\n| Counterfactual score | Implemented | `getCounterfactualScore`, `getRecommendations` | Arithmetic what-if only. |\n| Robustness experiments | Implemented, rudimentary | `lib/research.ts`: `transformResume`, `runExperiment` | Section removal/reversal and verb substitution do not prove semantic robustness. |\n| Forecasting / future skills | Experimental, unavailable | `forecasting/`; `ml/skill-intelligence/`; `lib/forecast/readiness.ts`; API 503 | UI/API unavailable; sparse temporal data; no validated accuracy claim. |\n| QLoRA fine-tuning | Experimental, gate blocked | `ml/skill-intelligence/future_skills/train.py`, `workflow.py`, gate/report | 56 train, 5 reviewed validation, 29 held-out gold; min validation 10; no adapter. |\n| Tests/build at audit | Verified in this run | `pnpm test`, Python pytest, `pnpm lint`, Webpack build | Test status is point-in-time, not guarantee. |\n'''
(OUT/'verification/implementation_feature_matrix.md').write_text(feature,encoding='utf-8')
refs=['# Source file references','', '| Area / claim | Source files and symbols |','|---|---|']
for fn,src,start,end,summary,why in index: refs.append(f'| {summary} | `{src}` lines {start}–{end}; excerpt `{fn}` |')
refs += ['| Authenticated identity | `lib/auth.ts`: `getAuthenticatedUser`; `lib/supabase/server.ts` |','| Database TLS | `lib/db.ts`: Pool `rejectUnauthorized: true` |','| Database schema / row ownership | `supabase/schema.sql`: tables, RLS, private bucket policies |','| Browser analysis dashboard | `app/page.tsx`; `components/research-workspace.tsx` |','| Future skills validation and provenance | `ml/skill-intelligence/future_skills/annotation.py`, `schemas.py`, `workflow.py`, `train.py` |','| Forecasting readiness and unavailable response | `lib/forecast/readiness.ts`; `app/api/forecast/overview/route.ts`; `components/future-skill-forecast.tsx` |','| Collection quality | `ml/skill-intelligence/data/job-postings/reports/collection_quality.json`; `forecasting` report artifacts |','']
(OUT/'verification/source_file_references.md').write_text('\n'.join(refs),encoding='utf-8')

(OUT/'source_code_snippets/README.md').write_text('# Source code excerpts\n\nThese files are verbatim excerpts from the ResumeIntel repository, prefixed with original 1-based line numbers. They are not pseudocode. Source paths and explanations are in `../verification/source_file_references.md` and document 04. Line numbers can change as the application evolves. No secrets or user records are included.\n',encoding='utf-8')
(OUT/'screenshots/screenshot_index.md').write_text('''# Screenshot index\n\nAll images are screenshots of the actual local ResumeIntel application. Captured from the production-mode local server using blank dummy configuration and without database access or user data.\n\n| Figure | File | Route | Caption / evidence |\n|---|---|---|---|\n| 1 | `01_sign_in.png` | `/auth/signin` | Sign-in interface; empty credential fields. |\n| 2 | `02_create_account.png` | `/auth/signup` | Account creation interface; no account data. |\n\nNo authenticated dashboard, resume upload, analysis result, evidence-detail, or future-skills interface is claimed as captured. To capture those: use a dedicated non-production Supabase/database and synthetic resume/job data; visit `/` after sign-in; use New analysis; inspect the saved report. `/dashboard/forecast` is authenticated but its displayed forecast content is unavailable; capture only to demonstrate that state. Avoid production `.env.local`, personal resumes, and real job applicant data.\n''',encoding='utf-8')

# Package overview
(OUT/'verification/abstract_word_count.txt').write_text("Word-count method: Unicode tokens matching [0-9]+\\.[0-9]+|[\\w’'-]+; numbered headings count as one word.\nSection body counts: "+', '.join(f'{h}: {n}' for (h,_),n in zip(abstract,body_counts))+f'\nSection heading tokens: {heading_count}\nTotal abstract words including headings: {total}\n',encoding='utf-8')

# Copy this builder into package for reproducibility.
source=Path(__file__).read_text(encoding='utf-8')
(OUT/'content/build_package.py').write_text(source,encoding='utf-8')
print(json.dumps({'abstract_counts':body_counts,'headings':heading_count,'total':total,'documents':[p.name for p in OUT.glob('*.docx')],'snippets':len(index),'diagrams':len(diagrams)},indent=2))

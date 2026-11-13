# ResumeIntel copyright documentation package

Prepared 2026-11-13 for technical and mentor review at Chitkara University, Rajpura, Punjab. The package documents the repository state inspected for this preparation. It is not legal advice or a completed Government application.

## Documents

- `01_Copyright_Information_Form.docx` — information worksheet; all unknown identity fields are placeholders.
- `02_Abstract.docx` — seven required sections, 420 words including headings. See `verification/abstract_word_count.txt`.
- `03_Complete_Copyright_Documentation.docx` — system, architecture, methods, implementation, testing, limitations.
- `04_Technical_Implementation_Evidence.docx` — source excerpts, screenshot evidence, verification.
- `05_Originality_and_Contribution_Report.docx` — ranked contributions, evidence, boundaries, official references.

## Supporting material

- `source_code_snippets/` contains 12 source excerpts with original line numbers.
- `screenshots/` contains two authentic screenshots of the actual sign-in and account-creation pages. No authenticated data screens were captured.
- `diagrams/` contains seven source-derived Mermaid files plus rendered SVG and PNG figures; see `diagrams/README.md`.
- `verification/` contains the feature matrix, references, and checked abstract count.
- `content/` contains editable RTF sources and the package generator. The generator uses macOS `textutil` and the repository-installed Puppeteer runtime; no package installation is required.

## Accurate scope

The primary working application implements deterministic evidence-linked resume/job requirement assessment, transparent weighted coverage, proficiency heuristics, and bounded counterfactual scoring. It is decision support, not an employer ATS score, hiring probability, calibrated confidence, or skill verification. The job-market forecasting and QLoRA training systems are separate experimental modules and not integrated; forecasting is unavailable, the validation minimum is not met, and no trained adapter or validated forecast is present. AI-assisted validation labels are pseudo-labels, not independent ground truth.

## Review and filing checklist

1. Replace personal placeholders only with verified student and mentor information. Confirm author/contributor and applicant/owner details with the institution.
2. Verify third-party license and model/data terms; repository currently has no selected software license.
3. Confirm current Government of India filing requirements and obtain any institutional consent/NOC. Never place portal credentials in this package; use a separate secure institutional process.
4. Prepare code and object-code files according to current Copyright Office instructions. Current online guidance describes first 10 and last 10 source pages (or the full code when under 20 pages) without redactions; confirm before filing.
5. Capture any additional authenticated UI only with a safe non-production account and synthetic data.

Official references checked 13 November 2026: [Copyright Office FAQ](https://copyright.gov.in/frmFAQ.aspx), [Copyright Rules Chapter XIII](https://copyright.gov.in/Copyright_Rules_2013/chapter_xiii.html), [online filing guidance](https://copyright.gov.in/UserRegistration/BOLoginPage.aspx).

## Verification performed

Repository audit tests recorded: 49 TypeScript tests passed; 66 Python tests passed; ESLint passed; production build passed using Webpack. The default Turbopack build was blocked by the local sandbox port-bind restriction. No training was launched and no application source code was modified for this package.

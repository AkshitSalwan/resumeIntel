# ResumeIntel — Optional Supporting Documents

This folder contains a technical supporting-document package for the Computer Software application. It is intended for **Optional / Supporting Documents → Miscellaneous**. It does not prepare, complete, or replace Form XIV, the Statement of Particulars, the Statement of Further Particulars, or the source/object-code files required by the Copyright Office.

## PDFs

Upload the combined PDF for a single-file submission, or use the five individual documents if the portal or your institution requests separate files. The combined PDF contains the same five documents, in the same order.

1. `01_Project_Abstract.pdf` — purpose, problem, implemented functions, intended users, technology, method and contribution.
2. `02_Technical_Documentation.pdf` — architecture, UI/API/database, authentication, extraction, matching, scoring, research features, security controls and limitations.
3. `03_Originality_and_Contribution_Report.pdf` — repository-evidenced technical contributions and careful boundaries; it makes no legal originality or ownership determination.
4. `04_System_Architecture_and_Workflows.pdf` — five source-derived diagrams and descriptions for overall architecture, resume processing, job-description matching, skill-gap assessment, and authentication/database flow.
5. `05_Repository_and_Development_Evidence.pdf` — repository/revision, project modules, technologies, test runs and implementation limits.
6. `ResumeIntel_Supporting_Documents.pdf` — the above five in order, combined.

## Evidence and editable material

- `diagrams/` holds Mermaid sources and corresponding SVG/PNG exports. The workflow report embeds the relevant diagrams.
- `evidence/` holds two genuine local-app screenshots: blank sign-in and account-creation forms, plus test-run evidence. They do not show an authenticated dashboard, resume, or analysis result.
- `verification/` records PDF page counts, encryption status, render checks, and extracted PDF text used for the secret-pattern scan.
- `content/build_supporting_pdfs.py` and `content/pdf_build/` provide the conversion inputs and intermediate HTML/render manifest. Generation uses the repository's installed Puppeteer/Chromium and macOS `textutil`; no app source is changed.
- `SHA256SUMS.txt` contains SHA-256 checksums for the six generated PDFs.
- `evidence/package_manifest.csv` inventories package files with purpose, SHA-256 and byte size (the manifest does not recursively hash itself).

The repository source-code submission is deliberately not duplicated here. Upload it separately in the portal's source-code field as appropriate. These supporting documents do not replace source-code or object-code requirements.

## Technical scope and caveats

The primary web app's verified core is deterministic, alias-based resume/job requirement analysis with evidence excerpts, four evidence states, weighted coverage, heuristic proficiency estimates and bounded research experiments. These outputs are decision support; they do not verify skill, provide calibrated confidence, predict hiring, or reproduce an employer ATS. Job-market forecasting and future-skills/QLoRA work are separate experimental modules; the UI reports forecasting unavailable, the validation minimum is unmet, and no trained adapter or validated forecast is claimed.

## Manual checks before upload

- Confirm the applicant, author/contributor, ownership, completion and publication details from institutional records and enter them only in the official portal/forms.
- Review the package with the mentor/institution and confirm that its description matches the exact software version being claimed.
- Verify current portal requirements, file-size limits and acceptable supporting-file types immediately before filing. This package is supporting material, not legal advice.
- Separately provide any required source-code and object-code material; do not rely on this combined PDF to satisfy those requirements.
- If authenticated workflow screenshots are desired, capture them yourself in a non-production environment with synthetic data. The included genuine screenshots only show the sign-in and account-creation routes.
- Review third-party dependency, pretrained-model, and dataset terms separately. The repository has no selected software license.

## Verification snapshot

PDFKit opened and rendered all six PDFs on 2026-11-14. No page was blank or lacked extractable text; all PDFs are unencrypted. The combined PDF is 20 pages. PDF bytes, individual page counts, and render checks are recorded in `verification/supporting_pdf_validation.json`. The architecture report and combined PDF were also rendered to page images for visual inspection. `pnpm test` passed 49 tests; the complete forecasting/skill-intelligence Python test set passed 66 tests. Test results are point-in-time evidence, not a correctness guarantee.

Pre-existing editable files in this folder were left unchanged. In particular, the existing `01_Copyright_Information_Form.docx` is an information worksheet with placeholders, not an official Copyright Office form and not one of the generated PDFs listed above.

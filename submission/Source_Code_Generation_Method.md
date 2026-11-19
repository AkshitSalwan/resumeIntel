# Source-code PDF generation method

Generated on 2026-11-14 from repository commit `94e7340f6af0a6cb78463b211970f5380d1ca67a`.

1. Read the tracked repository paths with `git ls-files`; sort eligible paths using a deterministic priority order for core analysis and application workflow, followed by lexical order within project areas, with ML training code last.
2. Include authored `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.py`, `.sql`, and `.css` source files. Include only explicitly listed runtime, test, model, and data-source configuration files. Exclude generated files, dependency and data files, docs, assets, and lock files.
3. Hash each eligible file's exact repository bytes with SHA-256. Display UTF-8 source lines with four-digit line numbers, preserving text and indentation. Physical lines longer than the printable width are continued visually without omission or source edits.
4. Paginate all eligible source into A4 portrait pages using 78 visual rows per page and a 108-column code wrap. Each page repeats the source-file path when a file continues. The cover is created separately after page selection and is not counted.
5. If the complete compilation has at least 20 pages, choose pages 1-10 and the final 10 pages, in ascending order. If it has fewer than 20 pages, include each page once.
6. Render the cover and selected pages with locally installed Puppeteer/Chromium. The 20 PNGs in `source_pages/` are image previews of the source pages, and the PDF includes those pages after its separate cover.
7. The generator scans included source for common credential patterns and stops if a likely secret is found; it does not redact or rewrite code.

To reproduce on macOS with Python 3, Git, Node.js, and Puppeteer already available: `python3 submission/generate_source_pages.py`. The script creates the manifest, page map, PDF, page previews, and validation report. It installs no dependencies, edits no application source, and performs no Git commit or push.

The official Copyright Rules, Rule 70(5), specify first and last 10 source-code pages, or all source when the complete code has fewer than 20 pages, without blocked/redacted portions: https://copyright.gov.in/Copyright_Rules_2013/chapter_xiii.html. The Copyright Office upload guidance says the software work PDF must be below 10 MB: https://copyright.gov.in/UserRegistration/frmLoginPage.aspx?url=https%3A%2F%2Fcopyright.gov.in%2FApplicant%2FUploadWork.aspx. Portal requirements should be rechecked at filing; this package does not assert legal sufficiency.

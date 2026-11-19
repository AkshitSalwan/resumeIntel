# Source PDF validation results

- Result: **PASS**
- PDF pages: 21 total (20 source pages plus one separate cover).
- Complete source compilation: 138 pages; selected pages 1–10 and 129–138.
- PDF size: 622508 bytes (0.623 MB decimal), under 10 MB.
- Eligible source files hashed: 158; mismatches: 0.
- Source page preview PNGs: 20.

## Checks

- PASS — pdf signature
- PASS — pdf eof
- PASS — pdf unencrypted
- PASS — pdf size under 10mb
- PASS — pdf page tree count is 21
- PASS — cover is separate
- PASS — source page total is 20
- PASS — first last source pages are 1 10 129 138
- PASS — page map lists first ten
- PASS — page map lists last ten
- PASS — page map reports 138 source pages
- PASS — manifest sha256 matches repository
- PASS — manifest source file count is 158
- PASS — twenty page previews present
- PASS — preview png signatures valid
- PASS — pdf has 21 leaf page objects

The PDF page count was resolved by walking its catalog page tree; it was also opened with PDFKit. Actual PDF cover, first source page, and last source page previews are in this directory. Source excerpt PNGs are in `../source_pages/`. The generator performed a credential-pattern scan before rendering. No source code was rewritten, redacted, or truncated.

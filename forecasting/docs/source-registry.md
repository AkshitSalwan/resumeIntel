# Historical source registry

This phase does not download or scrape public datasets. Sources must be
manually acquired through their permitted channels and passed to the CLI.

| Source | Identifier / URL | License or terms | Historical / geographic coverage | Limitations |
| --- | --- | --- | --- | --- |
| Kaggle job-posting datasets | Dataset-specific; use the dataset page URL | Dataset-specific; verify before use | Dataset-specific | Credentials may be required; schema and coverage vary |
| O*NET | https://www.onetcenter.org/database.html | O*NET database terms | US occupations and skill relationships | Occupational relationships are not posting-level demand |
| ESCO | https://esco.ec.europa.eu/en/use-esco/download | ESCO terms; verify current version | European occupations and skills | Classification data is not historical posting demand |
| World Economic Forum reports | https://www.weforum.org/reports/ | Report-specific terms | Report-specific | Supplementary context, not posting-level demand |
| arXiv metadata | https://info.arxiv.org/help/api/index.html | arXiv/API terms | Research metadata | Research activity is not hiring demand |
| Public patent datasets | Dataset-specific | Dataset-specific | Dataset-specific | Innovation signal, not direct labor demand |

Record the exact dataset identifier, URL, license, collection date, period,
geography, and any transformations in the ingestion run metadata. Do not
automate collection from sites whose terms or robots policies prohibit it.

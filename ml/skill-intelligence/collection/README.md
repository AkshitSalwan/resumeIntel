# Public job posting collection

This isolated collector uses only official public ATS endpoints:

- Greenhouse boards API with `content=true`
- Lever postings API with `mode=json` and documented pagination
- Ashby job-board posting API

The starter registry contains boards verified on 2026-11-09 for Airbnb,
Stripe, Anthropic, OpenAI, and Linear. Lever is supported by the adapter, but
no Lever starter entry is included because the checked candidates returned
404; add a verified site to `registry.json` only after checking its official
endpoint.

## Collection commands

```bash
cd ml/skill-intelligence
../../.venv/bin/python -m collection.collector --max-records 500 \
  --max-records-per-company 125 \
  --minimum-description-length 300 --checkpoint-interval 100 \
  --rate-limit-seconds 1.0 --output-root data/job-postings
```

`--max-records` is a global output target (default 1,000). By default, the
collector allocates a roughly equal maximum per registry company; override
that with `--max-records-per-company` or cap an ATS with
`--max-records-per-source`. `--no-resume` starts a fresh run; otherwise an
interrupted running checkpoint is resumed. The collector stores raw API
responses under `raw/`, normalized records under `normalized/`, and quality
reports/checkpoints under `reports/`. Raw filenames include a run ID and are
never overwritten. The report contains discovered, fetched, parsed, rejected,
normalized, unique, and exported counts by board.

The normalized schema preserves both `location_raw` and the resolved
`country`. Country is populated only from explicit country names, ISO codes, or
curated aliases (UK, USA, India); ambiguous or city-only locations remain
null. Greenhouse `updated_at` is stored as `source_updated_at`, never as
`published_at`.
It retries transient HTTP failures with bounded backoff, honors `Retry-After`,
and never bypasses authentication or access controls.

Public accessibility is not a redistribution license. Review each company's
terms and the ATS terms before sharing or using collected records for model
training. Registry country describes the employer's headquarters context, not
the job location; adapters leave posting country unknown unless the API
provides it. The dataset is not copied into Supabase or production application
tables.

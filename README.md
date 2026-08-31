# Enterprise Master Data & Data Quality Management System

MedCore Pharmaceuticals portfolio project: a repeatable pipeline that turns inconsistent CRM, ERP and sales extracts into governed customer and product master data.

## Run the complete project

```powershell
py -m pip install -r requirements.txt
py generate_source_data.py
py run_pipeline.py
```

The pipeline writes governed tables and Power BI-ready CSVs to `data/processed/` and a scorecard plus JSON summary to `reports/`.

To use PostgreSQL, create a database, run `sql/schema.sql`, then set a connection URL for the current PowerShell session:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@localhost:5432/medcore_mdm"
py run_pipeline.py
```

See [docs/architecture.md](docs/architecture.md), [docs/data-quality-rules.md](docs/data-quality-rules.md), [docs/methodology.md](docs/methodology.md), [docs/data-dictionary.md](docs/data-dictionary.md), [docs/runbook.md](docs/runbook.md), [docs/power-bi.md](docs/power-bi.md), and [docs/cv-ready-description.md](docs/cv-ready-description.md).

## Phase 1 — source dataset generation

`generate_source_data.py` creates the raw landing-zone extracts. The data is deterministic (`SEED = 20260830`) and deliberately includes missing fields, duplicates, formatting variants, invalid contact details, source conflicts, bad transaction values, an invalid date and a missing customer reference. These are intentional test fixtures—not issues corrected by the generator.

Run:

```powershell
py generate_source_data.py
```

Inspect `data/raw/generation_manifest.json` for file schemas, row counts and the injected issue categories. Phase 2 will define persistence; Phase 3 will quantify and report these issues programmatically.

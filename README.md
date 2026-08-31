# Enterprise Master Data & Data Quality Management System

MedCore Pharmaceuticals is a reproducible portfolio project that simulates an enterprise data-management workflow. Inconsistent CRM, ERP, product, and sales extracts are validated, standardized, reconciled, and published as governed customer and product master data.

## What the project demonstrates

- Raw data ingestion with an immutable landing layer
- Python and Pandas ETL processing
- Automated completeness, validity, uniqueness, consistency, and referential-integrity checks
- Customer and product standardization
- Confidence-scored entity resolution with configurable matching rules
- Source-to-master mappings for traceability
- Data lineage and rejected-record review queues
- PostgreSQL governed data storage
- SQL analytics and Power BI-ready outputs
- Repeatable command-line execution

## Architecture

```text
CRM / ERP / Sales extracts
            |
        data/raw
            |
  validation and quality scoring
            |
 standardization and normalization
            |
 confidence-scored entity resolution
            |
 master data and source mappings
            |
 PostgreSQL and data/processed outputs
            |
 SQL analytics and Power BI
```

## Run the project

Run these commands in order from the project directory:

```powershell
py -m pip install -r requirements.txt
py generate_source_data.py
py run_pipeline.py
```

This runs the local CSV/report workflow and writes outputs to `data/processed/` and `reports/`.

## Run with PostgreSQL

One-time database setup:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d postgres -c "CREATE DATABASE medcore_mdm;"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d medcore_mdm -f .\sql\schema.sql
```

For each new terminal session, set the connection URL and run the pipeline:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/medcore_mdm"
py run_pipeline.py
```

The PostgreSQL loader refreshes the current project snapshot atomically. A failed load rolls back to the previous snapshot. Do not commit passwords or connection strings containing real credentials.

Verify the database:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d medcore_mdm -c "SELECT 'master_customer' AS table_name, COUNT(*) FROM master_customer UNION ALL SELECT 'master_product', COUNT(*) FROM master_product UNION ALL SELECT 'sales_transactions', COUNT(*) FROM sales_transactions UNION ALL SELECT 'rejected_records', COUNT(*) FROM rejected_records;"
```

Expected counts for the included deterministic dataset are 120 master customers, 6 master products, 500 sales transactions, and 17 rejected records.

## Generated source data

`generate_source_data.py` uses a fixed seed (`20260830`) and writes intentionally imperfect source extracts to `data/raw/`:

| File | Rows | Description |
|---|---:|---|
| `crm_customers.csv` | 121 | CRM customer records, including a business duplicate |
| `erp_customers.csv` | 120 | ERP customer records with source variations |
| `crm_products.csv` | 6 | CRM product records |
| `erp_products.csv` | 6 | ERP product records with a spelling variant |
| `sales_transactions.csv` | 500 | Sales facts with invalid values and a broken reference |

Injected issues include missing fields, invalid emails and phones, formatting differences, duplicate entities, conflicting source values, product aliases, negative business values, an impossible date, and a missing customer reference.

## Pipeline outputs

The pipeline writes these Power BI-ready files to `data/processed/`:

- `master_customer.csv`
- `master_product.csv`
- `customer_mapping.csv`
- `product_mapping.csv`
- `sales_transactions.csv`
- `data_quality_results.csv`
- `rejected_records.csv`
- `data_lineage.csv`

It writes the quality scorecard and run summary to `reports/`:

- `data_quality_scorecard.csv`
- `pipeline_summary.json`

The latest run produces a calculated quality score of 99.69% from 5,441 passed checks out of 5,458 evaluated checks.

## Database and analytics

PostgreSQL schema: [sql/schema.sql](sql/schema.sql)

Analytics queries: [sql/analytics.sql](sql/analytics.sql)

Power BI build guide: [docs/power-bi.md](docs/power-bi.md)

## Documentation

- [Architecture](docs/architecture.md)
- [Data-quality rules](docs/data-quality-rules.md)
- [Master-data methodology](docs/methodology.md)
- [Data dictionary](docs/data-dictionary.md)
- [Restart runbook](docs/runbook.md)
- [Power BI guide](docs/power-bi.md)
- [CV-ready project description](docs/cv-ready-description.md)

## Scope and limitations

The data is synthetic and intended for demonstrating data-management reasoning. Accuracy is not measured against an external reference source. Matching thresholds are configurable assumptions and should be calibrated using steward-labelled examples in production. The implementation uses Pandas and standard-library similarity for portability; larger workloads could use Spark, Delta Lake, candidate blocking, or a specialized entity-resolution library.

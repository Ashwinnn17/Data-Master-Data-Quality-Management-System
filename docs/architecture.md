# Architecture

```text
CRM / ERP / Sales CSV extracts
            |
       data/raw (immutable landing layer)
            |
 schema/value/reference validation ---> rejected_records + scorecard
            |
 standardisation (text, email, phone, product aliases)
            |
 confidence-scored entity resolution ---> review queue
            |
 master_customer / master_product + source mappings + lineage
            |
 data/processed CSVs or PostgreSQL
            |
 SQL analytics / Power BI
```

The raw layer is never updated by `run_pipeline.py`. Each run has a UTC `run_id`, allowing quality results, mappings, exceptions and lineage to be traced to a specific execution.

Canonical values follow source precedence: CRM, then ERP, then Sales. A disagreement is retained through source-to-master mappings rather than overwritten in source data. In a production setting, business data stewards would own and approve this precedence policy.

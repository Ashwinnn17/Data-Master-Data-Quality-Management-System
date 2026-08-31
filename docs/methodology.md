# Master-data and matching methodology

## Standardisation

Names are trimmed, lowercased and stripped of punctuation. Corporate suffixes such as `Pvt` and `Ltd` are removed from match keys. Email values are lowercased; phone values are reduced to digits and Indian country code `91` is removed when present. Product aliases such as `AMOX` and `PCM` expand to their generic-name keys.

## Entity resolution

The resolver evaluates source records in precedence order: CRM, ERP, Sales.

1. Exact normalized email: confidence `1.00`.
2. Exact normalized phone: confidence `0.98`.
3. Customer name similarity, with a city agreement bonus of `0.05`.
4. Product normalized-name/alias similarity.

Scores at least `0.90` are automatically matched. Scores from `0.75` through `0.899` require review; lower scores become a new canonical record and are recorded as unmatched. The thresholds are policy assumptions for this portfolio dataset, not universal truth. Production thresholds should be calibrated from labelled stewardship decisions and monitored for false matches.

## Governance controls

- Each mapping retains source system, source identifier, confidence, status and rule.
- `data_lineage` records raw field → transformation → master target field.
- `rejected_records` is the operational review queue for quality exceptions and uncertain matches.
- Source data remains preserved in `data/raw`.
- PostgreSQL is refreshed atomically as a current governed snapshot on each run; a failed load rolls back to the previous snapshot.

## Limitations and next steps

This project uses deterministic synthetic data and `difflib` similarity for portability. At larger volumes, block candidate pairs by contact/location keys, use RapidFuzz or Splink, persist decision history, and introduce steward workflows. Deploying on Databricks would use Delta bronze/silver/gold layers, Spark transformations, data expectations, and scheduled workflows.

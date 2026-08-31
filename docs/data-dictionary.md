# Data dictionary

| Dataset | Key | Purpose |
|---|---|---|
| `master_customer` | `master_customer_id` | Canonical customer record, selected by source precedence and enrichment of blanks only |
| `master_product` | `master_product_id` | Canonical pharmaceutical product record |
| `customer_mapping` | `source_system`, `source_id` | Source-to-master customer traceability with confidence and rule |
| `product_mapping` | `source_system`, `source_id` | Source-to-master product traceability with confidence and rule |
| `sales_transactions` | `transaction_id` | Transaction facts enriched with master customer/product IDs |
| `data_quality_results` | `run_id`, dataset, dimension | Passed/evaluated checks and calculated score |
| `rejected_records` | `run_id`, record identifier | Quality failures and entity-resolution review queue |
| `data_lineage` | `run_id`, entity/field | Raw-field to standardized-field to target-field lineage |

Mapping fields: `confidence` is a 0–1 match score; `match_status` is `new_master` or `auto_matched`; `match_rule` explains the evidence used. Low-confidence candidates are retained in `rejected_records` with `reason = review_required` rather than automatically merged.

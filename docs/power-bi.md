# Power BI dashboard guide

This guide builds a data-management dashboard from the pipeline outputs. You can connect Power BI either to the processed CSV files or directly to PostgreSQL. PostgreSQL is the stronger portfolio demonstration; CSV import is a simple fallback.

## 1. Generate the latest outputs

From the project folder:

```powershell
py generate_source_data.py
py run_pipeline.py
```

The report uses one pipeline run at a time. The current files are written to `data/processed/` and the latest scorecard is in `reports/data_quality_scorecard.csv`.

## 2. Load the data

### Recommended: PostgreSQL

In Power BI Desktop select **Home → Get data → PostgreSQL database** and enter:

```text
Server: localhost
Database: medcore_mdm
```

Choose **Import**, then select these tables:

```text
master_customer
master_product
customer_mapping
product_mapping
sales_transactions
data_quality_results
rejected_records
data_lineage
```

Use the same PostgreSQL username and password used by the pipeline.

### Fallback: processed CSVs

Select **Home → Get data → Text/CSV** and import these files from `data/processed/`:

```text
master_customer.csv
master_product.csv
customer_mapping.csv
product_mapping.csv
sales_transactions.csv
data_quality_results.csv
rejected_records.csv
data_lineage.csv
```

Choose **Transform data** before loading if Power BI inferred an ID as a number. Keep all ID columns as **Text**. Set `transaction_date` to **Date**, and `quantity`, `unit_price`, and `revenue` to numeric types.

## 3. Create the relationships

Open **Model view** and create these relationships. The master side is the `1` side; the transaction/mapping side is the `*` side. Use single-direction filtering from master to detail.

| From table/column | To table/column | Cardinality |
|---|---|---|
| `sales_transactions[master_customer_id]` | `master_customer[master_customer_id]` | Many-to-one |
| `sales_transactions[master_product_id]` | `master_product[master_product_id]` | Many-to-one |
| `customer_mapping[master_customer_id]` | `master_customer[master_customer_id]` | Many-to-one |
| `product_mapping[master_product_id]` | `master_product[master_product_id]` | Many-to-one |

Do not create a direct relationship between mapping tables and sales transactions; that can create ambiguous filtering. `data_quality_results`, `rejected_records`, and `data_lineage` can remain standalone tables because they describe pipeline operations rather than sales facts.

## 4. Create measures

Create these measures in the corresponding tables. Format `Quality Score %` as a percentage with two decimal places.

```DAX
Quality Score % =
DIVIDE(
    SUM(data_quality_results[passed]),
    SUM(data_quality_results[evaluated])
)

Evaluated Checks = SUM(data_quality_results[evaluated])

Failed Checks =
SUM(data_quality_results[evaluated]) - SUM(data_quality_results[passed])

Quality Issues = COUNTROWS(rejected_records)

Master Customers = DISTINCTCOUNT(master_customer[master_customer_id])

Master Products = DISTINCTCOUNT(master_product[master_product_id])

Total Revenue = SUM(sales_transactions[revenue])

Transactions = DISTINCTCOUNT(sales_transactions[transaction_id])

Auto-Matched Customer Records =
CALCULATE(
    COUNTROWS(customer_mapping),
    customer_mapping[match_status] = "auto_matched"
)

Critical Issues =
CALCULATE(
    COUNTROWS(rejected_records),
    rejected_records[severity] = "critical"
)
```

The score measure returns `0.9969` internally and displays as `99.69%` when formatted as a percentage. Do not average the `quality_score_pct` column; calculate the score from total passed and evaluated checks.

## 5. Build the report pages

### Page 1 — Executive Data Quality

Add:

- Card: `Quality Score %`
- Card: `Evaluated Checks`
- Card: `Failed Checks`
- Card: `Quality Issues`
- Donut chart: `rejected_records[severity]` by count of records
- Bar chart: `data_quality_results[dataset]` and `data_quality_results[quality_score_pct]`
- Column chart: `data_quality_results[dimension]` and `data_quality_results[quality_score_pct]`

This page answers: “Can management trust the current data-processing run?”

### Page 2 — Customer Master

Add:

- Card: `Master Customers`
- Bar chart: `master_customer[state]` by count of `master_customer_id`
- Bar chart: `master_customer[customer_type]` by count of `master_customer_id`
- Stacked bar chart: `customer_mapping[source_system]` by `customer_mapping[match_status]`
- Table: source system, source ID, master customer ID, confidence, match rule

This page shows how many customers were governed and how source records were reconciled.

### Page 3 — Product Master

Add:

- Card: `Master Products`
- Bar chart: `master_product[category]` by count of `master_product_id`
- Table: product ID, product name, category, strength
- Bar chart: `product_mapping[match_rule]` by count of source IDs
- Table: source system, source ID, master product ID, confidence

This page demonstrates product standardization and alias resolution.

### Page 4 — Data Issues

Add:

- Card: `Critical Issues`
- Bar chart: `rejected_records[rule_name]` by count of records
- Bar chart: `rejected_records[dataset]` by count of records
- Donut chart: `rejected_records[severity]` by count
- Table: dataset, record ID, rule name, field name, observed value, severity

Add slicers for `dataset`, `rule_name`, and `severity`. Enable drill-through on `record_id` if you want a detailed issue page.

## 6. Optional filters and quality interpretation

Useful slicers include source system, dataset, quality dimension, severity, match status, product category, and customer state.

The quality score is an operational indicator based on automated checks. It is not a clinical-accuracy score. Accuracy is not measured because the project does not have a trusted external reference dataset.

The source-to-master mappings should be used to explain reconciliations. Do not hide source IDs from the report; they are useful for audit and stewardship workflows.

## 7. Refreshing the report

After regenerating the data:

1. Run the pipeline again.
2. Open the Power BI file.
3. Select **Home → Refresh**.
4. Confirm that the latest `run_id` is visible in the data-quality and mapping tables.
5. Save the report as a `.pbix` file.

The pipeline refreshes the PostgreSQL project snapshot atomically. If using CSVs, Power BI reads the files from the same `data/processed/` paths.

## 8. Suggested report title

```text
MedCore Pharmaceuticals — Master Data & Data Quality Dashboard
```

Use `reports/pipeline_summary.json` as the auditable run summary rather than manually typing KPI values into the report.

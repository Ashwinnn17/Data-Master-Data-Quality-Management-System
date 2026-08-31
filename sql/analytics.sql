-- Data-quality KPI by dataset and dimension
SELECT dataset, dimension, quality_score_pct, passed, evaluated
FROM data_quality_results
ORDER BY dataset, dimension;

-- Master-data reconciliation status
SELECT source_system, match_status, COUNT(*) AS records
FROM customer_mapping
GROUP BY source_system, match_status
ORDER BY source_system, match_status;

-- Customer geography for Power BI
SELECT state, customer_type, COUNT(*) AS master_customers
FROM master_customer
GROUP BY state, customer_type
ORDER BY master_customers DESC;

-- Data issues by rule and severity
SELECT dataset, rule_name, severity, COUNT(*) AS issue_count
FROM rejected_records
WHERE entity_type = 'data_quality'
GROUP BY dataset, rule_name, severity
ORDER BY issue_count DESC;

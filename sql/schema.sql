-- Run once in PostgreSQL before setting DATABASE_URL and running the pipeline.
CREATE TABLE IF NOT EXISTS master_customer (
  master_customer_id TEXT PRIMARY KEY, master_name TEXT, email TEXT, phone TEXT,
  city TEXT, state TEXT, country TEXT, customer_type TEXT
);
CREATE TABLE IF NOT EXISTS master_product (
  master_product_id TEXT PRIMARY KEY, master_product_name TEXT, category TEXT, strength TEXT
);
CREATE TABLE IF NOT EXISTS customer_mapping (
  run_id TEXT, source_system TEXT, source_id TEXT, master_customer_id TEXT,
  confidence NUMERIC(4,3), match_status TEXT, match_rule TEXT
);
CREATE TABLE IF NOT EXISTS product_mapping (
  run_id TEXT, source_system TEXT, source_id TEXT, master_product_id TEXT,
  confidence NUMERIC(4,3), match_status TEXT, match_rule TEXT
);
CREATE TABLE IF NOT EXISTS sales_transactions (
  transaction_id TEXT, customer_id TEXT, customer_name TEXT, product_id TEXT, product_name TEXT,
  transaction_date DATE, quantity NUMERIC, unit_price NUMERIC, revenue NUMERIC,
  master_customer_id TEXT, master_product_id TEXT
);
CREATE TABLE IF NOT EXISTS data_quality_results (
  run_id TEXT, dataset TEXT, dimension TEXT, passed INTEGER, evaluated INTEGER,
  definition TEXT, quality_score_pct NUMERIC(5,2)
);
CREATE TABLE IF NOT EXISTS rejected_records (
  run_id TEXT, dataset TEXT, record_id TEXT, rule_name TEXT, field_name TEXT,
  observed_value TEXT, severity TEXT, entity_type TEXT, reason TEXT, confidence NUMERIC(4,3), suggested_master_id TEXT
);
CREATE TABLE IF NOT EXISTS data_lineage (
  run_id TEXT, entity_type TEXT, raw_field TEXT, transformation TEXT,
  standardized_field TEXT, target_table TEXT, target_field TEXT
);

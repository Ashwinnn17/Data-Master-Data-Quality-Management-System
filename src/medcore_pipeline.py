"""Validation, standardisation, matching and governed-output generation."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd


RAW = Path("data/raw")
OUT = Path("data/processed")
REPORTS = Path("reports")
RUN_ID = datetime.now(UTC).strftime("run_%Y%m%dT%H%M%SZ")
EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE = re.compile(r"^\d{10,15}$")
STOPWORDS = {"pvt", "private", "limited", "ltd", "inc", "corporation", "corp"}
SOURCE_PRIORITY = {"CRM": 1, "ERP": 2, "SALES": 3}


def clean_text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    return re.sub(r"\s+", " ", str(value).strip()) or None


def norm_text(value: Any, remove_stopwords: bool = False) -> str | None:
    value = clean_text(value)
    if not value:
        return None
    result = re.sub(r"[^a-z0-9 ]", " ", value.lower())
    words = result.split()
    if remove_stopwords:
        words = [word for word in words if word not in STOPWORDS]
    return " ".join(words) or None


def norm_phone(value: Any) -> str | None:
    value = clean_text(value)
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return digits or None


def norm_email(value: Any) -> str | None:
    value = clean_text(value)
    return value.lower() if value else None


def rename_source_id(frame: pd.DataFrame, id_column: str) -> pd.DataFrame:
    """Rename a dynamic source-ID column without triggering pandas-stub overload warnings."""
    output = frame.copy()
    output.columns = ["source_id" if column == id_column else column for column in output.columns]
    return output


def similarity(left: Any, right: Any) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, str(left), str(right)).ratio()


def load_raw() -> dict[str, pd.DataFrame]:
    files = {
        "crm_customers": "crm_customers.csv", "erp_customers": "erp_customers.csv",
        "crm_products": "crm_products.csv", "erp_products": "erp_products.csv",
        "sales_transactions": "sales_transactions.csv",
    }
    missing = [name for name in files.values() if not (RAW / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing raw files: {missing}. Run `py generate_source_data.py` first.")
    return {name: pd.read_csv(RAW / filename) for name, filename in files.items()}


def add_issue(issues: list[dict[str, Any]], dataset: str, record_id: str, rule: str, field: str, value: Any, severity: str = "high") -> None:
    issues.append({"run_id": RUN_ID, "dataset": dataset, "record_id": record_id, "rule_name": rule,
                   "field_name": field, "observed_value": "" if pd.isna(value) else str(value), "severity": severity})


def validate(data: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return record-level exceptions and dimension-level quality metrics."""
    issues: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    customer_specs = [("crm_customers", "customer_id"), ("erp_customers", "erp_customer_id")]
    product_specs = [("crm_products", "product_id"), ("erp_products", "erp_product_id")]
    for dataset, identifier in customer_specs + product_specs:
        frame = data[dataset]
        required = [col for col in frame.columns if col != identifier]
        missing = 0
        for _, row in frame.iterrows():
            for field in required:
                if pd.isna(row[field]) or clean_text(row[field]) is None:
                    missing += 1
                    add_issue(issues, dataset, str(row[identifier]), "required_field_present", field, row[field])
        duplicate_ids = int(frame[identifier].duplicated().sum())
        for _, row in frame[frame[identifier].duplicated(keep=False)].iterrows():
            add_issue(issues, dataset, str(row[identifier]), "primary_key_unique", identifier, row[identifier], "critical")
        opportunities = len(frame) * len(required)
        metrics.append(metric(dataset, "completeness", opportunities - missing, opportunities, "Required non-null fields"))
        metrics.append(metric(dataset, "uniqueness", len(frame) - duplicate_ids, len(frame), "Primary-key uniqueness"))
    for dataset, identifier in customer_specs:
        frame = data[dataset]
        bad = 0
        for _, row in frame.iterrows():
            email = norm_email(row["email"])
            if email and not EMAIL.fullmatch(email):
                bad += 1; add_issue(issues, dataset, str(row[identifier]), "valid_email", "email", row["email"])
            phone = norm_phone(row["phone"])
            if phone and not PHONE.fullmatch(phone):
                bad += 1; add_issue(issues, dataset, str(row[identifier]), "valid_phone", "phone", row["phone"])
        metrics.append(metric(dataset, "validity", len(frame) * 2 - bad, len(frame) * 2, "Email and phone format"))
    sales = data["sales_transactions"]
    bad_sales = 0
    for _, row in sales.iterrows():
        transaction_id = str(row["transaction_id"])
        checks = {
            "positive_quantity": (row["quantity"] > 0, "quantity", row["quantity"]),
            "positive_unit_price": (row["unit_price"] > 0, "unit_price", row["unit_price"]),
            "positive_revenue": (row["revenue"] > 0, "revenue", row["revenue"]),
            "valid_transaction_date": (not pd.isna(pd.to_datetime(row["transaction_date"], errors="coerce")), "transaction_date", row["transaction_date"]),
        }
        for rule, (passed, field, value) in checks.items():
            if not passed:
                bad_sales += 1; add_issue(issues, "sales_transactions", transaction_id, rule, field, value)
    metrics.append(metric("sales_transactions", "validity", len(sales) * 4 - bad_sales, len(sales) * 4, "Positive values and parseable date"))
    crm_ids = set(data["crm_customers"]["customer_id"])
    failures = sales.loc[~sales["customer_id"].isin(crm_ids)]
    for _, row in failures.iterrows():
        add_issue(issues, "sales_transactions", str(row["transaction_id"]), "customer_reference_exists", "customer_id", row["customer_id"], "critical")
    metrics.append(metric("sales_transactions", "referential_integrity", len(sales) - len(failures), len(sales), "Sales customer exists in CRM extract"))
    # Consistency is measured as revenue agreeing with quantity x price, to two decimals.
    revenue_ok = (sales["revenue"].round(2) == (sales["quantity"] * sales["unit_price"]).round(2))
    for _, row in sales.loc[~revenue_ok].iterrows():
        add_issue(issues, "sales_transactions", str(row["transaction_id"]), "revenue_calculation_consistent", "revenue", row["revenue"])
    metrics.append(metric("sales_transactions", "consistency", int(revenue_ok.sum()), len(sales), "Revenue = quantity × unit price"))
    results = pd.DataFrame(metrics)
    results["quality_score_pct"] = (results["passed"] / results["evaluated"] * 100).round(2)
    return pd.DataFrame(issues), results


def metric(dataset: str, dimension: str, passed: int, evaluated: int, definition: str) -> dict[str, Any]:
    return {"run_id": RUN_ID, "dataset": dataset, "dimension": dimension, "passed": int(passed), "evaluated": int(evaluated), "definition": definition}


def standardise_customers(frame: pd.DataFrame, source: str, id_column: str) -> pd.DataFrame:
    output = rename_source_id(frame, id_column)
    output.insert(0, "source_system", source)
    output["name_normalized"] = output["customer_name"].map(lambda x: norm_text(x, remove_stopwords=True))
    output["email_normalized"] = output["email"].map(norm_email)
    output["phone_normalized"] = output["phone"].map(norm_phone)
    output["city_normalized"] = output["city"].map(norm_text)
    output["state_normalized"] = output["state"].map(norm_text)
    output["country_normalized"] = output["country"].map(norm_text)
    return output


def standardise_products(frame: pd.DataFrame, source: str, id_column: str) -> pd.DataFrame:
    output = rename_source_id(frame, id_column)
    output.insert(0, "source_system", source)
    output["name_normalized"] = output["product_name"].map(lambda x: norm_text(x, remove_stopwords=True))
    aliases = {r"\bamox\b": "amoxicillin", r"\bmet\b": "metformin", r"\batorva\b": "atorvastatin",
               r"\bpcm\b": "paracetamol", r"\bomep\b": "omeprazole", r"\bceti\b": "cetirizine"}
    output["product_key"] = output["name_normalized"]
    for alias, canonical in aliases.items():
        output["product_key"] = output["product_key"].str.replace(alias, canonical, regex=True)
    return output


def choose_match(record: pd.Series, masters: list[dict[str, Any]], entity: str) -> tuple[dict[str, Any] | None, float, str, str]:
    best: tuple[dict[str, Any] | None, float, str, str] = (None, 0.0, "unmatched", "unmatched")
    for master in masters:
        if entity == "customer":
            if record.get("email_normalized") and record["email_normalized"] == master.get("email_normalized"):
                return master, 1.0, "auto_matched", "exact_email"
            if record.get("phone_normalized") and record["phone_normalized"] == master.get("phone_normalized"):
                return master, 0.98, "auto_matched", "exact_phone"
            if record.get("name_normalized") and record["name_normalized"] == master.get("name_normalized"):
                return master, 0.95, "auto_matched", "exact_normalized_name"
            name_score = similarity(record.get("name_normalized"), master.get("name_normalized"))
            record_numbers = set(re.findall(r"\d+", record.get("name_normalized") or ""))
            master_numbers = set(re.findall(r"\d+", master.get("name_normalized") or ""))
            if record_numbers and master_numbers and record_numbers != master_numbers:
                name_score = 0.0  # Distinct branch/account identifiers veto a fuzzy merge candidate.
            city_bonus = 0.05 if record.get("city_normalized") and record.get("city_normalized") == master.get("city_normalized") else 0
            score = min(1.0, name_score + city_bonus)
            rule = "name_city_similarity"
        else:
            score = max(similarity(record.get("product_key"), master.get("product_key")), similarity(record.get("name_normalized"), master.get("name_normalized")))
            rule = "product_name_similarity"
        if score > best[1]:
            # Similar names alone are candidate evidence, not sufficient for an automatic customer merge.
            status = "review_required" if entity == "customer" and score >= 0.75 else "auto_matched" if score >= 0.90 else "review_required" if score >= 0.75 else "unmatched"
            best = master, score, status, rule
    return best


def resolve(entity_records: pd.DataFrame, entity: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    master_rows: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for _, record in entity_records.sort_values("source_system", key=lambda s: s.map(SOURCE_PRIORITY)).iterrows():
        master, score, status, rule = choose_match(record, master_rows, entity)
        # A fuzzy candidate is deliberately not merged. It gets its own provisional
        # canonical record and a steward-review item naming the possible candidate.
        if status == "review_required" and master is not None:
            rejected.append({"run_id": RUN_ID, "entity_type": entity, "source_system": record["source_system"], "source_id": record["source_id"], "reason": status, "confidence": round(score, 3), "suggested_master_id": master["master_id"]})
            master = None
        if master is None or status == "unmatched":
            master_id = f"M{'C' if entity == 'customer' else 'P'}{len(master_rows) + 1:04d}"
            master = {"master_id": master_id, **record.to_dict()}
            master_rows.append(master)
            score, status, rule = 1.0, "new_master", "new_canonical_entity"
        else:
            # Preserve source precedence, but enrich a canonical record when its
            # preferred-source attribute is blank and a matched source supplies it.
            for field, value in record.items():
                if field in {"source_system", "source_id"}:
                    continue
                if (field not in master or clean_text(master[field]) is None) and clean_text(value) is not None:
                    master[field] = value
        mappings.append({"run_id": RUN_ID, "source_system": record["source_system"], "source_id": record["source_id"],
                         f"master_{entity}_id": master["master_id"], "confidence": round(score, 3), "match_status": status, "match_rule": rule})
        if status == "unmatched":
            rejected.append({"run_id": RUN_ID, "entity_type": entity, "source_system": record["source_system"], "source_id": record["source_id"], "reason": status, "confidence": round(score, 3), "suggested_master_id": master["master_id"] if master else None})
    master_frame = pd.DataFrame(master_rows)
    if entity == "customer":
        master_frame = master_frame.rename(columns={"master_id": "master_customer_id", "customer_name": "master_name"})
        columns = ["master_customer_id", "master_name", "email", "phone", "city", "state", "country", "customer_type"]
    else:
        master_frame = master_frame.rename(columns={"master_id": "master_product_id", "product_name": "master_product_name"})
        columns = ["master_product_id", "master_product_name", "category", "strength"]
    return master_frame.reindex(columns=columns), pd.DataFrame(mappings), pd.DataFrame(rejected)


def sales_entity_records(sales: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    customer_records = sales[["customer_id", "customer_name"]].drop_duplicates().rename(columns={"customer_id": "source_id", "customer_name": "customer_name"})
    customer_records["email"] = None; customer_records["phone"] = None; customer_records["city"] = None; customer_records["state"] = None; customer_records["country"] = None; customer_records["customer_type"] = None
    customer_records = standardise_customers(customer_records, "SALES", "source_id")
    product_records = sales.groupby("product_id", as_index=False)["product_name"].agg(lambda values: values.mode().iloc[0]).rename(columns={"product_id": "source_id"})
    product_records["category"] = None; product_records["strength"] = None
    product_records = standardise_products(product_records, "SALES", "source_id")
    return customer_records, product_records


def lineage() -> pd.DataFrame:
    rows = []
    for entity, raw_column, standard_column, master_column in [
        ("customer", "customer_name", "name_normalized", "master_name"),
        ("customer", "email", "email_normalized", "email"),
        ("customer", "phone", "phone_normalized", "phone"),
        ("product", "product_name", "product_key", "master_product_name"),
    ]:
        rows.append({"run_id": RUN_ID, "entity_type": entity, "raw_field": raw_column, "transformation": "normalization and entity resolution", "standardized_field": standard_column, "target_table": f"master_{entity}", "target_field": master_column})
    return pd.DataFrame(rows)


def build_analytics(sales: pd.DataFrame, customer_mapping: pd.DataFrame, product_mapping: pd.DataFrame) -> pd.DataFrame:
    customer_map = customer_mapping[customer_mapping["source_system"] == "SALES"][["source_id", "master_customer_id"]]
    product_map = product_mapping[product_mapping["source_system"] == "SALES"][["source_id", "master_product_id"]]
    result = sales.merge(customer_map, how="left", left_on="customer_id", right_on="source_id").drop(columns="source_id")
    result = result.merge(product_map, how="left", left_on="product_id", right_on="source_id").drop(columns="source_id")
    result["transaction_date"] = pd.to_datetime(result["transaction_date"], errors="coerce")
    return result


def write_outputs(outputs: dict[str, pd.DataFrame], quality_results: pd.DataFrame, issues: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True); REPORTS.mkdir(parents=True, exist_ok=True)
    for name, frame in outputs.items():
        frame.to_csv(OUT / f"{name}.csv", index=False)
    issues.to_csv(OUT / "rejected_records.csv", index=False)
    quality_results.to_csv(OUT / "data_quality_results.csv", index=False)
    summary = {"run_id": RUN_ID, "overall_quality_score_pct": round(float((quality_results["passed"].sum() / quality_results["evaluated"].sum()) * 100), 2),
               "issues_found": int(len(issues)), "records_requiring_review": int((issues["reason"] == "review_required").sum() if "reason" in issues else 0),
               "master_customers": int(len(outputs["master_customer"])), "master_products": int(len(outputs["master_product"]))}
    (REPORTS / "pipeline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    quality_results.to_csv(REPORTS / "data_quality_scorecard.csv", index=False)


def load_postgres(outputs: dict[str, pd.DataFrame], quality: pd.DataFrame, issues: pd.DataFrame) -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        return
    try:
        from sqlalchemy import create_engine
    except ImportError as exc:
        raise RuntimeError("DATABASE_URL is set; install optional dependency `sqlalchemy psycopg[binary]`.") from exc
    engine = create_engine(url)
    all_tables = {**outputs, "data_quality_results": quality, "rejected_records": issues}
    with engine.begin() as connection:
        # The database tables represent the current governed snapshot. Refresh
        # them atomically so rerunning the pipeline does not collide with the
        # master-table primary keys. If a later insert fails, the transaction
        # rolls back and the previous snapshot remains available.
        for table_name in all_tables:
            connection.exec_driver_sql(f'DELETE FROM "{table_name}"')
        for name, frame in all_tables.items():
            frame.to_sql(name, connection, if_exists="append", index=False, method="multi")


def run() -> None:
    data = load_raw()
    issues, quality = validate(data)
    crm_customers = standardise_customers(data["crm_customers"], "CRM", "customer_id")
    erp_customers = standardise_customers(data["erp_customers"], "ERP", "erp_customer_id")
    crm_products = standardise_products(data["crm_products"], "CRM", "product_id")
    erp_products = standardise_products(data["erp_products"], "ERP", "erp_product_id")
    sales_customers, sales_products = sales_entity_records(data["sales_transactions"])
    master_customer, customer_mapping, customer_rejected = resolve(pd.concat([crm_customers, erp_customers, sales_customers], ignore_index=True), "customer")
    master_product, product_mapping, product_rejected = resolve(pd.concat([crm_products, erp_products, sales_products], ignore_index=True), "product")
    governed_sales = build_analytics(data["sales_transactions"], customer_mapping, product_mapping)
    outputs = {"master_customer": master_customer, "master_product": master_product, "customer_mapping": customer_mapping,
               "product_mapping": product_mapping, "sales_transactions": governed_sales, "data_lineage": lineage()}
    all_rejected = pd.concat([issues.assign(entity_type="data_quality", reason=issues["rule_name"], confidence=None, suggested_master_id=None), customer_rejected, product_rejected], ignore_index=True, sort=False)
    # Pandas otherwise infers an all-null confidence column as text, which is
    # incompatible with PostgreSQL's NUMERIC confidence field.
    all_rejected["confidence"] = pd.to_numeric(all_rejected["confidence"], errors="coerce").astype("Float64")
    write_outputs(outputs, quality, all_rejected)
    load_postgres(outputs, quality, all_rejected)
    summary = json.loads((REPORTS / "pipeline_summary.json").read_text(encoding="utf-8"))
    print(f"Pipeline complete: score {summary['overall_quality_score_pct']}%, {summary['master_customers']} master customers, {summary['master_products']} master products.")
    print(f"Outputs: {OUT} | Reports: {REPORTS}")

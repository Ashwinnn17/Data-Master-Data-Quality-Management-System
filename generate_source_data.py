"""Generate deterministic, intentionally imperfect source extracts for MedCore.

The files written by this script represent the raw landing layer.  They are not
corrected here: later pipeline phases will validate, standardise and reconcile
them while retaining their source-system provenance.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd


SEED = 20260830
OUTPUT_DIR = Path("data/raw")

FIRST_NAMES = ["Aarav", "Diya", "Ishaan", "Kavya", "Rohan", "Meera", "Arjun", "Nisha"]
ORGANISATIONS = [
    "Apollo Hospitals", "Sunrise Clinic", "Green Valley Pharmacy",
    "Carewell Medical Centre", "Zenith Diagnostics", "Lifeline Hospital",
    "Nova Health Distributors", "Medisource Pharmacy",
]
LOCATIONS = [
    ("Hyderabad", "Telangana"), ("Bangalore", "Karnataka"),
    ("Mumbai", "Maharashtra"), ("Pune", "Maharashtra"),
    ("Chennai", "Tamil Nadu"), ("Delhi", "Delhi"),
]
PRODUCTS = [
    ("Amoxicillin 500 mg", "Antibiotic", "AMOX 500MG"),
    ("Metformin 500 mg", "Diabetes", "MET 500MG"),
    ("Atorvastatin 10 mg", "Cardiovascular", "ATORVA 10MG"),
    ("Paracetamol 650 mg", "Analgesic", "PCM 650MG"),
    ("Omeprazole 20 mg", "Gastroenterology", "OMEP 20MG"),
    ("Cetirizine 10 mg", "Allergy", "CETI 10MG"),
]


def source_customer_name(name: str, index: int, source: str) -> str:
    """Return source-specific variants that later stages should reconcile."""
    if index % 8 == 0:
        return name.upper() if source == "crm" else f"{name} Pvt. Ltd."
    if index % 11 == 0:
        return f"  {name.lower()}  "
    return name


def base_customer_name(index: int) -> str:
    """Create a stable, distinct real-world customer before source variation."""
    if index % 3 == 0:
        city, _ = LOCATIONS[(index - 1) % len(LOCATIONS)]
        return f"{FIRST_NAMES[(index - 1) % len(FIRST_NAMES)]} Pharmacy {city} {index:03d}"
    organisation = ORGANISATIONS[(index - 1) % len(ORGANISATIONS)]
    city, _ = LOCATIONS[(index - 1) % len(LOCATIONS)]
    branch = (index - 1) // len(ORGANISATIONS) + 1
    return f"{organisation} {city} Branch {branch}"


def build_customers(rng: random.Random, count: int = 120) -> tuple[pd.DataFrame, pd.DataFrame]:
    crm_rows, erp_rows = [], []
    for i in range(1, count + 1):
        is_org = i % 3 != 0
        base_name = base_customer_name(i)
        city, state = LOCATIONS[(i - 1) % len(LOCATIONS)]
        email = f"contact{i:03d}@medcore-demo.in"
        phone = f"+91 98{(10000000 + i):08d}"
        customer_type = "Provider" if is_org else "Pharmacy"

        crm_rows.append({
            "customer_id": f"C{i:04d}", "customer_name": source_customer_name(base_name, i, "crm"),
            "email": email, "phone": phone, "city": city, "state": state,
            "country": "India", "customer_type": customer_type,
        })
        erp_rows.append({
            "erp_customer_id": f"E{i:04d}", "customer_name": source_customer_name(base_name, i, "erp"),
            "email": email.upper() if i % 9 == 0 else email, "phone": phone.replace(" ", "") if i % 7 else phone[3:],
            "city": city.lower() if i % 5 == 0 else city, "state": state,
            "country": "INDIA" if i % 6 == 0 else "India", "customer_type": customer_type,
        })

    # Controlled raw-data faults. Every record remains traceable by its source ID.
    crm_rows[4]["email"] = "apollo@"
    crm_rows[12]["phone"] = "98AB1234"
    crm_rows[21]["customer_name"] = None
    crm_rows[32]["city"] = None
    erp_rows[4]["email"] = "contactapollo.com"
    erp_rows[12]["phone"] = "12345"
    erp_rows[21]["email"] = None
    erp_rows[32]["state"] = None
    erp_rows[0]["city"] = "Bangalore"  # deliberate CRM/ERP conflict
    # A within-source duplicate with a distinct source identifier.
    duplicate = crm_rows[0].copy()
    duplicate["customer_id"] = "C0121"
    duplicate["customer_name"] = "Apollo Hospitals Pvt Ltd"
    crm_rows.append(duplicate)
    return pd.DataFrame(crm_rows), pd.DataFrame(erp_rows)


def build_products() -> tuple[pd.DataFrame, pd.DataFrame]:
    crm_rows, erp_rows = [], []
    for i, (name, category, sales_name) in enumerate(PRODUCTS, start=1):
        crm_rows.append({"product_id": f"P{i:03d}", "product_name": name.upper(), "category": category, "strength": name.split()[-2] + " " + name.split()[-1]})
        erp_rows.append({"erp_product_id": f"EP{i:03d}", "product_name": name, "category": category, "strength": name.split()[-2] + name.split()[-1]})
    crm_rows[2]["category"] = None
    erp_rows[4]["product_name"] = "Omeprzole 20mg"  # typo for fuzzy matching
    return pd.DataFrame(crm_rows), pd.DataFrame(erp_rows)


def build_sales(rng: random.Random, count: int = 500) -> pd.DataFrame:
    rows = []
    for i in range(1, count + 1):
        customer_num = rng.randint(1, 120)
        product_num = rng.randint(1, len(PRODUCTS))
        canonical, _, sales_name = PRODUCTS[product_num - 1]
        quantity = rng.randint(1, 50)
        unit_price = rng.choice([42.5, 75.0, 120.0, 185.5, 240.0])
        rows.append({
            "transaction_id": f"T{i:05d}", "customer_id": f"C{customer_num:04d}",
            "customer_name": source_customer_name(base_customer_name(customer_num), customer_num, "sales"),
            "product_id": f"SP{product_num:03d}", "product_name": sales_name,
            "transaction_date": f"2026-{rng.randint(1, 7):02d}-{rng.randint(1, 28):02d}",
            "quantity": quantity, "unit_price": unit_price, "revenue": round(quantity * unit_price, 2),
        })
    rows[10]["customer_id"] = "C9999"                 # referential failure
    rows[20]["quantity"] = -4                         # invalid business value
    rows[30]["unit_price"] = -75.0                    # invalid business value
    rows[40]["revenue"] = -500.0                      # invalid business value
    rows[50]["transaction_date"] = "2099-13-40"      # impossible date
    rows[60]["product_name"] = "AMOXICILIN 500MG"     # spelling variant
    return pd.DataFrame(rows)


def main() -> None:
    rng = random.Random(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    crm, erp = build_customers(rng)
    crm_products, erp_products = build_products()
    sales = build_sales(rng)
    outputs = {
        "crm_customers.csv": crm, "erp_customers.csv": erp,
        "crm_products.csv": crm_products, "erp_products.csv": erp_products,
        "sales_transactions.csv": sales,
    }
    for filename, frame in outputs.items():
        frame.to_csv(OUTPUT_DIR / filename, index=False)
    manifest = {
        "seed": SEED,
        "purpose": "Raw source extracts with intentional data-quality defects for later phases.",
        "files": {name: {"rows": len(frame), "columns": list(frame.columns)} for name, frame in outputs.items()},
        "injected_issues": [
            "missing values", "within-source duplicate", "format variations", "invalid emails and phones",
            "source-system location conflict", "referential failure", "negative business values", "impossible date", "product spelling variants",
        ],
    }
    (OUTPUT_DIR / "generation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {sum(len(frame) for frame in outputs.values())} raw rows in {OUTPUT_DIR}")
    for filename, frame in outputs.items():
        print(f"- {filename}: {len(frame)} rows")


if __name__ == "__main__":
    main()

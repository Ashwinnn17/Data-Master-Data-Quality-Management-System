"""Run MedCore's raw-to-governed master-data pipeline.

Usage: py run_pipeline.py
Optionally set DATABASE_URL to load the outputs into PostgreSQL, e.g.
postgresql+psycopg://medcore:password@localhost:5432/medcore_mdm
"""

from src.medcore_pipeline import run


if __name__ == "__main__":
    run()

# Restart runbook: run MedCore again

Use this guide whenever you restart your laptop or VS Code. All commands below should be run from the project folder:

```text
C:\Users\ashwi\OneDrive\Documents\VSCODE\AntiGrav\Master Data and Data Quality Management System
```

## 1. Open the project terminal

In VS Code, open the project folder and choose **Terminal → New Terminal**. Confirm the prompt is in the project directory:

```powershell
Get-Location
```

If necessary:

```powershell
Set-Location "C:\Users\ashwi\OneDrive\Documents\VSCODE\AntiGrav\Master Data and Data Quality Management System"
```

## 2. Confirm PostgreSQL is running

This project uses the PostgreSQL 18 Windows service:

```powershell
Get-Service postgresql-x64-18
```

The status should be `Running`. If it is stopped, start it from an Administrator PowerShell:

```powershell
Start-Service postgresql-x64-18
```

You do not need to recreate the `medcore_mdm` database or run `sql/schema.sql` again after a normal restart. Those are one-time setup steps.

## 3. Confirm Python dependencies

This is safe to run each time; already-installed packages will be skipped:

```powershell
py -m pip install -r requirements.txt
```

## 4. Regenerate the deterministic raw files

Run:

```powershell
py generate_source_data.py
```

This recreates the same raw CRM, ERP, product, and sales extracts because the generator uses a fixed seed. It writes them to `data/raw/`.

## 5. Run the pipeline with PostgreSQL

The `DATABASE_URL` environment variable is scoped to the current terminal session, so set it again after opening a new terminal. Replace `YOUR_PASSWORD` with your PostgreSQL password, and do not commit or save this value in the repository:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/medcore_mdm"
py run_pipeline.py
```

If your password contains URL-reserved characters such as `@`, `:`, `/`, or `#`, URL-encode those characters in the connection string.

The PostgreSQL loader refreshes the current project snapshot atomically. It clears and reloads the project tables inside one transaction, so a failed run rolls back to the previous database state.

## 6. Verify the database load

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d medcore_mdm -c "SELECT 'master_customer' AS table_name, COUNT(*) FROM master_customer UNION ALL SELECT 'master_product', COUNT(*) FROM master_product UNION ALL SELECT 'sales_transactions', COUNT(*) FROM sales_transactions UNION ALL SELECT 'rejected_records', COUNT(*) FROM rejected_records;"
```

Expected counts for the current generated data are:

```text
master_customer      120
master_product         6
sales_transactions   500
rejected_records      17
```

## 7. If PostgreSQL is not needed

To run only the local CSV/report workflow, clear the database variable and run the pipeline:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
py run_pipeline.py
```

The processed CSVs remain available in `data/processed/`, and the scorecard and summary remain available in `reports/`.

## 8. Common problems

**`password authentication failed`** — Check the PostgreSQL password, username, database name, and port. The default local port is `5432`.

**`database medcore_mdm does not exist`** — Create it once in pgAdmin or run `CREATE DATABASE medcore_mdm;` while connected to the `postgres` database.

**`relation does not exist`** — Run `sql/schema.sql` once against the `medcore_mdm` database.

**`psycopg` or `sqlalchemy` is missing** — Run `py -m pip install -r requirements.txt`.

**`psql is not recognized`** — Use the full path shown above. PostgreSQL can work even when its `bin` folder is not on the Windows PATH.

**The terminal asks for a password twice** — One prompt is from `psql`; another may be from a separate verification command. This is normal.

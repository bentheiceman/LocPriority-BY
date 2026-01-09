# LOCPRIORITY Upload File Builder (GUI)

Windows desktop app to generate Blue Yonder LOCPRIORITY upload CSV files in chunks of **60,000 rows per file**.

## What it does
- Takes an input CSV (typically exported from your SQL query)
- Validates required columns: `item`, `loc`, `locpriority`
- Generates sequential output files with **≤ 60,000 data rows** each (header optional)

## Run (dev)
1. Create/activate a virtualenv (recommended)
2. Install deps:
   - `pip install -r requirements.txt`
3. Start the app:
   - `python -m app`

PowerShell note (paths with spaces):
- If you run Python by full path, use the call operator:
  - `& "C:\path\to\python.exe" -m app`

## How to use
1. Export your SQL results to a CSV with columns: `item`, `loc`, `locpriority`
2. In the app:
   - Select the input CSV
   - Select an output folder
   - Click **Generate upload files**
3. Upload the generated files manually into Blue Yonder.

Output files are named like `LOCPRIORITY_UPLOAD_001.csv`, `..._002.csv`, etc.
Each file contains **at most 60,000 data rows** (header row not counted).

## Packaging (optional)
This repo includes a build script that produces a **single, self-contained Windows executable** (no Python install required for end users).

Build:
- `powershell -ExecutionPolicy Bypass -File .\build_exe.ps1`

Output:
- `dist\HD_Supply_LOCPRIORITY_Builder.exe`

Distribute the `.exe` to the team and run it directly.

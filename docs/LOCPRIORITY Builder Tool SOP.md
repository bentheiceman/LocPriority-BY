# SOP: Using the HD Supply LOCPRIORITY Builder Tool

## Purpose
Use this tool to generate the Blue Yonder LOCPRIORITY upload CSV from Snowflake and (if needed) split it into **at most two files**.

## What you need
- The tool executable: `HD_Supply_LOCPRIORITY_Builder.exe`
- HD Supply SSO access to Snowflake (external browser authentication)
- Access to Blue Yonder Production for the manual upload

## Run the tool
1. Double-click `HD_Supply_LOCPRIORITY_Builder.exe`
2. In **Snowflake Authentication**:
   - Enter your HD Supply email (example: `first.last@hdsupply.com`)
   - Click **Authenticate**
   - Complete the browser sign-in (SSO)

## Generate the upload file(s)
1. In **Data Source**:
   - Leave **Pull data from Snowflake (recommended)** checked
   - Do not change the SQL unless instructed
2. In **Input / Output**:
   - Select an **Output folder** (where the CSV(s) will be saved)
   - Set **Base file name** (recommended: `LOCPRIORITY_UPLOAD`)
   - Leave **Include header row** checked
3. Click **Generate upload files**

## Output rules (important)
- If the query returns **≤ 60,000 rows**:
  - The tool writes **one file**: `BaseName.csv`
- If the query returns **> 60,000 rows**:
  - The tool writes **two files**:
    - `BaseName_001.csv` (first 60,000 rows)
    - `BaseName_002.csv` (remaining rows)
- If the query returns **> 120,000 rows**:
  - The tool stops with an error (it will not generate many small files)

## Upload into Blue Yonder
1. Open **LOCPRIORITY Upload** in **Blue Yonder Production**
2. Select **More Actions** → **Import**
3. Select the generated CSV file(s)
   - If you have 2 files, upload `_001` first, then `_002`
4. Check:
   - **Skip First Row**
   - **Update Existing Records**
5. Press **Done** to run the upload

## Troubleshooting
- Authentication fails:
  - Re-try **Authenticate** and complete the browser sign-in
  - Confirm you entered your correct HD Supply email
- Output folder is empty:
  - Confirm you clicked **Generate upload files** and selected an output folder
- “Result exceeds 120,000 rows”:
  - Contact the IPR team to confirm the query scope and expected volume

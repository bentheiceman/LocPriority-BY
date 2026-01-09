# Weekly LOCPRIORITY Upload SOP (Blue Yonder)

## Purpose
Maintain the `LOCPRIORITY` field in `SKUDEPLOYMENTPARAM` via a weekly upload. This ensures locations are prioritized correctly for transfers when inventory is constrained.

## Schedule / Timing
- Run **each Monday after 9:00 AM** (local business time).
- The underlying table used for the upload is populated by a scheduled procedure (see **Scheduled Procedure & Task** below).

## Step-by-step

### 1) Run the SQL to identify changes
Run the following query:

```sql
select distinct item,loc, locpriority
from dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD 
inner join (
    select distinct item,loc,locpriority as old_locpriority
    from dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD
    where upload_dt in (
        select top 2 upload_dt
        from dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD
    )
) using (item,loc)
where upload_dt=current_date()
and locpriority<>old_locpriority;
```

Expected result:
- Returns only `item`/`loc` pairs where today’s `locpriority` differs from the prior snapshot within the most recent two `upload_dt` values.

### 2) Export results to CSV
- Export the query results into a `.csv`.
- Ensure the CSV contains exactly these columns (in order):
  - `item`
  - `loc`
  - `locpriority`

### 3) Open the LOCPRIORITY Upload page in Blue Yonder Production
- Navigate to **LOCPRIORITY Upload** in **Blue Yonder Production**.

### 4) Import the CSV
- Select **More Actions** → **Import**.
- Choose the CSV file exported in Step 2.

### 5) Set import options and run
- Check:
  - **Skip First Row**
  - **Update Existing Records**
- Press **Done** to run the upload.

## Post-upload validation (recommended)
- Confirm the import completed successfully (no failed rows).
- If the page provides import status/results, verify counts align with the number of CSV rows.

## Scheduled Procedure & Task (reference)
The tables referenced in the query above are created via a scheduled weekly procedure.

### View definition
```sql
create or replace view dm_supplychain.IPR_STRATEGY.v_LOCPRIORITY_UPLOAD as (
select item, loc, 
case when udc_source_3 is not null and udc_source_3<>udc_ultimate_source then '4'
when udc_source_3 is not null then '3'
when udc_source_2 is not null then '2'
else '1' end as locpriority, current_date() as upload_dt
from edp.std_jda.skuextract
where udc_source_1 is not null
)
;
```

### Procedure
```sql
CREATE OR REPLACE PROCEDURE DM_SUPPLYCHAIN.IPR_STRATEGY.LOCPRIORITY_UPLOAD_PROC()
RETURNS VARCHAR(16777216)
LANGUAGE SQL
EXECUTE AS CALLER
AS ' BEGIN
DELETE FROM dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD
	WHERE upload_dt=current_date();

INSERT INTO dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD (
select * from dm_supplychain.IPR_STRATEGY.v_LOCPRIORITY_UPLOAD
);
END '
;
--CALL dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD_PROC()
;
```

### Task
```sql
create or replace task dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD_TASK
	warehouse=SUPPLYCHAIN_WH1
	schedule='USING CRON 45 8 * * MON  America/New_York'
	as CALL dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD_PROC()
;

ALTER TASK dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD_TASK RESUME
;
```

## Notes
- The scheduled task runs at **08:45 AM America/New_York** each Monday.
- The manual upload should occur after the scheduled data refresh is available (per the timing guidance above).

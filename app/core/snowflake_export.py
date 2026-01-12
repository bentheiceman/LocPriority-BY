from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

from app.core.csv_chunker import REQUIRED_COLUMNS, CsvChunkerError, _safe_base_name  # noqa: PLC2701


DEFAULT_QUERY = """select distinct item,loc, locpriority
from dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD
inner join (
    select distinct item,loc,locpriority as old_locpriority
    from dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD where
        upload_dt in (select top 2 upload_dt from dm_supplychain.IPR_STRATEGY.LOCPRIORITY_UPLOAD)
) using (item,loc)
where upload_dt=current_date()
and locpriority<>old_locpriority
"""


class SnowflakeExportError(RuntimeError):
    pass


def export_query_to_chunked_csv(
    *,
    email: str,
    query: str,
    output_dir: str,
    base_name: str,
    max_rows: int = 60000,
    include_header: bool = True,
    insecure_mode: bool = True,
    account: str = "HDSUPPLY-DATA",
    authenticator: str = "externalbrowser",
    on_log: Callable[[str], None] | None = None,
) -> dict:
    """Run a Snowflake query and stream-write chunked CSV files.

    This avoids client-side export limits by fetching all rows via the connector.
    Each output file contains at most `max_rows` *data* rows (header not counted).
    """

    email = (email or "").strip()
    if not email or "@" not in email:
        raise SnowflakeExportError("Enter a valid HD Supply email address (e.g., name@hdsupply.com).")

    query = (query or "").strip()
    if not query:
        raise SnowflakeExportError("Query is empty.")

    if max_rows != 60000:
        raise SnowflakeExportError("This tool enforces 60,000 rows max per file.")

    # Interpretation: 60,000 is the maximum number of DATA rows per file.
    # Header (when enabled) does not count toward the limit.
    max_data_rows = 60000

    out_dir = Path(output_dir)
    if not out_dir.exists():
        raise SnowflakeExportError(f"Output folder not found: {output_dir}")

    base_name = _safe_base_name(base_name)

    def log(msg: str) -> None:
        if on_log:
            on_log(msg)

    try:
        import snowflake.connector as sc  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise SnowflakeExportError("Snowflake connector is not available.") from exc

    con = None
    cur = None
    try:
        log("Connecting to Snowflake (external browser SSO)…")
        con = sc.connect(
            user=email,
            account=account,
            authenticator=authenticator,
            insecure_mode=bool(insecure_mode),
        )
        cur = con.cursor()

        log("Running query…")
        cur.execute(query)

        if not cur.description:
            raise SnowflakeExportError("Query returned no columns.")

        columns = [d[0] for d in cur.description]
        # Normalize for validation
        normalized = {c.lower(): c for c in columns}
        missing = [c for c in REQUIRED_COLUMNS if c not in normalized]
        if missing:
            raise SnowflakeExportError(
                "Query result is missing required column(s): "
                + ", ".join(missing)
                + ". Required: item, loc, locpriority."
            )

        # Force output header order to match required columns first, then the rest
        ordered_cols = [normalized["item"], normalized["loc"], normalized["locpriority"]]
        for c in columns:
            if c not in ordered_cols:
                ordered_cols.append(c)

        def first_path() -> Path:
            return out_dir / f"{base_name}.csv"

        def part_path(part_index: int) -> Path:
            return out_dir / f"{base_name}_{part_index:03d}.csv"

        files_written = 0
        rows_written = 0
        rows_in_part = 0

        out_fp = None
        writer = None

        def open_first() -> Path:
            nonlocal out_fp, writer, files_written, rows_in_part
            p = first_path()
            out_fp = p.open("w", newline="", encoding="utf-8")
            writer = csv.writer(out_fp)
            files_written = 1
            rows_in_part = 0
            if include_header:
                writer.writerow(ordered_cols)
            log(f"Writing: {p.name}")
            return p

        def rollover_to_second(first_file: Path) -> None:
            nonlocal out_fp, writer, files_written, rows_in_part
            if out_fp:
                out_fp.close()

            first_renamed = part_path(1)
            try:
                first_file.replace(first_renamed)
            except OSError as exc:
                raise SnowflakeExportError(f"Failed to rename output file: {exc}") from exc

            p = part_path(2)
            out_fp = p.open("w", newline="", encoding="utf-8")
            writer = csv.writer(out_fp)
            files_written = 2
            rows_in_part = 0
            if include_header:
                writer.writerow(ordered_cols)
            log(f"Writing: {p.name}")

        first_file = open_first()

        # Stream rows in batches
        cur.arraysize = 10000
        while True:
            batch = cur.fetchmany(cur.arraysize)
            if not batch:
                break

            for row in batch:
                if rows_in_part >= max_data_rows:
                    if files_written == 1:
                        rollover_to_second(first_file)
                    else:
                        raise SnowflakeExportError(
                            "Result exceeds 120,000 rows. This tool only outputs 1 file (<=60,000) "
                            "or 2 files (<=120,000 total)."
                        )

                # Row is a tuple in column order `columns`.
                row_map = dict(zip(columns, row))
                # `writer` is initialized by open_first() and may be re-initialized by rollover.
                writer.writerow([row_map.get(c) for c in ordered_cols])
                rows_in_part += 1
                rows_written += 1

        # If there were zero rows, remove the empty first file
        if rows_written == 0:
            first = first_path()
            try:
                first.unlink(missing_ok=True)  # py3.8+ supports missing_ok
            except TypeError:
                if first.exists():
                    first.unlink()
            files_written = 0

        return {
            "files_written": files_written,
            "rows_written": rows_written,
            "base_name": base_name,
            "max_rows": max_rows,
            "include_header": include_header,
        }

    except CsvChunkerError as exc:
        raise SnowflakeExportError(str(exc)) from exc
    finally:
        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass
        try:
            if con is not None:
                con.close()
        except Exception:
            pass

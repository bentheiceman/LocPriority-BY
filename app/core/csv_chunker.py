from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, Iterable


REQUIRED_COLUMNS = ("item", "loc", "locpriority")


class CsvChunkerError(RuntimeError):
    pass


def _normalize_fieldnames(fieldnames: Iterable[str] | None) -> list[str]:
    if not fieldnames:
        return []
    return [str(f).strip() for f in fieldnames]


def _validate_required_columns(fieldnames: list[str]) -> None:
    normalized = {f.lower(): f for f in fieldnames}
    missing = [c for c in REQUIRED_COLUMNS if c not in normalized]
    if missing:
        raise CsvChunkerError(
            "Input CSV is missing required column(s): "
            + ", ".join(missing)
            + ". Required: item, loc, locpriority."
        )


def _safe_base_name(name: str) -> str:
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_"))
    return cleaned or "LOCPRIORITY_UPLOAD"


def _part_path(output_dir: str, base_name: str, part_index: int) -> Path:
    return Path(output_dir) / f"{base_name}_{part_index:03d}.csv"


def chunk_csv(
    *,
    input_csv: str,
    output_dir: str,
    base_name: str,
    max_rows: int = 60000,
    include_header: bool = True,
    validate_required_columns: bool = True,
    on_progress: Callable[[int], None] | None = None,
    on_log: Callable[[str], None] | None = None,
) -> dict:
    """Chunk a CSV into sequential files of at most `max_rows` data rows.

    - Counts *data* rows only (header not counted).
    - Writes files named: <base_name>_001.csv, <base_name>_002.csv, ...
    """

    if max_rows != 60000:
        raise CsvChunkerError("This tool enforces 60,000 rows max per file.")

    # Interpretation: 60,000 is the maximum number of DATA rows per file.
    # If header is included, it does not count toward the limit.
    max_data_rows = 60000

    input_path = Path(input_csv)
    if not input_path.exists():
        raise CsvChunkerError(f"Input file not found: {input_csv}")

    output_path = Path(output_dir)
    if not output_path.exists():
        raise CsvChunkerError(f"Output folder not found: {output_dir}")

    base_name = _safe_base_name(base_name)

    def log(msg: str) -> None:
        if on_log:
            on_log(msg)

    def progress(pct: int) -> None:
        if on_progress:
            on_progress(max(0, min(100, int(pct))))

    files_written = 0
    rows_written = 0

    # Output naming:
    # - If total rows <= 60,000: <base>.csv
    # - If > 60,000: rename first to <base>_001.csv and create <base>_002.csv
    current_part_index = 0
    current_part_rows = 0
    out_fp = None
    out_writer = None

    try:
        progress(0)
        with input_path.open("r", newline="", encoding="utf-8-sig") as in_fp:
            reader = csv.DictReader(in_fp)
            fieldnames = _normalize_fieldnames(reader.fieldnames)

            if validate_required_columns:
                _validate_required_columns(fieldnames)

            if not fieldnames:
                raise CsvChunkerError("Input CSV appears to have no header/columns.")

            def open_first_file() -> Path:
                nonlocal out_fp, out_writer, files_written, current_part_rows
                out_file = Path(output_dir) / f"{base_name}.csv"
                out_fp = out_file.open("w", newline="", encoding="utf-8")
                out_writer = csv.DictWriter(out_fp, fieldnames=fieldnames, extrasaction="ignore")
                files_written = 1
                current_part_rows = 0
                if include_header:
                    out_writer.writeheader()
                log(f"Writing: {out_file.name}")
                return out_file

            def rollover_to_second_file(first_path: Path) -> None:
                nonlocal out_fp, out_writer, files_written, current_part_rows, current_part_index

                # Close first file so we can rename on Windows.
                if out_fp:
                    out_fp.close()

                first_renamed = _part_path(output_dir, base_name, 1)
                # Rename <base>.csv -> <base>_001.csv
                try:
                    first_path.replace(first_renamed)
                except OSError as exc:
                    raise CsvChunkerError(f"Failed to rename output file: {exc}") from exc

                out_file = _part_path(output_dir, base_name, 2)
                out_fp = out_file.open("w", newline="", encoding="utf-8")
                out_writer = csv.DictWriter(out_fp, fieldnames=fieldnames, extrasaction="ignore")
                files_written = 2
                current_part_rows = 0
                current_part_index = 2

                if include_header:
                    out_writer.writeheader()

                log(f"Writing: {out_file.name}")

            first_path = open_first_file()

            for row in reader:
                if current_part_rows >= max_data_rows:
                    if files_written == 1:
                        rollover_to_second_file(first_path)
                    else:
                        raise CsvChunkerError(
                            "Result exceeds 120,000 rows. This tool only outputs 1 file (<=60,000) "
                            "or 2 files (<=120,000 total)."
                        )

                out_writer.writerow(row)
                current_part_rows += 1
                rows_written += 1

            progress(100)

    finally:
        if out_fp:
            out_fp.close()

    # If input had only headers and no data rows, delete the empty output file.
    if rows_written == 0:
        first = Path(output_dir) / f"{base_name}.csv"
        if first.exists():
            try:
                first.unlink()
            except OSError:
                pass
        files_written = 0

    return {
        "files_written": files_written,
        "rows_written": rows_written,
        "base_name": base_name,
        "max_rows": max_rows,
        "include_header": include_header,
    }

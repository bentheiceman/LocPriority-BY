from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

# Allow running as: `python tools/selftest.py`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.csv_chunker import chunk_csv


def count_data_rows(path: Path) -> int:
    with path.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.reader(fp)
        header = next(reader, None)
        if header is None:
            return 0
        return sum(1 for _ in reader)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        input_csv = td_path / "in.csv"
        out_dir = td_path / "out"
        out_dir.mkdir(parents=True, exist_ok=True)

        # 120,005 data rows -> 3 output files when max_rows=60,000
        with input_csv.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            writer.writerow(["item", "loc", "locpriority"])
            for i in range(1, 120_006):
                writer.writerow([f"SKU{i}", f"LOC{i%10}", str(i % 4 + 1)])

        res = chunk_csv(
            input_csv=str(input_csv),
            output_dir=str(out_dir),
            base_name="TEST",
            max_rows=60_000,
            include_header=True,
            validate_required_columns=True,
        )

        parts = sorted(out_dir.glob("TEST_*.csv"))
        print(res)
        print([p.name for p in parts])

        if len(parts) != 3:
            raise SystemExit(f"Expected 3 files, got {len(parts)}")

        counts = [count_data_rows(p) for p in parts]
        print("row-counts:", counts)

        if counts != [60_000, 60_000, 5]:
            raise SystemExit(f"Unexpected row counts: {counts}")

        print("selftest-ok")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

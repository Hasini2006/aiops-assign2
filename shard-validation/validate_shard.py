"""
validate_shard.py -- AIOps, Module 3, Question 3
Entry point for each pod of the Kubernetes Indexed Job. Reads
JOB_COMPLETION_INDEX (set automatically by Kubernetes for Indexed Jobs) to
pick ONE of the 8 pre-generated shard CSVs baked into this image, validates
every row, and reports the invalid count as a single RESULT_JSON line.
"""

import csv
import json
import os
import re
import sys
import traceback

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid(row: dict) -> bool:
    if not row["name"].strip():
        return False
    if not EMAIL_RE.match(row["email"]):
        return False
    return True


def main() -> None:
    index = int(os.environ["JOB_COMPLETION_INDEX"])
    pod_name = os.environ.get("POD_NAME", "unknown-pod")
    node_name = os.environ.get("NODE_NAME", "unknown-node")
    data_dir = os.environ.get("DATA_DIR", "/app/data")

    # Printed FIRST, before anything else, so a log with only this line and
    # nothing after it tells us the process started but died before
    # finishing -- as opposed to a log with nothing at all in it.
    print(f"[validate_shard] starting: index={index} pod={pod_name} node={node_name} data_dir={data_dir}", flush=True)

    shard_path = os.path.join(data_dir, f"shard_{index}.csv")
    with open(shard_path, newline="") as f:
        rows = list(csv.DictReader(f))

    invalid_rows = sum(1 for row in rows if not is_valid(row))

    result = {
        "shard_index": index,
        "pod_name": pod_name,
        "node_name": node_name,
        "total_rows": len(rows),
        "invalid_rows": invalid_rows,
    }
    print("RESULT_JSON:" + json.dumps(result), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("[validate_shard] FAILED with an exception:", file=sys.stderr, flush=True)
        traceback.print_exc()
        sys.exit(1)
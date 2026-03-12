#!/usr/bin/env python3
"""Aggregate per-reading JSON files into a single data.json for the web dashboard.

Each Enviro device stores readings as individual timestamped JSON files inside
a directory named ``{nickname}-{uid}/``.  This script scans for those
directories, reads every JSON file in sorted (chronological) order, and writes
a combined ``data.json`` keyed by device nickname.

Usage:
    python3 build_data.py [--dir DATA_DIR] [--out OUTPUT]

If --dir is omitted the script looks in its own directory.  The default output
file is ``data.json`` in the same location.
"""

import argparse
import glob
import json
import os
import sys


# Device directories follow the naming convention: {nickname}-{uid}/
DEVICE_DIR_PATTERN = "*-*-*/"


def find_device_dirs(base: str) -> list[str]:
    """Return sorted list of device directories under *base*."""
    return sorted(glob.glob(os.path.join(base, DEVICE_DIR_PATTERN)))


def load_readings(device_dir: str) -> list[dict]:
    """Load and return all JSON readings from *device_dir*, sorted by filename."""
    readings = []
    for path in sorted(glob.glob(os.path.join(device_dir, "*.json"))):
        with open(path) as fh:
            readings.append(json.load(fh))
    return readings


def build_data(base: str) -> dict[str, list[dict]]:
    """Scan *base* for device directories and return aggregated readings."""
    data: dict[str, list[dict]] = {}
    for device_dir in find_device_dirs(base):
        readings = load_readings(device_dir)
        if readings:
            nickname = readings[0]["nickname"]
            data[nickname] = readings
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate Enviro sensor JSON files into a single data.json."
    )
    parser.add_argument(
        "--dir",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Directory containing device reading folders (default: script directory)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output file path (default: data.json in --dir)",
    )
    args = parser.parse_args()

    base = args.dir
    out = args.out or os.path.join(base, "data.json")

    data = build_data(base)
    if not data:
        print("No device directories found.", file=sys.stderr)
        sys.exit(1)

    with open(out, "w") as f:
        json.dump(data, f)

    print(f"Wrote {out}")
    for nickname, readings in data.items():
        print(f"  {nickname}: {len(readings)} readings")


if __name__ == "__main__":
    main()

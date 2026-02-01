#!/usr/bin/env python3
"""
PolyBench/C Automated Build Script
Compiles all benchmarks in datamining, linear-algebra, medley, and stencils directories.
"""

import argparse
import json
import os
import shlex
import statistics
import subprocess
import sys
import time
from pathlib import Path

# Configuration
BIN_DIR = "bin"

def run_binary(bin_path: Path):
    print(f"running {bin_path}")
    start = time.time()
    result = subprocess.run(bin_path, text=True, capture_output=True, timeout=1800)
    end = time.time()
    print(f"ran {bin_path}, took: {end - start} seconds")
    assert result.returncode == 0, f"result: {result.stdout}\n{result.stderr}"
    return float(result.stdout)

    # runtimes = []
    # for _ in range(100):
    #     result = subprocess.run(bin_path, text=True, capture_output=True)
    #     assert result.returncode == 0, f"result: {result.stdout}\n{result.stderr}"
    #     runtimes.append(float(result.stdout))

    # return statistics.median(runtimes)

def run_all_binaries(output: str):
    bench_result = {}
    for fname in os.listdir(BIN_DIR):
        if "cholesky" in fname or "seidel-2d" in fname:
            continue
        runtime = run_binary(Path(BIN_DIR) / fname)
        bench_result[fname] = runtime

    with open(output, "w") as f:
        json.dump(bench_result, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure performance of test scripts.")
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="output path",
    )
    args = parser.parse_args()
    run_all_binaries(args.output)

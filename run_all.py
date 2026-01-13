#!/usr/bin/env python3
"""
PolyBench/C Automated Build Script
Compiles all benchmarks in datamining, linear-algebra, medley, and stencils directories.
"""

import os
import subprocess
import sys
from pathlib import Path

# Configuration
BIN_DIR = "bin"

def run_binary(bin_path: Path):
    print(f"running binary: {bin_path}")
    result = subprocess.run(bin_path, text=True)
    assert result.returncode == 0, f"result: {result}"

def run_all_binaries():
    for fname in os.listdir(BIN_DIR):
        run_binary(Path(BIN_DIR) / fname)

if __name__ == "__main__":
    run_all_binaries()

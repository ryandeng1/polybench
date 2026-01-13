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
ROOT_DIR = Path(__file__).parent.absolute()
UTILITIES_DIR = ROOT_DIR / "utilities"
POLYBENCH_C = UTILITIES_DIR / "polybench.c"

# Target directories
TARGET_DIRS = [
    ROOT_DIR / "datamining",
    ROOT_DIR / "linear-algebra",
    ROOT_DIR / "medley",
    ROOT_DIR / "stencils"
]

# Compilation settings
CC = os.path.expanduser("~/data_race_analysis/build/bin/clang++")
CFLAGS = ["-O3", "-fopencilk", "-march=native", "-fsanitize=cilk", "-g"]
DEFINES = ["-DPOLYBENCH_TIME"]
LDFLAGS = ["-lm"]  # Math library for functions like sqrt

# Output directory for compiled binaries
OUTPUT_DIR = ROOT_DIR / "bin"


def find_benchmarks():
    """Find all benchmark C files in target directories."""
    benchmarks = []

    for target_dir in TARGET_DIRS:
        if not target_dir.exists():
            print(f"Warning: Directory {target_dir} does not exist, skipping...")
            continue

        # Find all .c files, excluding backup/original files
        for c_file in target_dir.rglob("*.c"):
            # Skip files with .orig or backup in name
            if ".orig" in c_file.name.lower() or "backup" in c_file.name.lower():
                continue

            benchmarks.append(c_file)

    return sorted(benchmarks)


def compile_benchmark(benchmark_path):
    """
    Compile a single benchmark.

    Args:
        benchmark_path: Path to the benchmark .c file

    Returns:
        Tuple of (success: bool, output_file: Path, error_msg: str)
    """
    # Get benchmark name and directory
    benchmark_name = benchmark_path.stem
    benchmark_dir = benchmark_path.parent

    # Output filename
    output_name = f"{benchmark_name}_time"
    output_path = OUTPUT_DIR / output_name

    # Build compile command
    cmd = [
        CC,
        *CFLAGS,
        f"-I{UTILITIES_DIR}",
        f"-I{benchmark_dir}",
        str(POLYBENCH_C),
        str(benchmark_path),
        *DEFINES,
        *LDFLAGS,
        "-o", str(output_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        if result.returncode != 0:
            assert False, f"error compiling: {result.stdout}\n{result.stderr}"
        return output_path
    except Exception as e:
        print(f"exception: {e}")
        raise e

def main():
    """Main build function."""
    print("=" * 70)
    print("PolyBench/C Automated Build Script")
    print("=" * 70)
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Find all benchmarks
    print("Scanning for benchmarks...")
    benchmarks = find_benchmarks()
    print(f"Found {len(benchmarks)} benchmarks")
    print()

    # Compile each benchmark
    print("Starting compilation...")
    print("-" * 70)

    results = {
        "success": [],
        "failed": []
    }

    for i, benchmark in enumerate(benchmarks, 1):
        # Get relative path for display
        rel_path = benchmark.relative_to(ROOT_DIR)

        print(f"[{i}/{len(benchmarks)}] Compiling {rel_path}...", end=" ", flush=True)

        output_path = compile_benchmark(benchmark)

        print("✓")
        results["success"].append((rel_path, output_path))

    # Print summary
    print("-" * 70)
    print()
    print("=" * 70)
    print("Build Summary")
    print("=" * 70)
    print(f"Total benchmarks: {len(benchmarks)}")
    print(f"Successful: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")
    print()

    if results["failed"]:
        print("Failed benchmarks:")
        for benchmark, error in results["failed"]:
            print(f"  - {benchmark}")
            if error and "-v" in sys.argv or "--verbose" in sys.argv:
                print(f"    Error: {error[:200]}...")
        print()

    if results["success"]:
        print(f"Compiled binaries are in: {OUTPUT_DIR}")
        print()

    # Exit with appropriate code
    sys.exit(0 if not results["failed"] else 1)


if __name__ == "__main__":
    main()

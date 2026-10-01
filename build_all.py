#!/usr/bin/env python3
"""
PolyBench/C Automated Build Script
Compiles all benchmarks in datamining, linear-algebra, medley, and stencils directories.
"""

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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
DEFAULT_DATASET_SIZE = "EXTRALARGE_DATASET"
CC = os.path.expanduser("~/opencilk_build/build/bin/clang++")
# CFLAGS = ["-O3", "-fopencilk", "-march=native"]
# CFLAGS = ["-O3", "-fopencilk", "-ftapir=serial", "-g"]
CFLAGS = ["-O3", "-fopencilk", "-g", "-fno-exceptions", "-mllvm", "-enable-unroll-and-jam", "-march=native", "-ftapir=serial"]
# CFLAGS = ["-O3", "-fopencilk", "-g", "-fno-exceptions", "-march=native"]
# CFLAGS = ["-O3", "-fopencilk", "-mllvm", "-enable-loop-versioning-licm", "-mllvm", "-licm-versioning-max-depth-threshold=3"]
# DEFINES = ["-DBENCHMARK", "-DPOLYBENCH_NO_FLUSH_CACHE", "-DPOLYBENCH_USE_RESTRICT"]
DEFINES = ["-DBENCHMARK", "-DPOLYBENCH_NO_FLUSH_CACHE"]
# DEFINES = ["-DBENCHMARK", "-DPOLYBENCH_NO_FLUSH_CACHE"]
# DEFINES = ["-DPOLYBENCH_TIME"]
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


def parse_requested_benchmarks(requested_args):
    if not requested_args:
        return None

    requested = []
    for requested_arg in requested_args:
        for benchmark_name in requested_arg.split(","):
            benchmark_name = benchmark_name.strip()
            if benchmark_name:
                requested.append(benchmark_name)

    return requested


def filter_benchmarks(benchmarks, requested):
    if requested is None:
        return benchmarks

    matched = [
        benchmark for benchmark in benchmarks
        if any(name in benchmark.stem for name in requested)
    ]
    missing = [
        name for name in requested
        if not any(name in benchmark.stem for benchmark in benchmarks)
    ]
    if missing:
        raise ValueError(f"No benchmark matching: {', '.join(missing)}")

    return matched


def compile_benchmark(benchmark_path, dataset_size: str, use_drfaa: bool):
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

    # drfaa_flag = ["-mllvm", "-enable-drf-aa"] if use_drfaa else []
    # drfaa_flag = ["-mllvm", "-enable-drf-aa", "-mllvm", "-enable-drf-aa-delta-set-proof", "-mllvm", "-enable-drf-laa-check-elision"] if use_drfaa else []
    # drfaa_flag = ["-mllvm", "-enable-drf-aa", "-mllvm", "-enable-drf-aa-presburger-delta-set-proof", "-mllvm", "-enable-drf-aa-delta-set-proof", "-mllvm", "-enable-drf-laa-check-elision", "-mllvm", "-enable-drf-aa-hyper-view"] if use_drfaa else []
    # drfaa_flag = ["-mllvm", "-enable-drf-aa", "-mllvm", "-enable-drf-aa-presburger-delta-set-proof", "-mllvm", "-enable-drf-aa-delta-set-proof", "-mllvm", "-enable-drf-laa", "-mllvm", "-enable-drf-laa-check-elision", "-mllvm", "-enable-drf-aa-hyper-view", "-mllvm", "-enable-drf-loop-optimizations", "-fhyperobject-associative-math", "-mllvm", "-drf-aa-presburger-delta-set-max-loop-vars=1"] if use_drfaa else []
    drfaa_flag = ["-mllvm", "-enable-drf-aa", "-mllvm", "-enable-drf-aa-presburger-delta-set-proof", "-mllvm", "-enable-drf-aa-delta-set-proof", "-mllvm", "-enable-drf-laa", "-mllvm", "-enable-drf-laa-check-elision", "-mllvm", "-enable-drf-aa-hyper-view", "-mllvm", "-drf-aa-presburger-delta-set-max-loop-vars=1", "-mllvm", "-enable-drf-memoryssa", "-mllvm", "-enable-drf-loop-optimizations"] if use_drfaa else []

    # Build compile command
    cmd = [
        CC,
        *CFLAGS,
        *drfaa_flag,
        f"-I{UTILITIES_DIR}",
        f"-I{benchmark_dir}",
        str(POLYBENCH_C),
        str(benchmark_path),
        *DEFINES,
        f"-D{dataset_size}",
        *LDFLAGS,
        "-o", str(output_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            # check=True
        )
        if result.returncode != 0:
            assert False, f"error compiling: {result.stdout}\n{result.stderr}"
        return output_path
    except Exception as e:
        print(f"exception: {e}")
        raise e


def compile_benchmarks_parallel(
    benchmarks, dataset_size: str, use_drfaa: bool, jobs: int
):
    """Compile independent benchmarks concurrently using worker threads."""
    results = {
        "success": [],
        "failed": []
    }
    total = len(benchmarks)

    print(f"Using {jobs} parallel compiler jobs")

    with ThreadPoolExecutor(
        max_workers=jobs,
        thread_name_prefix="polybench-compile",
    ) as executor:
        futures = {}
        for i, benchmark in enumerate(benchmarks, 1):
            future = executor.submit(
                compile_benchmark,
                benchmark,
                dataset_size,
                use_drfaa,
            )
            futures[future] = (i, benchmark)

        for future in as_completed(futures):
            i, benchmark = futures[future]
            rel_path = benchmark.relative_to(ROOT_DIR)
            try:
                output_path = future.result()
            except Exception as error:
                print(
                    f"[{i}/{total}] Compiling {rel_path}... ✗",
                    flush=True,
                )
                results["failed"].append((rel_path, str(error)))
            else:
                print(
                    f"[{i}/{total}] Compiling {rel_path}... ✓",
                    flush=True,
                )
                results["success"].append((rel_path, output_path))

    results["success"].sort(key=lambda result: result[0])
    results["failed"].sort(key=lambda result: result[0])
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Test PolyBench/C benchmarks by comparing optimized vs reference outputs"
    )
    parser.add_argument(
        "-d", "--dataset",
        required=True,
        choices=["MINI_DATASET", "SMALL_DATASET", "MEDIUM_DATASET",
                 "LARGE_DATASET", "EXTRALARGE_DATASET"],
        help=f"Dataset size to use (default: {DEFAULT_DATASET_SIZE})"
    )
    parser.add_argument(
        "--drfaa",
        action="store_true",
        help=f"whether or not to use drfaa"
    )
    parser.add_argument(
        "-b", "--benchmark",
        action="append",
        help=(
            "Compile only matching benchmark name(s); can be repeated and can "
            "include comma-separated names, e.g. -b doitgen or -b atax,bicg"
        )
    )
    parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=1,
        metavar="N",
        help=(
            "Number of benchmarks to compile concurrently; 1 uses the "
            "original single-threaded build path (default: 1)"
        ),
    )
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")

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
    requested_benchmarks = parse_requested_benchmarks(args.benchmark)
    try:
        benchmarks = filter_benchmarks(benchmarks, requested_benchmarks)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    print(f"Found {len(benchmarks)} benchmarks")
    print()

    # Compile each benchmark
    print("Starting compilation...")
    print("-" * 70)

    if args.jobs == 1:
        results = {
            "success": [],
            "failed": []
        }

        for i, benchmark in enumerate(benchmarks, 1):
            # Get relative path for display
            rel_path = benchmark.relative_to(ROOT_DIR)

            print(f"[{i}/{len(benchmarks)}] Compiling {rel_path}...", end=" ", flush=True)

            output_path = compile_benchmark(benchmark, args.dataset, args.drfaa)

            print("✓")
            results["success"].append((rel_path, output_path))
    else:
        results = compile_benchmarks_parallel(
            benchmarks,
            args.dataset,
            args.drfaa,
            args.jobs,
        )

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

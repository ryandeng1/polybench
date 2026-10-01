#!/usr/bin/env python3
"""
PolyBench/C Automated Testing Script
Compares outputs of optimized benchmarks against reference implementations.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
import argparse

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

# Compiler settings
CC = os.path.expanduser("~/opencilk_build/build/bin/clang++")  # Optimized compiler

# Reference compilation flags (no optimizations for correctness)
CFLAGS_REF = ["-O3", "-fopencilk", "-fno-exceptions"]
# Optimized compilation flags
# CFLAGS_OPT = ["-O3", "-fopencilk", "-mllvm", "-enable-drf-aa", "-mllvm", "-enable-drf-aa-delta-set-proof", "-mllvm", "-enable-drf-equality-versioning"]
CFLAGS_OPT = ["-O3", "-fopencilk", "-fno-exceptions", "-mllvm", "-enable-drf-aa", "-mllvm", "-enable-drf-laa", "-mllvm", "-enable-drf-laa-check-elision", "-mllvm", "-enable-drf-aa-delta-set-proof", "-mllvm", "-enable-drf-aa-presburger-delta-set-proof"]
# CFLAGS_OPT = ["-O3", "-fopencilk", "-ftapir=serial"]

# Common flags
DEFINES = ["-DPOLYBENCH_DUMP_ARRAYS", "-DUSE_REDUCER"]
LDFLAGS = ["-lm"]

# Default dataset size (use MINI for faster testing)
DEFAULT_DATASET = "LARGE_DATASET"


def find_benchmarks():
    """Find all benchmark C files in target directories."""
    benchmarks = []

    for target_dir in TARGET_DIRS:
        if not target_dir.exists():
            continue

        for c_file in target_dir.rglob("*.c"):
            if ".orig" in c_file.name.lower() or "backup" in c_file.name.lower():
                continue
            benchmarks.append(c_file)

    return sorted(benchmarks)


def compile_benchmark(benchmark_path, output_path, cc, cflags, dataset):
    """
    Compile a single benchmark.

    Args:
        benchmark_path: Path to the benchmark .c file
        output_path: Path for the output binary
        cc: Compiler to use
        cflags: Compiler flags
        dataset: Dataset size define (e.g., MINI_DATASET)

    Returns:
        True if compilation succeeded, False otherwise
    """
    benchmark_dir = benchmark_path.parent

    cmd = [
        cc,
        *cflags,
        f"-I{UTILITIES_DIR}",
        f"-I{benchmark_dir}",
        str(POLYBENCH_C),
        str(benchmark_path),
        *DEFINES,
        f"-D{dataset}",
        *LDFLAGS,
        "-o", str(output_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0, result.stderr
    except Exception as e:
        raise e

def run_benchmark(binary_path, timeout=500):
    """
    Run a benchmark and capture its output.

    Args:
        binary_path: Path to the compiled binary
        timeout: Maximum execution time in seconds

    Returns:
        Tuple of (success: bool, stderr_output: str, error_msg: str)
    """
    try:
        result = subprocess.run(
            [str(binary_path)],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        # POLYBENCH_DUMP_ARRAYS outputs to stderr
        return True, result.stderr, ""
    except subprocess.TimeoutExpired:
        return False, "", "Execution timed out"
    except Exception as e:
        return False, "", str(e)


def compare_outputs(ref_output, opt_output, tolerance=1e-6):
    """
    Compare reference and optimized outputs.

    Args:
        ref_output: Reference output string
        opt_output: Optimized output string
        tolerance: Floating point comparison tolerance

    Returns:
        Tuple of (match: bool, diff_info: str)
    """
    ref_lines = ref_output.strip().split('\n')
    opt_lines = opt_output.strip().split('\n')

    if len(ref_lines) != len(opt_lines):
        return False, f"Line count mismatch: ref={len(ref_lines)}, opt={len(opt_lines)}"

    for i, (ref_line, opt_line) in enumerate(zip(ref_lines, opt_lines)):
        if ref_line == opt_line:
            continue

        # Try numerical comparison
        ref_values = ref_line.split()
        opt_values = opt_line.split()

        if len(ref_values) != len(opt_values):
            return False, f"Line {i+1}: value count mismatch"

        for j, (ref_val, opt_val) in enumerate(zip(ref_values, opt_values)):
            try:
                ref_num = float(ref_val)
                opt_num = float(opt_val)
                if abs(ref_num - opt_num) > tolerance * max(abs(ref_num), 1.0):
                    return False, f"Line {i+1}, value {j+1}: {ref_num} != {opt_num}"
            except ValueError:
                if ref_val != opt_val:
                    return False, f"Line {i+1}: '{ref_val}' != '{opt_val}'"

    return True, ""


def test_benchmark(benchmark_path, temp_dir, dataset, verbose=False):
    """
    Test a single benchmark by comparing reference and optimized outputs.

    Args:
        benchmark_path: Path to the benchmark .c file
        temp_dir: Temporary directory for binaries
        dataset: Dataset size to use
        verbose: Print detailed output

    Returns:
        Tuple of (passed: bool, error_msg: str)
    """
    benchmark_name = benchmark_path.stem
    ref_binary = Path(temp_dir) / f"{benchmark_name}_ref"
    opt_binary = Path(temp_dir) / f"{benchmark_name}_opt"

    # Compile reference version
    success, err = compile_benchmark(
        benchmark_path, ref_binary, CC, CFLAGS_REF, dataset
    )
    if not success:
        return False, f"Reference compilation failed: {err}"

    # Compile optimized version
    success, err = compile_benchmark(
        benchmark_path, opt_binary, CC, CFLAGS_OPT, dataset
    )
    if not success:
        return False, f"Optimized compilation failed: {err}"

    # Run reference version
    success, ref_output, err = run_benchmark(ref_binary)
    if not success:
        return False, f"Reference execution failed: {err}"

    # Run optimized version
    success, opt_output, err = run_benchmark(opt_binary)
    if not success:
        return False, f"Optimized execution failed: {err}"

    # Compare outputs
    match, diff_info = compare_outputs(ref_output, opt_output)
    if not match:
        if verbose:
            return False, f"Output mismatch: {diff_info}"
        return False, f"Output mismatch: {diff_info}"

    return True, ""


def main():
    parser = argparse.ArgumentParser(
        description="Test PolyBench/C benchmarks by comparing optimized vs reference outputs"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed output"
    )
    parser.add_argument(
        "-d", "--dataset",
        default=DEFAULT_DATASET,
        choices=["MINI_DATASET", "SMALL_DATASET", "MEDIUM_DATASET",
                 "LARGE_DATASET", "EXTRALARGE_DATASET"],
        help=f"Dataset size to use (default: {DEFAULT_DATASET})"
    )
    parser.add_argument(
        "-b", "--benchmark",
        help="Test only a specific benchmark (by name, e.g., 'atax')"
    )
    parser.add_argument(
        "-t", "--tolerance",
        type=float,
        default=1e-6,
        help="Floating point comparison tolerance (default: 1e-6)"
    )
    parser.add_argument(
        "--ref-compiler",
        default=CC,
        help=f"Reference compiler (default: {CC})"
    )
    parser.add_argument(
        "--opt-compiler",
        default=CC,
        help=f"Optimized compiler (default: {CC})"
    )
    parser.add_argument(
        "--keep-binaries",
        action="store_true",
        help="Keep compiled binaries after testing"
    )

    args = parser.parse_args()

    # Update compilers if specified

    print("=" * 70)
    print("PolyBench/C Automated Testing Script")
    print("=" * 70)
    print(f"Dataset: {args.dataset}")
    print(f"Tolerance: {args.tolerance}")
    print()

    # Find benchmarks
    benchmarks = find_benchmarks()

    # Filter if specific benchmark requested
    if args.benchmark:
        benchmarks = [b for b in benchmarks if args.benchmark in b.stem]
        if not benchmarks:
            print(f"Error: No benchmark matching '{args.benchmark}' found")
            sys.exit(1)

    print(f"Found {len(benchmarks)} benchmark(s) to test")
    print("-" * 70)

    # Create temp directory for binaries
    temp_dir = tempfile.mkdtemp(prefix="polybench_test_")
    if args.keep_binaries:
        print(f"Binaries will be kept in: {temp_dir}")
    print()

    results = {"passed": [], "failed": []}

    for i, benchmark in enumerate(benchmarks, 1):
        rel_path = benchmark.relative_to(ROOT_DIR)
        print(f"[{i}/{len(benchmarks)}] Testing {rel_path}...", end=" ", flush=True)

        passed, error = test_benchmark(
            benchmark, temp_dir, args.dataset, args.verbose
        )

        if passed:
            print("PASS")
            results["passed"].append(rel_path)
        else:
            print("FAIL")
            results["failed"].append((rel_path, error))
            if args.verbose:
                print(f"    Error: {error}")

    # Cleanup temp directory unless --keep-binaries
    if not args.keep_binaries:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Print summary
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Total: {len(benchmarks)}")
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")
    print()

    if results["failed"]:
        print("Failed benchmarks:")
        for benchmark, error in results["failed"]:
            print(f"  - {benchmark}")
            if args.verbose:
                print(f"    {error}")
        print()

    # Exit with appropriate code
    sys.exit(0 if not results["failed"] else 1)


if __name__ == "__main__":
    main()

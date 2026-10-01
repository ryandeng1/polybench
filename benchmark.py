#!/usr/bin/env python3
"""
PolyBench/C Automated Build Script
Compiles all benchmarks in datamining, linear-algebra, medley, and stencils directories.
"""

import argparse
import json
import random
import shlex
import subprocess
import time
from pathlib import Path

# Configuration
BIN_DIR = "bin"

def run_binary(bin_path: Path):
    cmd = f"taskset -c 41 {bin_path}"
    print(f"running {bin_path}")
    start = time.time()
    result = subprocess.run(shlex.split(cmd), text=True, capture_output=True, timeout=1800)
    end = time.time()
    print(f"ran {bin_path}, took: {end - start} seconds")
    assert result.returncode == 0, f"result: {result.stdout}\n{result.stderr}"
    return float(result.stdout)

def benchmark_name_from_binary(binary_name: str) -> str:
    if binary_name.endswith("_time"):
        return binary_name[: -len("_time")]
    return binary_name

def should_skip_benchmark(benchmark_name: str) -> bool:
    return "cholesky" in benchmark_name or "seidel-2d" in benchmark_name

def collect_binaries(bin_dir: Path, requested_benchmarks: set[str] | None = None) -> dict[str, Path]:
    binaries: dict[str, Path] = {}
    for path in sorted(bin_dir.iterdir()):
        if not path.is_file():
            continue
        benchmark_name = benchmark_name_from_binary(path.name)
        if requested_benchmarks is None and should_skip_benchmark(benchmark_name):
            continue
        if requested_benchmarks is not None and benchmark_name not in requested_benchmarks:
            continue
        binaries[benchmark_name] = path

    if requested_benchmarks is not None:
        missing = sorted(requested_benchmarks - set(binaries.keys()))
        assert not missing, f"requested benchmarks not found in {bin_dir}: {missing}"

    return binaries

def write_results(output: str, results: dict[str, float]):
    with open(output, "w") as f:
        json.dump(results, f)

def ordered_benchmark_names(
    benchmark_names: set[str] | list[str],
    randomize_order: bool = False,
    random_seed: int | None = None,
) -> list[str]:
    names = sorted(benchmark_names)
    if randomize_order:
        rng = random.Random(random_seed)
        rng.shuffle(names)
    return names

def run_all_binaries(
    output: str,
    bin_dir: Path,
    requested_benchmarks: set[str] | None = None,
    randomize_order: bool = False,
    random_seed: int | None = None,
):
    bench_result: dict[str, float] = {}
    binaries = collect_binaries(bin_dir, requested_benchmarks)
    benchmark_order = ordered_benchmark_names(
        list(binaries.keys()),
        randomize_order=randomize_order,
        random_seed=random_seed,
    )
    for benchmark_name in benchmark_order:
        runtime = run_binary(binaries[benchmark_name])
        bench_result[benchmark_name] = runtime
    write_results(output, bench_result)

def run_paired_binaries(
    reference_bin_dir: Path,
    drfaa_bin_dir: Path,
    reference_output: str,
    drfaa_output: str,
    requested_benchmarks: set[str] | None = None,
    randomize_order: bool = False,
    random_seed: int | None = None,
):
    reference_binaries = collect_binaries(reference_bin_dir, requested_benchmarks)
    drfaa_binaries = collect_binaries(drfaa_bin_dir, requested_benchmarks)

    reference_names = set(reference_binaries.keys())
    drfaa_names = set(drfaa_binaries.keys())
    missing_from_reference = sorted(drfaa_names - reference_names)
    missing_from_drfaa = sorted(reference_names - drfaa_names)
    assert not missing_from_reference and not missing_from_drfaa, (
        "binary mismatch between reference and drfaa:\n"
        f"missing_from_reference={missing_from_reference}\n"
        f"missing_from_drfaa={missing_from_drfaa}"
    )

    reference_results: dict[str, float] = {}
    drfaa_results: dict[str, float] = {}
    benchmark_order = ordered_benchmark_names(
        reference_names,
        randomize_order=randomize_order,
        random_seed=random_seed,
    )
    for benchmark_name in benchmark_order:
        reference_results[benchmark_name] = run_binary(reference_binaries[benchmark_name])
        drfaa_results[benchmark_name] = run_binary(drfaa_binaries[benchmark_name])

    write_results(reference_output, reference_results)
    write_results(drfaa_output, drfaa_results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure performance of test scripts.")
    parser.add_argument(
        "--output",
        type=str,
        help="output path when benchmarking a single bin directory",
    )
    parser.add_argument(
        "--bin-dir",
        type=str,
        default=BIN_DIR,
        help=f"directory containing binaries to benchmark (default: {BIN_DIR})",
    )
    parser.add_argument(
        "--reference-bin-dir",
        type=str,
        help="reference binaries directory for paired benchmarking mode",
    )
    parser.add_argument(
        "--drfaa-bin-dir",
        type=str,
        help="drfaa binaries directory for paired benchmarking mode",
    )
    parser.add_argument(
        "--reference-output",
        type=str,
        help="reference output path for paired benchmarking mode",
    )
    parser.add_argument(
        "--drfaa-output",
        type=str,
        help="drfaa output path for paired benchmarking mode",
    )
    parser.add_argument(
        "--benchmark",
        type=str,
        action="append",
        default=[],
        help=(
            "benchmark name to run; can be repeated and can include comma-separated names "
            "(e.g. --benchmark atax --benchmark 2mm,3mm)"
        ),
    )
    parser.add_argument(
        "--randomize-order",
        action="store_true",
        help="run benchmarks in randomized order instead of sorted order",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="seed for --randomize-order; if omitted, uses non-deterministic ordering",
    )
    args = parser.parse_args()

    requested_benchmarks: set[str] | None = None
    if args.benchmark:
        requested_benchmarks = set()
        for requested_arg in args.benchmark:
            for benchmark_name in requested_arg.split(","):
                normalized_name = benchmark_name_from_binary(benchmark_name.strip())
                if normalized_name:
                    requested_benchmarks.add(normalized_name)
        if not requested_benchmarks:
            parser.error("--benchmark was provided but no benchmark names were parsed")

    paired_mode_requested = any([
        args.reference_bin_dir,
        args.drfaa_bin_dir,
        args.reference_output,
        args.drfaa_output,
    ])

    if paired_mode_requested:
        assert args.reference_bin_dir, "--reference-bin-dir is required in paired mode"
        assert args.drfaa_bin_dir, "--drfaa-bin-dir is required in paired mode"
        assert args.reference_output, "--reference-output is required in paired mode"
        assert args.drfaa_output, "--drfaa-output is required in paired mode"
        run_paired_binaries(
            Path(args.reference_bin_dir),
            Path(args.drfaa_bin_dir),
            args.reference_output,
            args.drfaa_output,
            requested_benchmarks,
            randomize_order=args.randomize_order,
            random_seed=args.random_seed,
        )
    else:
        assert args.output, "--output is required in single-directory mode"
        run_all_binaries(
            args.output,
            Path(args.bin_dir),
            requested_benchmarks,
            randomize_order=args.randomize_order,
            random_seed=args.random_seed,
        )

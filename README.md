## Overview
This repository contains the PolyBench benchmark, which consists of 30 problems, using cilk_for.

### Relevant Files

* `build_all.py` compiles all of the benchmark files automatically as previously there was no obvious way to automate this process. Currently, the `-d` option determines the size of the input to be used when running the code. `-j` sets the number of parallel jobs. The specific flags used are in `build_all.py` which can/should be modified.
  * Example usage: `python build_all.py -d MEDIUM_DATASET`.
  * The drfaa flag is used for a particular compiler analysis I am testing and therefore is not necessarily applicable to all use cases.
* `test_all.py` was meant to test if any changes to the compiler resulted in different outputs. You provide a reference compiler such as `clang` and an `opt-compiler` and then the program will run the executables under compiled by both compilers, and then compare the outputs. The default program (without `-DBENCHMARK` writes out outputs to file).
* `benchmark.py` is used to benchmark the runtime of a given problem. When `-DBENCHMARK` is used, the program outputs the median runtime which is recorded by this python file.

The below can be ignored as it is comparing to Pluto.

### Pluto vs. DRFAA comparison

`pluto_compare.py` runs a reproducible single-core comparison between ordinary
serial C, the OpenCilk serial target, full DRFAA, and three serial Pluto
transformations. It never defines `USE_REDUCER` or `USE_ARRAY_REDUCER`.

```sh
python3 pluto_compare.py all
```

The defaults are all 30 kernels, `MEDIUM_DATASET`, 100 in-process timing
samples, CPU 41, `-O3 -march=native`, and a fixed randomization seed. OpenCilk
modes use `-fopencilk -ftapir=serial`; no mode uses LTO, `restrict`, or generic
fast-math flags.

The six reported modes are:

* `serial_c`
* `opencilk_serial`
* `drfaa`
* `pluto_l1`
* `pluto_l2`
* `pluto_diamond`

For the August-jam comparison of serial C++, DRFAA, and every Pluto tiling
mode, select the dedicated profile:

```sh
python3 pluto_compare.py all --comparison-profile august-jam-all-pluto
```

This profile keeps `serial_c`, `drfaa`, `pluto_l1`, `pluto_l2`, and
`pluto_diamond`. It preserves the literal `clang++` driver and gives all five
modes the August-jam common flags
`-O3 -g -fno-exceptions -mllvm -enable-unroll-and-jam`. DRFAA additionally
uses `-fopencilk -ftapir=serial` and the August DRF analysis flags, without the
later `-enable-drf-memoryssa` experiment. The older
`august-jam-three-way` profile remains available for reproducing L1-only
experiments.

To isolate the benefit of carrying OpenCilk's DRF loop contract into Pluto,
use the matched Clan profile (also selected by `build_pluto.sh`):

```sh
python3 pluto_compare.py all --comparison-profile august-jam-clan-drf
```

This profile adds `pluto_drf_l1`, `pluto_drf_l2`, and
`pluto_drf_diamond` alongside their three ordinary Pluto controls, plus
`serial_c` and `drfaa`. Every ordinary/DRF-aware Pluto pair consumes the same
`cilk_for`-annotated source hash and uses identical Pluto policy flags; the
DRF-aware member adds only `--assume-cilk-drf`.

The modified Clan frontend assigns each lexical `cilk_for` a unique ID and
records its iterator depth on every enclosed OpenScop statement. With the
opt-in flag, Pluto retains same-iteration dependences and removes only the
cross-iteration portions for source/destination statements enclosed by that
same loop ID. Dependencies between separate sibling loops are preserved.
This is a semantic assumption, not a proof: use the flag only where the
`cilk_for` contract is valid.

The driver stages ordinary C under `pluto_sources/serial` and a matched
`pluto_sources/cilk_drf` tree. Both resolve reducer conditionals and remove
Cilk headers/control constructs without modifying the checked-out benchmarks;
the annotated tree preserves `cilk_for` only inside the SCoP. When a profile
contains a Pluto+DRF mode, all ordinary and DRF-aware Pluto controls consume
that same annotated input. Generated C is retained under
`pluto_sources/transformed/<mode>`; binaries and logs remain in the separate
work directory.

Pluto uses Clan, the default `polycc` frontend. Five staged inputs need narrow
canonicalizations for Clan: loop-local scratch declarations in `symm`,
`gramschmidt`, `ludcmp`, and `deriche` become assignments to existing
function-scoped variables, and ADI's SCoP begins after scalar coefficient
initialization. These changes apply to both Pluto staging copies, not to the
checked-out OpenCilk sources. See `pluto_sources/README.md` for the generated
tree layout.

When Pluto output is compiled as C++, the driver removes the obsolete
`register` storage class emitted by Pluto's C code generator; variable types
and generated loop semantics are unchanged.

Every Pluto invocation records `--codegen-context=1`, the valid PolyBench
precondition that integer size parameters are positive. Without this context,
Pluto can emit signed-overflowing guards that incorrectly skip an entire
parametric kernel.

Each performance binary is checked for parallel-runtime dependencies. Separate
array-dump binaries are compared against the `serial_c` reference
before timing; failed pairs
are excluded rather than reported as speedups. The experiment directory
contains `manifest.json`, `correctness.json`, raw samples, CSV/JSON summaries,
and `report.md`.

Pluto transformations and Clang builds each have a 900-second timeout by
default; change it with `--compile-timeout`. The driver kills the whole child
process group on timeout so a `polycc` wrapper cannot leave Pluto running.
Correctness and timing executions use the separate `--timeout` setting
(1800 seconds by default). The end of `report.md` lists every compilation or
transformation timeout by phase, kernel, mode, and elapsed time.

Use `--benchmark 2mm,3mm` for a focused run. Use
`--pluto-source-dir PATH` to place the durable source workspace somewhere
other than `./pluto_sources`.

To separate compilation from execution, give the build a persistent experiment
and work directory, then resume that experiment:

```sh
experiment_dir=results/pluto_drfaa_my_run
python3 pluto_compare.py build \
  --experiment-dir "$experiment_dir" \
  --work-dir "$experiment_dir/work" \
  --jobs 8
python3 pluto_compare.py run --experiment-dir "$experiment_dir"
```

`build` performs Pluto transformation and compiles both performance and
array-dump correctness binaries. `run` loads those binaries from
`manifest.json`, checks numerical output, runs the timings, and writes the
report without invoking Pluto or Clang. `check` similarly reloads an existing
build and performs correctness only. Dataset and iteration count come from the
build manifest; runtime options such as `--cpu`, `--seed`, and `--timeout`
may be supplied to `run`.

`--jobs 1`, the default, retains the original serial compilation path. Values
greater than one select a bounded parallel path for Clang builds; for example,
`--jobs 8` permits eight compiler processes at once. Manifest updates remain
serialized, each compiler process retains its individual `--compile-timeout`,
and Pluto transformations remain serial.

The source-only and reporting phases remain available:

```sh
python3 pluto_compare.py stage
python3 pluto_compare.py transform
python3 pluto_compare.py report --experiment-dir results/pluto_drfaa_<timestamp>
```

## Overview
This repository contains the PolyBench benchmark, which consists of 30 problems.

### Relevant Files

Note: A lot of the code has been generated with the use of AI.

* `build_all.py` compiles all of the benchmark files automatically as previously there was no obvious way to automate this process. Currently, the only options are the `-d` option which determines the size of the input to be used when running the code.
    * In `build_all.py` the `-DBENCHMARK` defines is intended to run benchmarking is the current way of benchmarking is not ideal (it runs the program 5 times and gets the median time, which is not enough iterations for smaller input sizes). This defines should probably be removed for testing.
    * Example usage: `python build_all.py -d MEDIUM_DATASET`.
    * The drfaa flag is used for a particular compiler analysis I am testing and therefore is not necessarily applicable to all use cases.
* `test_all.py` was meant to test if any changes to the compiler resulted in different outputs. You provide a reference compiler such as `clang` and an `opt-compiler` and then the program will run the executables under compiled by both compilers, and then compare the outputs. The default program (without `-DBENCHMARK` writes out outputs to file).
* `benchmark.py` is used to benchmark the runtime of a given problem. When `-DBENCHMARK` is used, the program outputs the median runtime which is recorded by this python file.

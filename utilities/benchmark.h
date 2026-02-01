/**
 * benchmark.h: Benchmarking utilities for PolyBench/C
 *
 * Provides timing infrastructure using clock_gettime for accurate
 * kernel timing with multiple iterations and median calculation.
 *
 * Compile with -DBENCHMARK to enable benchmarking mode.
 */

#ifndef BENCHMARK_H
#define BENCHMARK_H

#include <time.h>
#include <stdlib.h>
#include <stdio.h>

/* Number of benchmark iterations */
#ifndef N_BENCHMARK_ITERATIONS
#define N_BENCHMARK_ITERATIONS 100
#endif

/* Comparison function for qsort */
static int benchmark_compare_doubles(const void *a, const void *b) {
    double da = *(const double *)a;
    double db = *(const double *)b;
    return (da > db) - (da < db);
}

/* Calculate median of an array of doubles */
static double benchmark_median(double *times, int n) {
    qsort(times, n, sizeof(double), benchmark_compare_doubles);
    if (n % 2 == 0) {
        return (times[n/2 - 1] + times[n/2]) / 2.0;
    } else {
        return times[n/2];
    }
}

/* Get elapsed time in seconds between two timespecs */
static double benchmark_elapsed_seconds(struct timespec *start, struct timespec *end) {
    return (end->tv_sec - start->tv_sec) + (end->tv_nsec - start->tv_nsec) / 1e9;
}

/* Macros for benchmark timing */
#define BENCHMARK_BEGIN \
    struct timespec _benchmark_start, _benchmark_end; \
    clock_gettime(CLOCK_MONOTONIC, &_benchmark_start);

#define BENCHMARK_END \
    clock_gettime(CLOCK_MONOTONIC, &_benchmark_end);

#define BENCHMARK_ELAPSED \
    benchmark_elapsed_seconds(&_benchmark_start, &_benchmark_end)

#define BENCHMARK_PRINT_MEDIAN(times, n) \
    printf("%0.6f\n", benchmark_median(times, n));

#endif /* BENCHMARK_H */

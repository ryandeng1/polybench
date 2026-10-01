/**
 * benchmark.h: Benchmarking utilities for PolyBench/C
 *
 * Provides timing infrastructure using clock_gettime for accurate
 * kernel timing with multiple iterations and median calculation.
 * Optionally appends per-iteration runtimes to a JSON-lines file when
 * POLYBENCH_RUNTIME_ARRAY_FILE is set in the environment.
 *
 * Compile with -DBENCHMARK to enable benchmarking mode.
 */

#ifndef BENCHMARK_H
#define BENCHMARK_H

#include <time.h>
#include <stdlib.h>
#include <stdio.h>

#ifndef BENCHMARK_RUNTIMES_FILE_ENV
#define BENCHMARK_RUNTIMES_FILE_ENV "POLYBENCH_RUNTIME_ARRAY_FILE"
#endif

/* Number of benchmark iterations */
#ifndef N_BENCHMARK_ITERATIONS
// #define N_BENCHMARK_ITERATIONS 2500
// #define N_BENCHMARK_ITERATIONS 1000
#define N_BENCHMARK_ITERATIONS 100
#endif

/* Comparison function for qsort */
static int benchmark_compare_doubles(const void *a, const void *b) {
    double da = *(const double *)a;
    double db = *(const double *)b;
    return (da > db) - (da < db);
}

/* Calculate median of an array of doubles */
static double benchmark_median(const double *times, int n) {
    if (n <= 0) {
        return 0.0;
    }

    double *sorted_times = (double *)malloc((size_t)n * sizeof(double));
    if (sorted_times == NULL) {
        return times[0];
    }

    for (int i = 0; i < n; i++) {
        sorted_times[i] = times[i];
    }

    qsort(sorted_times, n, sizeof(double), benchmark_compare_doubles);

    double median;
    if (n % 2 == 0) {
        median = (sorted_times[n/2 - 1] + sorted_times[n/2]) / 2.0;
    } else {
        median = sorted_times[n/2];
    }

    free(sorted_times);
    return median;
}

/* Get elapsed time in seconds between two timespecs */
static double benchmark_elapsed_seconds(struct timespec *start, struct timespec *end) {
    return (end->tv_sec - start->tv_sec) + (end->tv_nsec - start->tv_nsec) / 1e9;
}

static const char *benchmark_basename(const char *path) {
    const char *base = path;
    for (const char *p = path; *p != '\0'; p++) {
        if (*p == '/' || *p == '\\') {
            base = p + 1;
        }
    }
    return base;
}

static void benchmark_write_runtimes_if_requested(
    const char *source_path,
    const double *times,
    int n,
    double median
) {
    const char *output_path = getenv(BENCHMARK_RUNTIMES_FILE_ENV);
    if (output_path == NULL || output_path[0] == '\0') {
        return;
    }

    FILE *output_file = fopen(output_path, "a");
    if (output_file == NULL) {
        return;
    }

    const char *benchmark_name = benchmark_basename(source_path);
    fprintf(output_file, "{\"benchmark\":\"%s\",\"median\":%.9f,\"runtimes\":[", benchmark_name, median);
    for (int i = 0; i < n; i++) {
        if (i > 0) {
            fputc(',', output_file);
        }
        fprintf(output_file, "%.9f", times[i]);
    }
    fprintf(output_file, "]}\n");
    fclose(output_file);
}

static void benchmark_print_median(const char *source_path, const double *times, int n) {
    double median = benchmark_median(times, n);
    printf("%0.9f\n", median);
    benchmark_write_runtimes_if_requested(source_path, times, n, median);
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
    benchmark_print_median(__FILE__, times, n);

#endif /* BENCHMARK_H */

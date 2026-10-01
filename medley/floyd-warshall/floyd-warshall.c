/**
 * This version is stamped on May 10, 2016
 *
 * Contact:
 *   Louis-Noel Pouchet <pouchet.ohio-state.edu>
 *   Tomofumi Yuki <tomofumi.yuki.fr>
 *
 * Web address: http://polybench.sourceforge.net
 */
/* floyd-warshall.c: this file is part of PolyBench/C */

#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <math.h>
#include <cilk/cilk.h>
// #include <cilk/cilk_api.h>

/* Include polybench common header. */
#include <polybench.h>

/* Include benchmark header for timing */
#ifdef BENCHMARK
#include <benchmark.h>
#endif

/* Include benchmark-specific header. */
#include "floyd-warshall.h"


/* Array initialization. */
static
void init_array (int n,
		 DATA_TYPE POLYBENCH_2D(path,N,N,n,n))
{
  int i, j;

  for (i = 0; i < n; i++)
    for (j = 0; j < n; j++) {
      path[i][j] = i*j%7+1;
      if ((i+j)%13 == 0 || (i+j)%7==0 || (i+j)%11 == 0)
         path[i][j] = 999;
    }
}


/* DCE code. Must scan the entire live-out data.
   Can be used also to check the correctness of the output. */
static
void print_array(int n,
		 DATA_TYPE POLYBENCH_2D(path,N,N,n,n))

{
  int i, j;

  POLYBENCH_DUMP_START;
  POLYBENCH_DUMP_BEGIN("path");
  for (i = 0; i < n; i++)
    for (j = 0; j < n; j++) {
      if ((i * n + j) % 20 == 0) fprintf (POLYBENCH_DUMP_TARGET, "\n");
      fprintf (POLYBENCH_DUMP_TARGET, DATA_PRINTF_MODIFIER, path[i][j]);
    }
  POLYBENCH_DUMP_END("path");
  POLYBENCH_DUMP_FINISH;
}


/* Main computational kernel. The whole function will be timed,
   including the call and return. */
static
void kernel_floyd_warshall(int n,
			   DATA_TYPE POLYBENCH_2D(path,N,N,n,n))
{
  int k;
#pragma scop
  for (k = 0; k < _PB_N; k++)
    {
      // Iteration i=k writes to path[k][j] while other
      // iterations concurrently read path[k][j].

      cilk_for(int i = 0; i < _PB_N; i++) {
	      cilk_for (int j = 0; j < _PB_N; j++) {
          // int via = path[i][k] + path[k][j];
          // if (via < path[i][j]) path[i][j] = via;
	        path[i][j] = path[i][j] < path[i][k] + path[k][j] ? path[i][j] : path[i][k] + path[k][j];
        }
      }
    }
#pragma endscop

}


int main(int argc, char** argv)
{
  // printf("nworkers: %d\n", __cilkrts_get_nworkers());
  cilk_scope {

  /* Retrieve problem size. */
  int n = N;

  /* Variable declaration/allocation. */
  POLYBENCH_2D_ARRAY_DECL(path, DATA_TYPE, N, N, n, n);


#ifdef BENCHMARK
  /* Benchmark mode: run kernel N_BENCHMARK_ITERATIONS times and report median */
  double benchmark_times[N_BENCHMARK_ITERATIONS];
  for (int benchmark_iter = 0; benchmark_iter < N_BENCHMARK_ITERATIONS; benchmark_iter++) {
    /* Initialize array(s). */
    init_array (n, POLYBENCH_ARRAY(path));

    /* Time the kernel */
    BENCHMARK_BEGIN
    kernel_floyd_warshall (n, POLYBENCH_ARRAY(path));
    BENCHMARK_END
    benchmark_times[benchmark_iter] = BENCHMARK_ELAPSED;
  }
  BENCHMARK_PRINT_MEDIAN(benchmark_times, N_BENCHMARK_ITERATIONS);
#else
  /* Initialize array(s). */
  init_array (n, POLYBENCH_ARRAY(path));

  /* Start timer. */
  polybench_start_instruments;

  /* Run kernel. */
  kernel_floyd_warshall (n, POLYBENCH_ARRAY(path));

  /* Stop and print timer. */
  polybench_stop_instruments;
  polybench_print_instruments;
#endif

  /* Prevent dead-code elimination. All live-out data must be printed
     by the function call in argument. */
  polybench_prevent_dce(print_array(n, POLYBENCH_ARRAY(path)));

  /* Be clean. */
  POLYBENCH_FREE_ARRAY(path);
  }

  return 0;
}

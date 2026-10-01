/**
 * This version is stamped on May 10, 2016
 *
 * Contact:
 *   Louis-Noel Pouchet <pouchet.ohio-state.edu>
 *   Tomofumi Yuki <tomofumi.yuki.fr>
 *
 * Web address: http://polybench.sourceforge.net
 */
/* atax.c: this file is part of PolyBench/C */

#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <math.h>
#include <cilk/cilk.h>
#ifdef USE_REDUCER
#include <cilk/opadd_reducer>
#endif

/* Include polybench common header. */
#include <polybench.h>

/* Include benchmark header for timing */
#ifdef BENCHMARK
#include <benchmark.h>
#endif

/* Include benchmark-specific header. */
#include "atax.h"


/* Array initialization. */
static
void init_array (int m, int n,
		 DATA_TYPE POLYBENCH_2D(A,M,N,m,n),
		 DATA_TYPE POLYBENCH_1D(x,N,n))
{
  int i, j;
  DATA_TYPE fn;
  fn = (DATA_TYPE)n;

  for (i = 0; i < n; i++)
      x[i] = 1 + (i / fn);
  for (i = 0; i < m; i++)
    for (j = 0; j < n; j++)
      A[i][j] = (DATA_TYPE) ((i+j) % n) / (5*m);
}


/* DCE code. Must scan the entire live-out data.
   Can be used also to check the correctness of the output. */
static
void print_array(int n,
		 DATA_TYPE POLYBENCH_1D(y,N,n))

{
  int i;

  POLYBENCH_DUMP_START;
  POLYBENCH_DUMP_BEGIN("y");
  for (i = 0; i < n; i++) {
    if (i % 20 == 0) fprintf (POLYBENCH_DUMP_TARGET, "\n");
    fprintf (POLYBENCH_DUMP_TARGET, DATA_PRINTF_MODIFIER, y[i]);
  }
  POLYBENCH_DUMP_END("y");
  POLYBENCH_DUMP_FINISH;
}


/* Main computational kernel. The whole function will be timed,
   including the call and return. */
#ifdef USE_REDUCER
static
void kernel_atax(int m, int n,
		 DATA_TYPE POLYBENCH_2D(A,M,N,m,n),
		 DATA_TYPE POLYBENCH_1D(x,N,n),
		 DATA_TYPE POLYBENCH_1D(y,N,n),
		 DATA_TYPE POLYBENCH_1D(tmp,M,m))
{
  int j;
#pragma scop
  /*
  cilk_for (int i = 0; i < _PB_N; i++)
    y[i] = 0;
  for (int i = 0; i < _PB_M; i++)
    {
      tmp[i] = SCALAR_VAL(0.0);
      for (int j = 0; j < _PB_N; j++)
	tmp[i] = tmp[i] + A[i][j] * x[j];
      for (int j = 0; j < _PB_N; j++)
	y[j] = y[j] + A[i][j] * tmp[i];
    }
  */

  cilk::opadd_reducer<DATA_TYPE> reduction_r = SCALAR_VAL(0.0);
  for (int i = 0; i < _PB_M; i++) {
    reduction_r = SCALAR_VAL(0.0);
    cilk_for (int j = 0; j < _PB_N; j++)
      reduction_r += A[i][j] * x[j];
    tmp[i] = reduction_r;
  }

  for (int j = 0; j < _PB_N; j++) {
    reduction_r = SCALAR_VAL(0.0);
    cilk_for (int i = 0; i < _PB_M; i++)
      reduction_r += A[i][j] * tmp[i];
    y[j] = reduction_r;
  }
#pragma endscop

}
#else
static
void kernel_atax(int m, int n,
		 DATA_TYPE POLYBENCH_2D(A,M,N,m,n),
		 DATA_TYPE POLYBENCH_1D(x,N,n),
		 DATA_TYPE POLYBENCH_1D(y,N,n),
		 DATA_TYPE POLYBENCH_1D(tmp,M,m))
{
  int j;
#pragma scop
  /*
  cilk_for (int i = 0; i < _PB_N; i++)
    y[i] = 0;
  for (int i = 0; i < _PB_M; i++)
    {
      tmp[i] = SCALAR_VAL(0.0);
      for (int j = 0; j < _PB_N; j++)
	tmp[i] = tmp[i] + A[i][j] * x[j];
      for (int j = 0; j < _PB_N; j++)
	y[j] = y[j] + A[i][j] * tmp[i];
    }
  */

  cilk_for (int i = 0; i < _PB_M; i++) {
    tmp[i] = SCALAR_VAL(0.0);
    for (int j = 0; j < _PB_N; j++) {
	    tmp[i] = tmp[i] + A[i][j] * x[j];
    }
  }

  cilk_for (int j = 0; j < _PB_N; j++) {
    y[j] = 0;
    for (int i = 0; i < _PB_M; i++) {
	    y[j] = y[j] + A[i][j] * tmp[i];
    }
  }
#pragma endscop

}
#endif


int main(int argc, char** argv)
{
  cilk_scope {

  /* Retrieve problem size. */
  int m = M;
  int n = N;

  /* Variable declaration/allocation. */
  POLYBENCH_2D_ARRAY_DECL(A, DATA_TYPE, M, N, m, n);
  POLYBENCH_1D_ARRAY_DECL(x, DATA_TYPE, N, n);
  POLYBENCH_1D_ARRAY_DECL(y, DATA_TYPE, N, n);
  POLYBENCH_1D_ARRAY_DECL(tmp, DATA_TYPE, M, m);

#ifdef BENCHMARK
  /* Benchmark mode: run kernel N_BENCHMARK_ITERATIONS times and report median */
  double benchmark_times[N_BENCHMARK_ITERATIONS];
  for (int benchmark_iter = 0; benchmark_iter < N_BENCHMARK_ITERATIONS; benchmark_iter++) {
    /* Initialize array(s). */
    init_array (m, n, POLYBENCH_ARRAY(A), POLYBENCH_ARRAY(x));

    /* Time the kernel */
    BENCHMARK_BEGIN
    kernel_atax (m, n,
	       POLYBENCH_ARRAY(A),
	       POLYBENCH_ARRAY(x),
	       POLYBENCH_ARRAY(y),
	       POLYBENCH_ARRAY(tmp));
    BENCHMARK_END
    benchmark_times[benchmark_iter] = BENCHMARK_ELAPSED;
  }
  BENCHMARK_PRINT_MEDIAN(benchmark_times, N_BENCHMARK_ITERATIONS);
#else
  /* Initialize array(s). */
  init_array (m, n, POLYBENCH_ARRAY(A), POLYBENCH_ARRAY(x));

  /* Start timer. */
  polybench_start_instruments;

  /* Run kernel. */
  kernel_atax (m, n,
	       POLYBENCH_ARRAY(A),
	       POLYBENCH_ARRAY(x),
	       POLYBENCH_ARRAY(y),
	       POLYBENCH_ARRAY(tmp));

  /* Stop and print timer. */
  polybench_stop_instruments;
  polybench_print_instruments;
#endif

  /* Prevent dead-code elimination. All live-out data must be printed
     by the function call in argument. */
  polybench_prevent_dce(print_array(n, POLYBENCH_ARRAY(y)));

  /* Be clean. */
  POLYBENCH_FREE_ARRAY(A);
  POLYBENCH_FREE_ARRAY(x);
  POLYBENCH_FREE_ARRAY(y);
  POLYBENCH_FREE_ARRAY(tmp);
  }

  return 0;
}

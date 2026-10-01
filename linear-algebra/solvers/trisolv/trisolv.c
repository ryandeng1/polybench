/**
 * This version is stamped on May 10, 2016
 *
 * Contact:
 *   Louis-Noel Pouchet <pouchet.ohio-state.edu>
 *   Tomofumi Yuki <tomofumi.yuki.fr>
 *
 * Web address: http://polybench.sourceforge.net
 */
/* trisolv.c: this file is part of PolyBench/C */

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
#include "trisolv.h"


/* Array initialization. */
static
void init_array(int n,
		DATA_TYPE POLYBENCH_2D(L,N,N,n,n),
		DATA_TYPE POLYBENCH_1D(x,N,n),
		DATA_TYPE POLYBENCH_1D(b,N,n))
{
  int i, j;

  for (i = 0; i < n; i++)
    {
      x[i] = - 999;
      b[i] =  i ;
      for (j = 0; j <= i; j++)
	L[i][j] = (DATA_TYPE) (i+n-j+1)*2/n;
    }
}


/* DCE code. Must scan the entire live-out data.
   Can be used also to check the correctness of the output. */
static
void print_array(int n,
		 DATA_TYPE POLYBENCH_1D(x,N,n))

{
  int i;

  POLYBENCH_DUMP_START;
  POLYBENCH_DUMP_BEGIN("x");
  for (i = 0; i < n; i++) {
    fprintf (POLYBENCH_DUMP_TARGET, DATA_PRINTF_MODIFIER, x[i]);
    if (i % 20 == 0) fprintf (POLYBENCH_DUMP_TARGET, "\n");
  }
  POLYBENCH_DUMP_END("x");
  POLYBENCH_DUMP_FINISH;
}


/* Main computational kernel. The whole function will be timed,
   including the call and return. */
#ifdef USE_REDUCER
static
void kernel_trisolv(int n,
		    DATA_TYPE POLYBENCH_2D(L,N,N,n,n),
		    DATA_TYPE POLYBENCH_1D(x,N,n),
		    DATA_TYPE POLYBENCH_1D(b,N,n))
{
  int i, j;
#pragma scop
  cilk::opadd_reducer<DATA_TYPE> x_r = SCALAR_VAL(0.0);
  for (int i = 0; i < _PB_N; i++)
    {
      x_r = b[i];
      cilk_for (int j = 0; j < i; j++)
        x_r += -L[i][j] * x[j];
      x[i] = x_r / L[i][i];
    }
#pragma endscop

}
#else
static
void kernel_trisolv(int n,
		    DATA_TYPE POLYBENCH_2D(L,N,N,n,n),
		    DATA_TYPE POLYBENCH_1D(x,N,n),
		    DATA_TYPE POLYBENCH_1D(b,N,n))
{
  int i, j;
#pragma scop
  for (int i = 0; i < _PB_N; i++)
    {
      x[i] = b[i];
      for (int j = 0; j <i; j++)
        x[i] -= L[i][j] * x[j];
      x[i] = x[i] / L[i][i];
    }
#pragma endscop

}
#endif


int main(int argc, char** argv)
{
  cilk_scope {

  /* Retrieve problem size. */
  int n = N;

  /* Variable declaration/allocation. */
  POLYBENCH_2D_ARRAY_DECL(L, DATA_TYPE, N, N, n, n);
  POLYBENCH_1D_ARRAY_DECL(x, DATA_TYPE, N, n);
  POLYBENCH_1D_ARRAY_DECL(b, DATA_TYPE, N, n);


#ifdef BENCHMARK
  /* Benchmark mode: run kernel N_BENCHMARK_ITERATIONS times and report median */
  double benchmark_times[N_BENCHMARK_ITERATIONS];
  for (int benchmark_iter = 0; benchmark_iter < N_BENCHMARK_ITERATIONS; benchmark_iter++) {
    /* Initialize array(s). */
    init_array (n, POLYBENCH_ARRAY(L), POLYBENCH_ARRAY(x), POLYBENCH_ARRAY(b));

    /* Time the kernel */
    BENCHMARK_BEGIN
    kernel_trisolv (n, POLYBENCH_ARRAY(L), POLYBENCH_ARRAY(x), POLYBENCH_ARRAY(b));
    BENCHMARK_END
    benchmark_times[benchmark_iter] = BENCHMARK_ELAPSED;
  }
  BENCHMARK_PRINT_MEDIAN(benchmark_times, N_BENCHMARK_ITERATIONS);
#else
  /* Initialize array(s). */
  init_array (n, POLYBENCH_ARRAY(L), POLYBENCH_ARRAY(x), POLYBENCH_ARRAY(b));

  /* Start timer. */
  polybench_start_instruments;

  /* Run kernel. */
  kernel_trisolv (n, POLYBENCH_ARRAY(L), POLYBENCH_ARRAY(x), POLYBENCH_ARRAY(b));

  /* Stop and print timer. */
  polybench_stop_instruments;
  polybench_print_instruments;
#endif

  /* Prevent dead-code elimination. All live-out data must be printed
     by the function call in argument. */
  polybench_prevent_dce(print_array(n, POLYBENCH_ARRAY(x)));

  /* Be clean. */
  POLYBENCH_FREE_ARRAY(L);
  POLYBENCH_FREE_ARRAY(x);
  POLYBENCH_FREE_ARRAY(b);
  }

  return 0;
}

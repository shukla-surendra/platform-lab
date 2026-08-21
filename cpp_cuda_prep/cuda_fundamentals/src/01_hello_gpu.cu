/*
 * 01_hello_gpu.cu - Simplest CUDA Program
 *
 * This is the "Hello World" of GPU programming
 * Shows:
 * - Kernel definition (__global__)
 * - Kernel launch (<<<blocks, threads>>>)
 * - Basic thread identification
 */

#include <stdio.h>

// Kernel: This runs on GPU, once per thread
__global__ void hello_kernel() {
    // Each thread has a unique ID
    int thread_id = blockIdx.x * blockDim.x + threadIdx.x;

    // Print from GPU (only a few threads, for clarity)
    if (thread_id < 10) {
        printf("Hello from GPU thread %d!\n", thread_id);
    }
}

int main() {
    printf("=== Hello GPU ===\n");
    printf("Launching 32 blocks × 256 threads = 8192 threads total\n\n");

    // Launch kernel
    // <<<gridSize, blockSize>>>
    // gridSize = number of blocks
    // blockSize = threads per block
    hello_kernel<<<32, 256>>>();

    // Wait for GPU to finish
    cudaDeviceSynchronize();

    printf("\nDone!\n");

    return 0;
}

/*
 * What happens:
 *
 * 1. hello_kernel is called 32 * 256 = 8192 times
 * 2. Each call runs on a different GPU thread
 * 3. Each thread:
 *    a. Calculates its unique ID
 *    b. If ID < 10, prints to console
 *
 * Expected output:
 * Hello from GPU thread 0!
 * Hello from GPU thread 1!
 * ...
 * Hello from GPU thread 9!
 *
 * Compilation:
 * nvcc -std=c++17 src/01_hello_gpu.cu -o hello_gpu
 *
 * Run:
 * ./hello_gpu
 */

/*
 * 02_vector_add.cu - Parallel Vector Addition
 *
 * Demonstrates:
 * - GPU kernel that does actual computation
 * - Memory allocation (cudaMalloc)
 * - Memory transfer (cudaMemcpy)
 * - Proper thread organization
 * - Error checking
 */

#include <stdio.h>
#include <cuda_runtime.h>

// Error checking macro
#define CUDA_CHECK(call)                                                  \
    do {                                                                  \
        cudaError_t error = call;                                        \
        if (error != cudaSuccess) {                                      \
            printf("CUDA error: %s\n", cudaGetErrorString(error));       \
            return 1;                                                     \
        }                                                                  \
    } while (0)

// Kernel: Add two vectors element-wise
// d_a, d_b: pointers to GPU memory
// d_result: pointer to result on GPU
// n: number of elements
__global__ void vector_add(float *d_a, float *d_b, float *d_result, int n) {
    // Calculate which element this thread handles
    int i = blockIdx.x * blockDim.x + threadIdx.x;

    // Make sure we don't access beyond array bounds
    if (i < n) {
        d_result[i] = d_a[i] + d_b[i];
    }
}

int main() {
    printf("=== Vector Addition on GPU ===\n\n");

    // Problem size
    const int n = 1000000;  // 1 million elements
    const size_t bytes = n * sizeof(float);

    printf("Adding vectors with %d elements\n", n);
    printf("Total memory: %.1f MB per vector\n\n", bytes / 1e6);

    // ============================================
    // Step 1: Allocate CPU memory
    // ============================================
    printf("Step 1: Allocating CPU memory...\n");
    float *h_a = (float *)malloc(bytes);
    float *h_b = (float *)malloc(bytes);
    float *h_result = (float *)malloc(bytes);

    if (!h_a || !h_b || !h_result) {
        printf("Failed to allocate CPU memory\n");
        return 1;
    }

    // ============================================
    // Step 2: Initialize CPU data
    // ============================================
    printf("Step 2: Initializing data...\n");
    for (int i = 0; i < n; i++) {
        h_a[i] = 1.0f;      // a[i] = 1.0
        h_b[i] = 2.0f;      // b[i] = 2.0
    }
    // Expected: result[i] = 3.0 for all i

    // ============================================
    // Step 3: Allocate GPU memory
    // ============================================
    printf("Step 3: Allocating GPU memory...\n");
    float *d_a, *d_b, *d_result;
    CUDA_CHECK(cudaMalloc(&d_a, bytes));
    CUDA_CHECK(cudaMalloc(&d_b, bytes));
    CUDA_CHECK(cudaMalloc(&d_result, bytes));
    printf("  Allocated %.1f MB on GPU\n\n", 3 * bytes / 1e6);

    // ============================================
    // Step 4: Copy data CPU → GPU
    // ============================================
    printf("Step 4: Copying data CPU → GPU...\n");
    CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice));
    printf("  Copied %.1f MB to GPU\n\n", 2 * bytes / 1e6);

    // ============================================
    // Step 5: Launch kernel on GPU
    // ============================================
    printf("Step 5: Launching kernel...\n");

    // Thread organization
    int block_size = 256;
    int grid_size = (n + block_size - 1) / block_size;  // Ceil division

    printf("  Block size: %d threads\n", block_size);
    printf("  Grid size: %d blocks\n", grid_size);
    printf("  Total threads: %d\n", grid_size * block_size);
    printf("  Elements per thread: ~%.1f\n\n", (float)n / (grid_size * block_size));

    // Launch kernel
    vector_add<<<grid_size, block_size>>>(d_a, d_b, d_result, n);
    CUDA_CHECK(cudaGetLastError());

    // Wait for kernel to finish
    CUDA_CHECK(cudaDeviceSynchronize());
    printf("  Kernel completed!\n\n");

    // ============================================
    // Step 6: Copy results GPU → CPU
    // ============================================
    printf("Step 6: Copying results GPU → CPU...\n");
    CUDA_CHECK(cudaMemcpy(h_result, d_result, bytes, cudaMemcpyDeviceToHost));
    printf("  Copied %.1f MB from GPU\n\n", bytes / 1e6);

    // ============================================
    // Step 7: Verify results
    // ============================================
    printf("Step 7: Verifying results...\n");
    int errors = 0;
    for (int i = 0; i < n; i++) {
        if (h_result[i] != 3.0f) {
            errors++;
            if (errors <= 5) {  // Print first 5 errors
                printf("  ERROR: result[%d] = %f (expected 3.0)\n", i, h_result[i]);
            }
        }
    }

    if (errors == 0) {
        printf("✓ All %d results correct!\n\n", n);
    } else {
        printf("✗ Found %d errors\n\n", errors);
    }

    // ============================================
    // Step 8: Print some results
    // ============================================
    printf("Step 8: Sample results:\n");
    for (int i = 0; i < 5; i++) {
        printf("  result[%d] = %.1f\n", i, h_result[i]);
    }
    printf("  ...\n");
    for (int i = n - 5; i < n; i++) {
        printf("  result[%d] = %.1f\n", i, h_result[i]);
    }
    printf("\n");

    // ============================================
    // Step 9: Cleanup
    // ============================================
    printf("Step 9: Cleaning up...\n");
    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_result));
    free(h_a);
    free(h_b);
    free(h_result);
    printf("  Memory freed\n\n");

    printf("=== Done! ===\n");

    return 0;
}

/*
 * What this program does:
 *
 * 1. Allocates 1 million floats on CPU (4 MB)
 * 2. Initializes: a[i] = 1.0, b[i] = 2.0
 * 3. Allocates same on GPU (VRAM)
 * 4. Copies data from CPU to GPU
 * 5. Launches GPU kernel with 1M threads
 *    - Each thread adds one pair of numbers
 *    - result[i] = a[i] + b[i] = 3.0
 * 6. Copies results back to CPU
 * 7. Verifies all results are correct
 * 8. Prints sample output
 * 9. Frees all memory
 *
 * Expected output:
 * ✓ All 1000000 results correct!
 * result[0] = 3.0
 * result[1] = 3.0
 * result[2] = 3.0
 * result[3] = 3.0
 * result[4] = 3.0
 * ...
 *
 * Compilation:
 * nvcc -std=c++17 src/02_vector_add.cu -o vector_add
 *
 * Run:
 * ./vector_add
 *
 * Performance note:
 * This will be 10-100x faster than CPU version!
 * (depending on GPU and CPU)
 */

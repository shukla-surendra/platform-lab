# CUDA Quick Start (5 Minutes)

Jump into CUDA programming immediately.

---

## Prerequisites

✅ Completed C++ fundamentals (../README.md)
✅ Understand pointers, memory allocation, functions
✅ Can compile C++ with clang++

---

## Installation Check

### If You Have NVIDIA GPU (Linux/Windows)

```bash
# Check NVIDIA GPU
nvidia-smi

# Check CUDA Toolkit
nvcc --version
```

**Expected output:** CUDA 12.0+ or similar

### If You DON'T Have NVIDIA GPU (macOS, older systems)

❌ Can't run examples locally
✅ Can still learn the syntax
✅ Use Google Colab (free cloud GPU)

---

## What is CUDA? (30-Second Version)

CUDA lets you run code on NVIDIA GPU instead of CPU.

```
CPU: 8 cores  → 1 task per core = 8 parallel tasks
GPU: 1000 cores → 1 task per core = 1000 parallel tasks!
```

**Result: 10-100x faster for parallel work**

---

## Core Concept: Kernels

A **kernel** is a function that runs on GPU, once per thread.

```cuda
// Runs on GPU, once per thread
__global__ void add(float *a, float *b, float *result, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        result[i] = a[i] + b[i];  // Each thread adds 1 pair
    }
}
```

**Key insight:** Same code runs 1000 times simultaneously (one per thread)!

---

## The CUDA Program Pattern

Every CUDA program follows this 5-step pattern:

```
1. Allocate GPU memory      cudaMalloc(&device_ptr, size)
2. Copy CPU data to GPU     cudaMemcpy(device_ptr, host_ptr, size, ...)
3. Launch kernel on GPU     kernel<<<gridSize, blockSize>>>(args)
4. Copy results back to CPU cudaMemcpy(host_ptr, device_ptr, size, ...)
5. Free GPU memory          cudaFree(device_ptr)
```

**Sound familiar?** It's the same pattern as C++ `new`/`delete`!

```cpp
// C++ (CPU memory)
float *arr = new float[1000];      // Allocate
// ... use array ...
delete[] arr;                       // Free

// CUDA (GPU memory)
float *d_arr;
cudaMalloc(&d_arr, 1000 * sizeof(float));  // Allocate
// ... use array on GPU ...
cudaFree(d_arr);                           // Free
```

---

## How to Compile CUDA

Use `nvcc` instead of `clang++`:

```bash
# Compile single file
nvcc -std=c++17 src/01_hello_gpu.cu -o hello_gpu

# Compile multiple files
nvcc -std=c++17 src/02_vector_add.cu src/utils.cu -o vector_add

# With headers
nvcc -std=c++17 -I./include src/program.cu -o program
```

**It's just like clang++, but for GPU code!**

---

## Thread Organization: The Key Difference

On GPU, you must think about how work is organized:

```
Grid (all threads you launch)
├─ Block 0    (256 threads working together)
├─ Block 1    (256 threads working together)
└─ Block 2    (256 threads working together)
   ...
Total: millions of threads, organized in blocks
```

**How to launch:**
```cuda
int gridSize = 100;      // 100 blocks
int blockSize = 256;     // 256 threads per block
kernel<<<gridSize, blockSize>>>(args);  // Total: 100 * 256 = 25,600 threads!
```

**Inside kernel, find your thread ID:**
```cuda
int threadId = blockIdx.x * blockDim.x + threadIdx.x;
```

Think: "Which thread am I? Use that to decide what to do."

---

## Memory: CPU vs GPU

| Location | CUDA Name | Allocate | Free | Use |
|----------|-----------|----------|------|-----|
| Computer RAM | Host memory | malloc/new | free/delete | Regular C++ |
| GPU RAM | Device memory | cudaMalloc | cudaFree | CUDA kernels |

**Pattern:**
```cuda
// Host (CPU) memory
float h_data[1000];  // Regular array

// Device (GPU) memory
float *d_data;
cudaMalloc(&d_data, 1000 * sizeof(float));

// Transfer CPU → GPU
cudaMemcpy(d_data, h_data, 1000*sizeof(float), cudaMemcpyHostToDevice);

// Use on GPU (kernel runs here)
kernel<<<blocks, threads>>>(d_data);

// Transfer GPU → CPU
cudaMemcpy(h_data, d_data, 1000*sizeof(float), cudaMemcpyDeviceToHost);

// Cleanup
cudaFree(d_data);
```

---

## Example: Vector Addition on GPU

### CPU Version (Sequential)
```cpp
void add_cpu(float *a, float *b, float *result, int n) {
    for (int i = 0; i < n; i++) {
        result[i] = a[i] + b[i];
    }
    // Time: 1ms for 1M elements
}
```

### GPU Version (Parallel)
```cuda
__global__ void add_gpu(float *a, float *b, float *result, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        result[i] = a[i] + b[i];  // Each of 1000 threads does this
    }
}

// Main CPU code
int main() {
    int n = 1000000;
    size_t bytes = n * sizeof(float);
    
    // CPU arrays
    float *h_a = (float*)malloc(bytes);
    float *h_b = (float*)malloc(bytes);
    float *h_result = (float*)malloc(bytes);
    
    // GPU arrays
    float *d_a, *d_b, *d_result;
    cudaMalloc(&d_a, bytes);
    cudaMalloc(&d_b, bytes);
    cudaMalloc(&d_result, bytes);
    
    // Initialize CPU data
    for (int i = 0; i < n; i++) {
        h_a[i] = 1.0f;
        h_b[i] = 2.0f;
    }
    
    // Copy to GPU
    cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice);
    
    // Launch kernel (256 threads per block)
    int blockSize = 256;
    int gridSize = (n + blockSize - 1) / blockSize;  // ~3906 blocks
    add_gpu<<<gridSize, blockSize>>>(d_a, d_b, d_result, n);
    
    // Copy results back
    cudaMemcpy(h_result, d_result, bytes, cudaMemcpyDeviceToHost);
    
    // Verify
    for (int i = 0; i < 10; i++) {
        printf("result[%d] = %f\n", i, h_result[i]);  // Should be 3.0
    }
    
    // Cleanup
    cudaFree(d_a);
    cudaFree(d_b);
    cudaFree(d_result);
    free(h_a);
    free(h_b);
    free(h_result);
    
    return 0;
}
```

**Speedup:** 10-100x faster than CPU version!

---

## Try This RIGHT NOW

### Option 1: You Have NVIDIA GPU (Linux/Windows)

```bash
cd cuda_fundamentals

# Compile
nvcc -std=c++17 src/01_hello_gpu.cu -o hello_gpu

# Run
./hello_gpu

# Expected output:
# Hello from GPU thread!
```

### Option 2: No GPU (macOS, but want to learn)

```bash
# Read the example code
cat src/01_hello_gpu.cu

# Understand the structure
# ✓ __global__ keyword (runs on GPU)
# ✓ blockIdx, threadIdx (parallel ID)
# ✓ cudaMalloc/cudaMemcpy/cudaFree (memory management)
```

### Option 3: Use Google Colab (Free GPU!)

1. Go to: https://colab.research.google.com
2. Create new notebook
3. Copy-paste code from `src/02_vector_add.cu`
4. Run in cloud with free GPU!

---

## Key Vocabulary

| Term | Meaning |
|------|---------|
| **Kernel** | Function that runs on GPU |
| **Thread** | Single execution of kernel |
| **Block** | Group of threads that work together |
| **Grid** | All blocks (all threads) |
| **Host** | CPU and RAM |
| **Device** | GPU and VRAM |
| **cudaMalloc** | Allocate GPU memory |
| **cudaMemcpy** | Transfer data CPU ↔ GPU |
| **cudaFree** | Free GPU memory |
| **<<<gridSize, blockSize>>>** | Launch kernel with configuration |

---

## Common Mistakes (Avoid These!)

❌ **Forgetting cudaMalloc**
```cuda
float *d_data;  // Uninitialized pointer!
cudaMemcpy(d_data, h_data, size, ...);  // CRASH!
```

✅ **Correct:**
```cuda
float *d_data;
cudaMalloc(&d_data, size);  // Allocate first
cudaMemcpy(d_data, h_data, size, ...);  // Now safe
```

---

❌ **Forgetting to copy data to GPU**
```cuda
float h_data[1000] = {...};  // CPU data
kernel<<<blocks, threads>>>(h_data);  // Pass CPU pointer!
// Kernel reads from CPU memory (WRONG! Very slow)
```

✅ **Correct:**
```cuda
cudaMemcpy(d_data, h_data, size, cudaMemcpyHostToDevice);
kernel<<<blocks, threads>>>(d_data);  // Pass GPU pointer
```

---

❌ **Accessing same memory from multiple blocks**
```cuda
__global__ void kernel() {
    // Multiple blocks might access shared memory simultaneously
    // Need synchronization!
}
```

✅ **Correct:** Use `__syncthreads()` within blocks, or use atomic operations

---

## Next Steps

1. **Read CUDA_BASICS.md** (20 min) — Understand GPU architecture
2. **Compile 02_vector_add.cu** — See parallel code in action
3. **Modify examples** — Change array sizes, see performance
4. **Read MEMORY_MANAGEMENT.md** — Deep dive on GPU memory
5. **Write your own kernel** — Matrix multiplication, dot product

---

## Map C++ Knowledge → CUDA

**C++ Concept You Know → CUDA Equivalent You'll Learn**

```
for loop (sequential)
    ↓
Kernel launch (parallel)
    - Each thread is like 1 iteration
    - 1000 iterations → 1000 threads
    - All run simultaneously!

malloc/free (CPU memory)
    ↓
cudaMalloc/cudaFree (GPU memory)
    - Same concept, different device

Function call
    ↓
Kernel launch
    - kernel<<<gridSize, blockSize>>>(args)
    - Runs function 1000x in parallel
```

---

## Do You Need NVIDIA GPU to Learn?

**No!** But it helps:

| Have GPU | How to Learn |
|----------|-------------|
| ✅ Linux/Windows with NVIDIA GPU | Run examples locally, instant feedback |
| ❌ macOS (no NVIDIA support) | Use Google Colab (free cloud GPU) |
| ❌ No GPU | Learn theory + syntax, run on Colab later |

**Google Colab is free and has real NVIDIA GPUs!** Use it.

---

## This Took 5 Minutes

You now understand:
✅ What CUDA is (GPU programming)
✅ The 5-step CUDA pattern
✅ Kernels and thread organization
✅ How to compile with nvcc
✅ Memory management (GPU-specific)

**Next:** Read CUDA_BASICS.md (20 min) for deep dive.

---

## Quick Reference

```bash
# Compile CUDA
nvcc -std=c++17 program.cu -o program

# Memory management pattern
cudaMalloc(&device_ptr, size);
cudaMemcpy(device_ptr, host_ptr, size, cudaMemcpyHostToDevice);
kernel<<<gridSize, blockSize>>>(device_ptr);
cudaMemcpy(host_ptr, device_ptr, size, cudaMemcpyDeviceToHost);
cudaFree(device_ptr);

# Kernel basics
__global__ void kernel() {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    // Each thread does something here
}
```

Welcome to GPU programming! 🚀

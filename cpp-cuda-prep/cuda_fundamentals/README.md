# CUDA Fundamentals — GPU Programming Basics

Welcome to GPU programming! This folder teaches you CUDA (Compute Unified Device Architecture) — how to write programs that run on NVIDIA GPUs.

**Prerequisites:** You've completed the C++ fundamentals (../). Go back and finish those first if you haven't!

---

## What is CUDA?

**CUDA = Compute Unified Device Architecture**

CUDA is a platform for writing programs that run on NVIDIA GPUs instead of CPUs.

### CPU vs GPU: The Key Difference

**CPU (Your Current Knowledge)**
```
1 processor
↓
Does 1 task at a time (or ~8-16 with modern CPUs)
↓
Good for: General computation, decision-making
```

**GPU (What We're Learning)**
```
1000s of processors
↓
Does 1000s of tasks simultaneously (in parallel)
↓
Good for: Massive parallel computation, matrix math, graphics
```

### Example: Adding Two Arrays

**CPU Version (Sequential)**
```cpp
// Add 1,000,000 numbers
for (int i = 0; i < 1000000; i++) {
    result[i] = a[i] + b[i];
}
// Takes: ~1 millisecond (1 core), or ~0.1ms (10 cores in parallel)
```

**GPU Version (Parallel)**
```cuda
// Same addition, but GPU has 1000 cores
// Each core does 1 addition simultaneously
// 1,000,000 / 1000 cores = 1000 additions per "round"
// Takes: ~0.001 milliseconds (1000x faster!)
```

---

## Why Learn CUDA?

1. **Speed:** 10-100x faster for parallel tasks
2. **Career:** NVIDIA GPUs everywhere (AI, crypto, gaming, science)
3. **Foundation:** Understanding GPU programming transfers to other platforms (HIP, OpenCL, Metal)
4. **Your Interview Prep:** ML System Design often involves GPU optimization

---

## What You'll Learn Here

### Folder Structure

```
cuda_fundamentals/
├─ README.md                    (you are here)
├─ QUICK_START.md               (5-min entry)
├─ CUDA_BASICS.md               (fundamentals)
├─ COMPILATION.md               (how to build CUDA)
├─ MEMORY_MANAGEMENT.md         (CPU ↔ GPU memory)
├─ THREADS_BLOCKS_GRIDS.md      (parallel organization)
│
├─ src/                         (CUDA code examples)
│  ├─ 01_hello_gpu.cu           (first kernel)
│  ├─ 02_vector_add.cu          (parallel addition)
│  ├─ 03_memory_transfer.cu     (CPU ↔ GPU)
│  └─ utils.cu                  (helper functions)
│
├─ include/
│  └─ cuda_utils.h              (utilities)
│
├─ cpu_vs_gpu/                  (compare approaches)
│  ├─ add_cpu.cpp               (CPU version)
│  ├─ add_gpu.cu                (GPU version)
│  └─ COMPARISON.md             (analysis)
│
└─ Makefile                     (build system)
```

### Learning Path

**Week 1: CUDA Basics**
- [ ] Read QUICK_START.md (5 min)
- [ ] Understand GPU architecture (CUDA_BASICS.md)
- [ ] Compile and run 01_hello_gpu.cu
- [ ] Understand what a "kernel" is

**Week 2: Core Concepts**
- [ ] Memory management (MEMORY_MANAGEMENT.md)
- [ ] Threads, blocks, grids (THREADS_BLOCKS_GRIDS.md)
- [ ] Run 02_vector_add.cu
- [ ] Modify examples

**Week 3: Practical Applications**
- [ ] Memory transfer (03_memory_transfer.cu)
- [ ] Compare CPU vs GPU versions
- [ ] Benchmark performance
- [ ] Write your own kernel

---

## Prerequisites & Setup

### Do You Have NVIDIA GPU?

This matters! CUDA requires NVIDIA hardware.

```bash
# Check if you have NVIDIA GPU (macOS won't show this)
nvidia-smi

# On macOS (Apple Silicon/Intel):
# NVIDIA GPUs are NOT supported on macOS anymore
# But you can still learn CUDA theory and syntax
# Options: Use cloud (Google Colab), or dual-boot Linux
```

### Install CUDA Toolkit

**Linux/Windows:**
1. Download from: https://developer.nvidia.com/cuda-downloads
2. Install CUDA Toolkit
3. Verify: `nvcc --version`

**macOS:**
- ❌ NVIDIA GPUs don't work on macOS
- ✓ But you can still learn CUDA syntax and theory
- ✓ Use Google Colab (free, cloud-based NVIDIA GPU)

---

## Key Concepts (Quick Overview)

### 1. Kernel: A Function That Runs on GPU

```cuda
// This runs on GPU, 1000s of times in parallel
__global__ void add(float *a, float *b, float *result, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        result[i] = a[i] + b[i];
    }
}
```

**`__global__`** = This function runs on GPU

### 2. Thread Blocks and Grids

GPU organizes parallel work as:
```
Grid (all work)
├─ Block 0 (group of threads)
│  ├─ Thread 0
│  ├─ Thread 1
│  └─ ...
├─ Block 1
│  ├─ Thread 0
│  ├─ Thread 1
│  └─ ...
└─ ...
```

### 3. Memory Hierarchy

```
CPU Memory                GPU Memory
(Your RAM)               (VRAM)
    ↓                        ↓
Regular memory           GPU VRAM
(Host)                   (Device)
    ↑←→ cudaMemcpy ←→↓
```

### 4. Typical CUDA Program Flow

```
1. Allocate GPU memory      (cudaMalloc)
2. Copy data CPU → GPU      (cudaMemcpy)
3. Launch kernel on GPU     (kernel<<<blocks, threads>>>())
4. Copy results GPU → CPU   (cudaMemcpy)
5. Free GPU memory          (cudaFree)
```

**This is EXACTLY the pattern from C++ new/delete!** Just on GPU instead.

---

## Map C++ Knowledge to CUDA

### C++ (What You Know) → CUDA (What You'll Learn)

| C++ Concept | CUDA Equivalent | Purpose |
|------------|-----------------|---------|
| `new` allocate memory | `cudaMalloc` | Allocate GPU memory |
| `delete` free memory | `cudaFree` | Free GPU memory |
| Regular function | `__global__` kernel | Function running on GPU |
| `for` loop (sequential) | Parallel threads | Execute 1000s simultaneously |
| `std::cout` | `printf` (in kernel) | Debug output from GPU |
| Function parameter | Kernel argument | Pass data to GPU function |

**Good news:** You already know 90% of the concepts! Just GPU-specific syntax.

---

## CUDA vs Your C++ Learning

### Similarities

✅ Same compilation pipeline (just different compiler: nvcc instead of clang++)
✅ Same memory model (malloc/free, just on different device)
✅ Same function concepts (kernels are just functions)
✅ Same optimization thinking (threads = parallel for loops)

### Differences

❌ Special keywords (`__global__`, `__device__`, `<<<...>>>`)
❌ Thread indexing (calculating which thread you are)
❌ Memory synchronization (waiting for all threads)
❌ Different hardware constraints (1000 threads vs 1 CPU)

---

## Quick Fact Check: Will You Understand This?

**After C++ fundamentals, you already know:**
- ✅ Memory allocation/deallocation
- ✅ Function concepts
- ✅ Loops and iterations
- ✅ Arrays and pointers
- ✅ Compilation process (how clang++ works)

**You'll learn here:**
- 🆕 GPU-specific syntax
- 🆕 Parallel thinking (1000 threads at once)
- 🆕 GPU memory management (different from CPU)
- 🆕 Thread synchronization

---

## Example: Your First CUDA Program

### What It Does
Add two arrays using GPU instead of CPU:

```cuda
// On GPU: Each thread adds one pair of numbers
__global__ void add(float *a, float *b, float *result, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) result[i] = a[i] + b[i];
}

// Main CPU code
int main() {
    // 1. Allocate GPU memory
    float *d_a, *d_b, *d_result;
    cudaMalloc(&d_a, size);
    cudaMalloc(&d_b, size);
    cudaMalloc(&d_result, size);
    
    // 2. Copy data to GPU
    cudaMemcpy(d_a, h_a, size, cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, h_b, size, cudaMemcpyHostToDevice);
    
    // 3. Launch kernel (256 threads per block, enough blocks for all data)
    int blockSize = 256;
    int gridSize = (n + blockSize - 1) / blockSize;
    add<<<gridSize, blockSize>>>(d_a, d_b, d_result, n);
    
    // 4. Copy results back to CPU
    cudaMemcpy(h_result, d_result, size, cudaMemcpyDeviceToHost);
    
    // 5. Free GPU memory
    cudaFree(d_a);
    cudaFree(d_b);
    cudaFree(d_result);
    
    return 0;
}
```

Notice the pattern: **Allocate → Copy → Compute → Copy Back → Free**

This is identical to the new/delete pattern you learned in C++!

---

## How to Use This Folder

### Option 1: Quick Start (15 minutes)

```bash
cd cuda_fundamentals
cat QUICK_START.md
```

### Option 2: Complete Learning (3-4 hours)

```bash
# Read in order
cat CUDA_BASICS.md           # 20 min
cat MEMORY_MANAGEMENT.md      # 20 min
cat THREADS_BLOCKS_GRIDS.md   # 20 min
cat COMPILATION.md            # 10 min

# Then compile and run examples
make run-01
make run-02
make run-03
```

### Option 3: Without GPU (Theory Only)

If you don't have NVIDIA GPU:

```bash
# Read all documentation
cat *.md

# Review code examples (read, don't run)
cat src/*.cu

# Use Google Colab for hands-on practice
# See QUICK_START.md for Colab link
```

---

## Success Criteria: You're Ready When...

✅ You understand what a CUDA kernel is
✅ You can explain thread blocks and grids
✅ You know the 5-step CUDA program pattern
✅ You can read and modify `02_vector_add.cu`
✅ You understand memory transfer (CPU ↔ GPU)
✅ You can calculate how many threads you need

---

## Resources

### Official NVIDIA
- CUDA Programming Guide: https://docs.nvidia.com/cuda/cuda-c-programming-guide/
- CUDA Best Practices: https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/
- Code Examples: https://github.com/NVIDIA/cuda-samples

### Learning
- Intro to CUDA: https://developer.nvidia.com/blog/even-easier-introduction-cuda/
- NVIDIA Educational Materials: https://developer.nvidia.com/cuda-education

### Cloud (No GPU Needed)
- Google Colab (free GPU!): https://colab.research.google.com
- Kaggle Notebooks (free GPU): https://www.kaggle.com/code

---

## Next Step

Start with: **QUICK_START.md** (5-minute entry)

Or jump to theory: **CUDA_BASICS.md** (complete fundamentals)

Welcome to GPU programming! 🚀

---

## File Glossary

| File | Purpose |
|------|---------|
| QUICK_START.md | 5-minute overview, how to run examples |
| CUDA_BASICS.md | GPU architecture, kernels, core concepts |
| MEMORY_MANAGEMENT.md | CPU ↔ GPU memory, cudaMalloc/Free/Memcpy |
| THREADS_BLOCKS_GRIDS.md | How GPU organizes parallel work |
| COMPILATION.md | How to compile CUDA with nvcc |
| 01_hello_gpu.cu | Simplest CUDA program |
| 02_vector_add.cu | Parallel vector addition |
| 03_memory_transfer.cu | CPU ↔ GPU communication |
| cpu_vs_gpu/COMPARISON.md | CPU vs GPU performance |
| Makefile | Build system for CUDA |

# CUDA Basics: GPU Architecture & Programming Model

Deep dive into how CUDA works and why GPUs are fast.

---

## Part 1: GPU Hardware (Why GPUs are Fast)

### CPU vs GPU Architecture

**CPU (What You're Used To)**
```
┌─ Core 1 ─┐  ┌─ Core 2 ─┐  ┌─ Core 3 ─┐  ┌─ Core 4 ─┐
│ Complex  │  │ Complex  │  │ Complex  │  │ Complex  │
│ Control  │  │ Control  │  │ Control  │  │ Control  │
│ Large    │  │ Large    │  │ Large    │  │ Large    │
│ Cache    │  │ Cache    │  │ Cache    │  │ Cache    │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
  ↓              ↓              ↓              ↓
  4 cores doing 4 different things
  (each core is very powerful)
```

**GPU (What We're Learning)**
```
┌─ Core 1 ─┐  ┌─ Core 2 ─┐  ┌─ Core 3 ─┐  ┌─ Core 4 ─┐  ... × 250
│ Simple   │  │ Simple   │  │ Simple   │  │ Simple   │
│ ALU      │  │ ALU      │  │ ALU      │  │ ALU      │
│ Small    │  │ Small    │  │ Small    │  │ Small    │
│ Cache    │  │ Cache    │  │ Cache    │  │ Cache    │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
  ↓              ↓              ↓              ↓
  1000 cores all doing the SAME thing
  (each core is simple, but lots of them)
```

### The Trade-Off

| CPU | GPU |
|-----|-----|
| Few cores (4-16) | Many cores (1000+) |
| Each core is powerful | Each core is simple |
| Can do different things | All do the same thing |
| Good for: Decision-making | Good for: Parallel computation |

---

## Part 2: CUDA Programming Model

### Abstraction: Kernels, Blocks, Grids

When you write a CUDA kernel, you don't think about individual cores. Instead:

```
Grid (logical concept)
├─ Block 0
│  ├─ Thread 0
│  ├─ Thread 1
│  ├─ Thread 2
│  └─ ... × 256
├─ Block 1
│  ├─ Thread 0
│  ├─ Thread 1
│  ├─ Thread 2
│  └─ ... × 256
└─ Block 2 (and so on)
```

**Key insight:** You launch kernels with thread organization, not with cores.

---

### Understanding Block Size & Grid Size

```cuda
// Kernel launch
kernel<<<gridSize, blockSize>>>(args);

// Example
kernel<<<100, 256>>>(args);
// Meaning: Launch 100 blocks, each with 256 threads
// Total: 100 * 256 = 25,600 threads
```

**Inside kernel:**
```cuda
__global__ void kernel(...) {
    // Find which thread you are
    int threadId = blockIdx.x * blockDim.x + threadIdx.x;
    
    // Only threads 0-24,599 exist
    // Thread 0 (block 0, thread 0)
    // Thread 1 (block 0, thread 1)
    // ...
    // Thread 256 (block 1, thread 0)
    // ...
    // Thread 25,599 (block 99, thread 255)
}
```

---

### How Work Gets Distributed

**Your code:**
```cuda
// Add 1,000,000 numbers
add<<<3906, 256>>>(d_a, d_b, d_result, 1000000);
```

**What happens:**
1. GPU creates 3906 blocks
2. Each block has 256 threads
3. Total: 1,000,000+ threads
4. Each thread runs `add()` once
5. Inside, thread calculates: `int i = blockIdx.x * blockDim.x + threadIdx.x;`
   - Thread 0: i = 0
   - Thread 1: i = 1
   - Thread 256: i = 256
   - Thread 257 (block 1, thread 1): i = 257
   - ...
   - Thread 999,999: i = 999,999

**Result:** Each number gets added by exactly one thread!

---

## Part 3: Memory Hierarchy

### Three Types of Memory

**1. Global Memory (Largest, Slowest)**
```cuda
float d_array[1000];  // This is global memory (VRAM)
// Accessible by all threads
// Slow (~100 cycles to access)
// Large (GB+)
```

**2. Shared Memory (Medium, Medium Speed)**
```cuda
__shared__ float shared_buffer[256];  // Only within one block
// All threads in block can access
// Fast (~10 cycles to access)
// Small (48 KB per block)
```

**3. Local Memory (Each Thread)**
```cuda
__global__ void kernel() {
    float local_var = 5.0f;  // Only this thread can access
    // In thread's own registers
    // Extremely fast (~1 cycle)
    // Very small (per-thread)
}
```

### Memory Bandwidth

```
GPU VRAM
  ↓
Huge bandwidth (100+ GB/s)
  ↓
Perfect for parallel access
```

vs

```
CPU RAM
  ↓
Lower bandwidth (~10 GB/s)
  ↓
Sequential access optimal
```

**Why GPUs are fast:** Each of 1000 cores accesses memory in parallel!

---

## Part 4: Synchronization

### Problem: Race Conditions

```cuda
__global__ void bad_kernel() {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    
    // What if two threads access same memory?
    global_counter++;  // RACE CONDITION!
    // Two threads might read 5, increment to 6, write 6
    // Should be 7, but one increment was lost!
}
```

### Solution 1: __syncthreads()

```cuda
__global__ void sync_kernel() {
    __shared__ int block_sum = 0;
    
    // Compute partial sum
    int partial = compute();
    
    // Wait for all threads in block
    __syncthreads();
    
    // Now safe to use block_sum
    atomicAdd(&block_sum, partial);
}
```

### Solution 2: Atomic Operations

```cuda
__global__ void atomic_kernel() {
    // Atomic: happens without interference
    atomicAdd(&global_counter, 1);  // Safe!
}
```

---

## Part 5: CUDA Execution Model

### What Happens When You Launch a Kernel

```
Step 1: Copy data CPU → GPU
Step 2: Queue kernel for execution
Step 3: GPU schedules threads
Step 4: Threads execute (potentially 1000s in parallel)
Step 5: Kernel returns to CPU
Step 6: Copy results GPU → CPU
```

### Important: Asynchronous Execution

```cuda
kernel<<<blocks, threads>>>(args);  // Returns immediately
// CPU continues here, GPU is still computing!

cudaMemcpy(...);  // This WAITS for kernel to finish
```

**Default behavior:** cudaMemcpy blocks until GPU finishes.

---

## Part 6: Common Kernel Patterns

### Pattern 1: Element-wise Operation

```cuda
__global__ void elementwise(float *a, float *b, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        b[i] = f(a[i]);  // Each thread operates on one element
    }
}
```

**Usage:** Adding arrays, scaling, applying functions element-by-element

### Pattern 2: Reduction (Sum All Elements)

```cuda
__global__ void reduce_sum(float *input, float *output, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    
    __shared__ float shared[256];
    
    // Load into shared memory
    if (i < n)
        shared[threadIdx.x] = input[i];
    else
        shared[threadIdx.x] = 0;
    
    __syncthreads();
    
    // Parallel reduction
    for (int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (threadIdx.x < s) {
            shared[threadIdx.x] += shared[threadIdx.x + s];
        }
        __syncthreads();
    }
    
    // Write result
    if (threadIdx.x == 0) {
        atomicAdd(output, shared[0]);
    }
}
```

**Usage:** Sum array, find max, find min, count elements

### Pattern 3: Broadcast

```cuda
__global__ void broadcast(float *data, float scalar, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        data[i] *= scalar;  // All threads multiply by same value
    }
}
```

**Usage:** Scaling vector, multiplying matrix by constant

---

## Part 7: Error Checking (Critical!)

CUDA operations can silently fail. Always check:

```cuda
// Memory allocation
cudaError_t err = cudaMalloc(&d_data, size);
if (err != cudaSuccess) {
    printf("cudaMalloc failed: %s\n", cudaGetErrorString(err));
    return;
}

// Kernel execution
kernel<<<blocks, threads>>>(args);
err = cudaGetLastError();
if (err != cudaSuccess) {
    printf("Kernel failed: %s\n", cudaGetErrorString(err));
    return;
}

// Wait and check (optional)
err = cudaDeviceSynchronize();
if (err != cudaSuccess) {
    printf("Device error: %s\n", cudaGetErrorString(err));
    return;
}

// Memory copy
err = cudaMemcpy(h_data, d_data, size, cudaMemcpyDeviceToHost);
if (err != cudaSuccess) {
    printf("cudaMemcpy failed: %s\n", cudaGetErrorString(err));
    return;
}

// Cleanup
err = cudaFree(d_data);
if (err != cudaSuccess) {
    printf("cudaFree failed: %s\n", cudaGetErrorString(err));
}
```

**Always add error checking in production code!**

---

## Part 8: Performance Considerations

### Occupancy

**Occupancy = (Threads Running) / (Threads GPU Can Support)**

```
GPU can support 1024 threads per block
You launch 256 threads per block
Occupancy = 256/1024 = 25%
Wasted potential!

Better: Launch 512 threads per block
Occupancy = 512/1024 = 50%
```

**Higher occupancy = better GPU utilization**

### Memory Access Patterns

**Coalesced Access (Good!)**
```cuda
for (int i = threadIdx.x; i < n; i += blockDim.x) {
    // Threads access consecutive memory
    // GPU can fetch all at once
    // Fast!
}
```

**Non-coalesced Access (Bad!)**
```cuda
for (int i = 0; i < n; i++) {
    data[threadIdx.x + i * blockDim.x];  // Scattered access
    // GPU must fetch from different parts of memory
    // Slow!
}
```

### Memory Bandwidth Utilization

```
Peak GPU bandwidth: 100+ GB/s
Your kernel's effective bandwidth: measure it!

// Simple metric
bytes_transferred = n_threads * bytes_per_thread
time_seconds = kernel_time
bandwidth = bytes_transferred / time_seconds

If << 100 GB/s: you're memory-bound (optimize memory access)
If >> 100 GB/s: something's wrong (can't exceed hardware limit)
```

---

## Part 9: Common Mistakes & Solutions

### Mistake 1: Wrong Memory Access

```cuda
❌ WRONG
cudaMemcpy(host_data, device_data, size, cudaMemcpyHostToHost);

✅ CORRECT
cudaMemcpy(host_data, device_data, size, cudaMemcpyDeviceToHost);
```

### Mistake 2: Not Enough Threads

```cuda
❌ WRONG
kernel<<<1, 1>>>(data, 1000000);  // Only 1 thread for 1M elements!

✅ CORRECT
kernel<<<4000, 256>>>(data, 1000000);  // 1M threads
```

### Mistake 3: Forgetting Edge Cases

```cuda
❌ WRONG
__global__ void kernel(float *data, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    data[i] = compute();  // What if i >= n?
}

✅ CORRECT
__global__ void kernel(float *data, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        data[i] = compute();
    }
}
```

### Mistake 4: Race Conditions

```cuda
❌ WRONG
__shared__ int counter = 0;
counter++;  // Multiple threads increment = race condition

✅ CORRECT
__shared__ int counter = 0;
atomicAdd(&counter, 1);  // Thread-safe
```

---

## Part 10: Workflow & Best Practices

### Development Workflow

1. **Write CPU version first** — Understand the algorithm
2. **Verify CPU version works** — Get correct results
3. **Profile CPU version** — Know baseline performance
4. **Convert to GPU** — Apply parallelism
5. **Verify GPU version matches CPU** — Correctness
6. **Measure GPU performance** — Compare speedup

### Best Practices

✅ Always initialize GPU memory
✅ Always check for errors
✅ Start with simple kernels, optimize later
✅ Profile before optimizing
✅ Use right data types (float32 usually fine for ML)
✅ Consider memory bandwidth
✅ Test edge cases
✅ Keep CPU version for validation

---

## Summary Table

| Concept | CPU | GPU |
|---------|-----|-----|
| Cores | 4-16 | 1000+ |
| Work Model | Sequential | Parallel |
| Memory | RAM | VRAM |
| Functions | Regular functions | Kernels (`__global__`) |
| Synchronization | Implicit | Explicit (`__syncthreads`) |
| Speed | Fast (per-core) | Slow (per-core) but massive throughput |
| Best For | Logic, decisions | Math, data-parallel |

---

## Map to Interview Questions

**"Explain GPU memory hierarchy"**
→ Global (slow, large) → Shared (medium) → Local (fast, small)

**"When would you use GPU vs CPU?"**
→ GPU for parallel data-processing, CPU for sequential logic

**"What's occupancy?"**
→ Percentage of GPU threads actually running (higher = better)

**"What's coalesced memory access?"**
→ Threads accessing consecutive memory locations (fast)

---

## Next Steps

1. Read MEMORY_MANAGEMENT.md — Deep dive on memory
2. Read THREADS_BLOCKS_GRIDS.md — Thread organization
3. Read COMPILATION.md — How to compile CUDA
4. Compile examples and modify them
5. Benchmark your changes

---

## Key Takeaway

CUDA exposes GPU parallelism through:
- **Kernels:** Functions running on GPU
- **Threads:** Parallel execution units
- **Blocks & Grids:** Organization of threads
- **Memory:** CPU memory vs GPU memory
- **Synchronization:** Coordinating 1000s of threads

You now understand the model. Practice makes the syntax automatic! 🚀

# Quick Start Guide for C++ CUDA Prep

## TL;DR - Run These Commands Now

```bash
cd /Users/surendrashukla/projects/2026/platform-lab/cpp_cuda_prep

# Build everything
make

# Run all examples
make run-all

# Or run individually
make run-01  # Hello World
make run-02  # Arrays & Memory
make run-03  # Functions & Lambdas

# Clean up compiled files
make clean
```

## What Just Happened?

You successfully:
1. ✅ Compiled C++ source code (`.cpp` files)
2. ✅ Linked object files (`.o`) with a library (`utils.o`)
3. ✅ Created executable programs
4. ✅ Ran them

This is **exactly the pattern CUDA uses**, just with GPU compilation added.

## The 3 Key Concepts for CUDA

### 1. Memory Management (Example 02)
```cpp
// Allocate memory
float* data = new float[1000];

// Use it
data[0] = 3.14f;

// Free it
delete[] data;
```

In CUDA, `new` → `cudaMalloc`, `delete` → `cudaFree`, but the pattern stays the same.

### 2. Parallel Functions (Example 03)
```cpp
// Function that might run in parallel
auto kernel = [](float x) { return x * 2; };

// In CUDA, thousands of GPU threads call this simultaneously
// Each thread: kernel(thread_id)
```

### 3. Data Transfer (Coming Next)
```
CPU Memory  →  Memcpy  →  GPU Memory
                         ↓
                    Run Kernel
                         ↓
GPU Memory  →  Memcpy  →  CPU Memory
```

## Next Learning Steps

### Week 1: Understand What You Just Ran

1. Read README.md (explains compilation process)
2. Modify an example:
   - Change array size in example 02
   - Add a new function in utils.cpp
   - Create a 04_your_own_example.cpp
3. Run `make run-all` to verify your changes compile

### Week 2: Dive Deeper

1. Understand pointers:
   - Modify example 02 to add pointer arithmetic
   - Print `sizeof(float*)`, `sizeof(float)`
   
2. Understand functions as data:
   - Add your own lambda to example 03
   - Pass different functions to `apply_function`

3. Try debugging:
   ```bash
   # Compile with debug symbols
   clang++ -g -std=c++17 src/01_hello_world.cpp -o build/hello_debug
   
   # Run with debugger (if lldb installed)
   lldb build/hello_debug
   (lldb) run
   (lldb) break set --file src/01_hello_world.cpp --line 5
   ```

### Week 3: Mini-Projects

1. **Matrix Multiply (CPU version)**
   - Write `matrix_multiply.cpp`
   - Allocate 3D arrays on heap
   - Implement C = A × B
   - This exact algorithm runs on GPU later

2. **Performance Measurement**
   - Time your matrix multiply
   - Compare different array sizes
   - Profile with `time ./program`

3. **Error Handling**
   - Add bounds checking
   - Validate inputs before using
   - Print meaningful error messages

## CUDA Timeline

```
Now (Week 1-3)          →  Intermediate (Week 4-6)     →  Advanced (Week 7+)
├─ C++ fundamentals        ├─ CUDA basics               ├─ Advanced kernels
├─ Memory management       ├─ GPU memory transfer       ├─ Optimization
├─ Pointer arithmetic      ├─ Kernel launching         ├─ Performance tuning
└─ Function concepts       ├─ Parallel thinking        └─ Real applications
                           └─ Thread indexing
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `make: command not found` | Install Make: `brew install make` (macOS) or `apt install make` (Linux) |
| `clang++: command not found` | Install clang: `brew install llvm` |
| Compile errors | Check line number in error, look at that line in code |
| Program crashes | Add `std::cout` statements to debug, or use `lldb` |
| Forgot how to use Make | Run `make debug` to see all variables |

## File Structure Cheat Sheet

```
cpp_cuda_prep/
├── src/              # Where you write your code (.cpp files)
├── include/          # Headers that declare functions (.h files)
├── build/            # Generated files (don't edit)
├── Makefile          # Build rules (describes how to compile)
└── README.md         # Full documentation
```

**Remember:** In CUDA, this becomes:
```
cuda_project/
├── src/
│   ├── kernel.cu     # GPU code
│   └── main.cpp      # CPU code
├── include/
│   └── kernel.h
├── Makefile          # Now calls nvcc (CUDA compiler)
└── README.md
```

## Commands to Memorize

```bash
# Navigate to project
cd cpp_cuda_prep

# Compile and run everything
make run-all

# Compile only (don't run)
make

# Run specific example
make run-02

# Delete build artifacts
make clean

# See what make will do
make -n run-all

# Compile one file manually
clang++ -std=c++17 -Wall -O2 -I./include src/01_hello_world.cpp -o build/hello

# Run a program
./build/hello

# Time a program
time ./build/02_arrays_memory

# List all build artifacts
ls -la build/
```

## Key Compiler Flags

| Flag | Meaning | Example |
|------|---------|---------|
| `-std=c++17` | C++17 standard | Required for modern features |
| `-Wall` | Show warnings | Catches mistakes |
| `-O2` | Optimize | Makes code faster |
| `-I./include` | Include path | Finds header files |
| `-c` | Compile only | Produces `.o` file |
| `-o output` | Output name | Specifies binary name |
| `-g` | Debug symbols | For stepping through code |

## One-Off Commands

```bash
# Compile and run without make
clang++ -std=c++17 -Wall -I./include src/02_arrays_memory.cpp src/utils.cpp -o /tmp/arrays && /tmp/arrays

# Compile multiple files separately
clang++ -c -std=c++17 -I./include src/utils.cpp -o /tmp/utils.o
clang++ -std=c++17 -I./include src/02_arrays_memory.cpp /tmp/utils.o -o /tmp/arrays && /tmp/arrays
```

## What to Try Right Now

1. **Change Example 02:** In `src/02_arrays_memory.cpp`, change `int size = 10;` to `int size = 1000;`
2. **Rebuild:** Run `make`
3. **See result:** Run `make run-02`
4. **Verify:** Notice the output shows 1000 elements

Then try:
5. **Edit utils:** Add a function `float max_array(const float* arr, int size)`
6. **Add to header:** Add declaration to `include/utils.h`
7. **Use it:** Call `max_array()` in one of the examples
8. **Rebuild:** `make clean && make run-02`

## Physics of C++ → CUDA Transition

When you learn CUDA, these C++ concepts map directly:

| C++ | CUDA | Why |
|-----|------|-----|
| `float* arr = new float[n]` | `cudaMalloc(&d_arr, n*sizeof(float))` | Allocate GPU memory |
| `arr[i] = value` | In kernel: `arr[i] = value` | Access memory |
| `delete[] arr` | `cudaFree(d_arr)` | Free GPU memory |
| `apply_function(arr, kernel)` | `kernel<<<blocks,threads>>>(arr)` | Launch parallel work |

You're learning the **CPU version** now. CUDA is the same logic on **GPU**.

---

**Your next checkpoint:** Modify example 02 and example 03, then create your own 04_combined_example.cpp that uses both arrays and lambdas. When that compiles and runs, you're ready for GPU concepts.

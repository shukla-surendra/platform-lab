# C++ Fundamentals for CUDA Programming

This project teaches C++ essentials needed for CUDA programming. Each example builds understanding progressively.

## Prerequisites

- **macOS:** `brew install llvm` (for clang compiler)
- **Linux:** `sudo apt install build-essential` (for g++/clang)
- **Windows:** MinGW or MSVC
- **Verify:** Run `clang++ --version`

## Project Structure

```
cpp_cuda_prep/
├── include/          # Header files (.h)
├── src/              # Source files (.cpp)
├── build/            # Compiled output (created by make)
├── Makefile          # Build rules
└── README.md         # This file
```

## How to Compile & Run

### Option 1: Compile Individually

```bash
# Navigate to project directory
cd cpp_cuda_prep

# Compile a single file (no dependencies on utils)
clang++ -std=c++17 -Wall -O2 src/01_hello_world.cpp -o build/hello
./build/hello

# Compile with header includes
clang++ -std=c++17 -Wall -O2 -I./include src/02_arrays_memory.cpp src/utils.cpp -o build/arrays
./build/arrays
```

### Option 2: Use Make (recommended)

```bash
cd cpp_cuda_prep

# Build all programs
make

# Run a single program
make run-01    # Runs 01_hello_world
make run-02    # Runs 02_arrays_memory
make run-03    # Runs 03_functions_lambdas

# Run all programs
make run-all

# Clean compiled files
make clean
```

### Option 3: Manual Compilation (step-by-step)

```bash
# Step 1: Compile source files to object files (.o)
clang++ -std=c++17 -Wall -O2 -I./include -c src/utils.cpp -o build/utils.o

# Step 2: Link object files with main program
clang++ -std=c++17 build/utils.o src/02_arrays_memory.cpp -o build/arrays

# Step 3: Run
./build/arrays
```

## Understanding the Compilation Process

### Compilation vs. Linking

```
Source Code (.cpp)
       ↓
   Compiler (clang++/g++)
       ↓
Object Files (.o)
       ↓
   Linker
       ↓
Executable (a.out/program)
```

**Example workflow:**

```bash
# Compile: Convert .cpp to .o (checks syntax, generates machine code)
clang++ -c src/utils.cpp -o build/utils.o

# Link: Combine .o files into executable (connects symbols, resolves references)
clang++ build/utils.o src/02_arrays_memory.cpp -o build/program

# Run: Execute the binary
./build/program
```

## Compiler Flags Explained

| Flag | Meaning |
|------|---------|
| `-std=c++17` | Use C++17 standard |
| `-Wall` | Show all warnings |
| `-Wextra` | Show extra warnings |
| `-O2` | Optimize for speed |
| `-I./include` | Add include directory to search path |
| `-c` | Compile only (don't link) |
| `-o output` | Write result to `output` |

## Examples Overview

### 01_hello_world.cpp
**Concepts:** Main function, output, program return value

```cpp
int main() {
    std::cout << "Hello, C++!\n";
    return 0;  // 0 = success
}
```

**Key learning:** Every C++ program needs `main()` as entry point.

---

### 02_arrays_memory.cpp
**Concepts:** 
- Stack arrays (fixed size, auto cleanup)
- Heap arrays (dynamic, manual cleanup)
- Pointers and array access
- Memory allocation with `new`/`delete`

**Key learning:** CUDA requires heap memory allocation because:
- GPU memory is dynamic (depends on GPU)
- You must allocate, fill, transfer to GPU, then free
- This pattern is exactly like `new`/`delete`

```cpp
// Stack: size known at compile time
int arr[5] = {1, 2, 3, 4, 5};

// Heap: size known at runtime
float* arr = new float[size];
// ... use arr ...
delete[] arr;  // MUST cleanup
```

---

### 03_functions_lambdas.cpp
**Concepts:**
- Function pointers
- Lambda functions (anonymous functions)
- Passing functions as arguments
- Capturing values

**Key learning:** CUDA kernels are functions that run in parallel:

```cpp
// Traditional function as kernel
void kernel(float* data, int size) {
    for (int i = 0; i < size; ++i) {
        data[i] = data[i] * 2;  // Each GPU thread does this
    }
}

// Lambda as kernel
auto kernel = [](float x) { return x * 2; };
```

## Path to CUDA Programming

Once comfortable with these examples:

1. **Understand pointers deeply** → Pointers to GPU memory
2. **Master memory management** → CPU vs GPU memory layout
3. **Learn about parallel thinking** → Thousands of threads simultaneously
4. **Study thread indexing** → `blockIdx`, `threadIdx` in CUDA

### CUDA Kernel Pattern

```cuda
// CPU memory
float* h_data = new float[1000];  // h_ = host

// GPU memory
float* d_data;
cudaMalloc(&d_data, 1000 * sizeof(float));

// Launch kernel: each GPU thread executes kernel()
kernel<<<blocks, threads>>>(d_data);

// Cleanup
cudaFree(d_data);
delete[] h_data;
```

## Troubleshooting

### Compilation Errors

**"command not found: clang++"**
- macOS: `brew install llvm`
- Linux: `sudo apt install clang`

**"undefined reference to..."**
- Missing object file in link step
- Check Makefile links all `.o` files needed

**"no such file or directory"**
- Include path wrong, use `-I./include`
- Check file paths match actual structure

### Runtime Errors

**"Segmentation fault"**
- Accessing memory you don't own
- Forgetting to allocate with `new`
- Accessing out-of-bounds indices

**"Floating point exception"**
- Division by zero
- Integer overflow

## Next Steps

1. ✅ Run all three examples with `make run-all`
2. ✅ Modify an example (e.g., change array size in 02)
3. ✅ Create your own simple function in utils
4. ✅ Write a fourth example using utils
5. → Move to CUDA when comfortable with pointers/memory

## Useful Commands

```bash
# Check if executable was created
ls -la build/

# Run with timing
time ./build/02_arrays_memory

# Run with debug output (add std::cerr in code)
./build/02_arrays_memory 2>&1 | head -20

# See what make would do (dry run)
make -n run-all
```

## C++ Standard Library Reference

### Input/Output
```cpp
#include <iostream>
std::cout << "output\n";  // Write to stdout
std::cin >> variable;      // Read from stdin
```

### Vectors (dynamic arrays)
```cpp
#include <vector>
std::vector<int> v = {1, 2, 3};
v.push_back(4);           // Add element
std::cout << v[0];        // Access element
std::cout << v.size();    // Get size
```

### Functions
```cpp
void print(int x) { std::cout << x << "\n"; }
int add(int a, int b) { return a + b; }
float (*fn_ptr)(float) = &square;  // Function pointer
```

## Key Takeaways for CUDA

| Concept | C++ | CUDA | Why |
|---------|-----|------|-----|
| Memory allocation | `new`/`delete` | `cudaMalloc`/`cudaFree` | GPU needs explicit allocation |
| Parallel function | Lambda/pointer | Kernel `__global__` | Runs thousands of times simultaneously |
| Array indexing | `arr[i]` | `blockIdx.x * blockDim.x + threadIdx.x` | Each thread needs a unique index |
| Data transfer | Pointer passed | `cudaMemcpy` | CPU memory ≠ GPU memory |

## References

- [Cppreference.com](https://en.cppreference.com/) — C++ standard library docs
- [isocpp.org](https://isocpp.org/) — C++ language standard
- [NVIDIA CUDA Docs](https://docs.nvidia.com/cuda/) — Start here for CUDA

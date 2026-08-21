# Manual C++ Compilation Guide (Without Make)

This guide shows exactly how to compile C++ programs manually, step-by-step.

---

## TL;DR: One-Liner Compilation

### Simplest Way (Single File)

```bash
clang++ -std=c++17 src/01_hello_world.cpp -o hello_world
./hello_world
```

### With Multiple Files (Linking)

```bash
clang++ -std=c++17 -I./include src/02_arrays_memory.cpp src/utils.cpp -o arrays
./arrays
```

---

## The Compilation Pipeline (What Actually Happens)

When you compile C++, there are really **4 stages**:

```
Source Code (.cpp)
       ↓
   1. PREPROCESSOR
   (handles #include, #define)
       ↓
Expanded Source
       ↓
   2. COMPILER
   (converts to assembly)
       ↓
Assembly Code (.s)
       ↓
   3. ASSEMBLER
   (converts to machine code)
       ↓
Object Files (.o)
       ↓
   4. LINKER
   (combines .o files, resolves symbols)
       ↓
Executable (binary)
```

**Most compilers combine steps 1-3 automatically.** We just run `clang++` once and it does all of them.

---

## Example 1: Simplest Program (One File)

### Program: 01_hello_world.cpp

```cpp
#include <iostream>

int main() {
    std::cout << "Hello, C++!\n";
    return 0;
}
```

### Method 1: Single Command (Simplest)

```bash
clang++ -std=c++17 src/01_hello_world.cpp -o hello_world
./hello_world
```

**What this does:**
1. Reads `src/01_hello_world.cpp`
2. Preprocesses it (`#include <iostream>` → expand)
3. Compiles to assembly
4. Assembles to machine code
5. Links (no other files needed)
6. Creates executable `hello_world`

**Output:**
```
Hello, C++!
```

---

### Method 2: Step-by-Step (See Each Stage)

#### Step 1: Preprocess Only

```bash
clang++ -std=c++17 -E src/01_hello_world.cpp -o hello_preprocessed.i
```

**Creates:** `hello_preprocessed.i` (preprocessed source, ~1000 lines!)

```bash
head -20 hello_preprocessed.i
```

**What you see:** All `#include` directives expanded (iostream header is ~1000 lines!)

---

#### Step 2: Compile to Assembly

```bash
clang++ -std=c++17 -S src/01_hello_world.cpp -o hello.s
cat hello.s
```

**Creates:** `hello.s` (assembly code, human-readable!)

**Output (simplified):**
```asm
	.section	__TEXT,__text,regular,pure_instructions
	.build_version macos, 14, 0 sdk_version 14, 4
	.globl	_main                   ; -- Begin function main
	.p2align	2
_main:                                  ; @main
	.cfi_startproc
; %bb.0:
	sub	sp, sp, #16
	.cfi_def_cfa_offset 16
	mov	w0, #0
	str	w0, [sp, #12]
	adrp	x0, l_.str@PAGE
	add	x0, x0, l_.str@PAGE_OFF
	bl	_ZNSt3__14coutE6insertI7chartraitsIcEEERNS_13basic_ostreamIT_T0_EES6_PKc
	...
```

This is the actual ARM64 assembly that will run on your Mac!

---

#### Step 3: Assemble to Machine Code (.o file)

```bash
clang++ -std=c++17 -c src/01_hello_world.cpp -o hello.o
file hello.o
```

**Creates:** `hello.o` (object file, binary!)

**Output:**
```
hello.o: Mach-O 64-bit object arm64
```

You can't read this directly (it's binary), but tools can:

```bash
# See symbols in object file
nm hello.o

# Output:
# 0000000000000000 T _main
# U _ZNSt3__14coutE
# U _ZNSt3__124__put_character_sequenceIcNS_11char_traitsIcEEEERNS_13basic_ostreamIT_T0_EES7_PKS4_m
```

---

#### Step 4: Link to Executable

```bash
clang++ -std=c++17 hello.o -o hello_world
./hello_world
```

**Creates:** `hello_world` (executable!)

**Output:**
```
Hello, C++!
```

---

### Summary: All Stages Combined

```bash
# All 4 stages in one command
clang++ -std=c++17 src/01_hello_world.cpp -o hello_world

# Or in separate steps (what clang++ is doing internally)
clang++ -std=c++17 -E src/01_hello_world.cpp -o hello.i    # Preprocess
clang++ -std=c++17 -S hello.i -o hello.s                   # Compile
clang++ -std=c++17 -c hello.s -o hello.o                   # Assemble
clang++ -std=c++17 hello.o -o hello_world                  # Link
./hello_world
```

---

## Example 2: Multiple Files (More Complex)

### Program: 02_arrays_memory.cpp (uses utils.cpp)

**File structure:**
```
src/
├── 02_arrays_memory.cpp (uses functions from utils)
└── utils.cpp (defines functions)

include/
└── utils.h (declares functions)
```

### The Problem: Linking Multiple Files

When `02_arrays_memory.cpp` has:
```cpp
#include "../include/utils.h"
...
print_array(stack_array, 5, "Stack array");
```

It **calls** `print_array()`, which is **defined in** `utils.cpp`.

Compiler needs to know:
1. Function declaration exists (from utils.h header)
2. Function implementation exists (in utils.cpp)

---

### Solution: Compile Both Files Together

#### Method 1: One Command (Simplest)

```bash
clang++ -std=c++17 -I./include \
  src/02_arrays_memory.cpp src/utils.cpp \
  -o arrays

./arrays
```

**What happens:**
1. Compile `02_arrays_memory.cpp` → `02_arrays_memory.o`
2. Compile `utils.cpp` → `utils.o`
3. Link both `.o` files together
4. Create `arrays` executable

**Output:**
```
=== STACK ARRAYS (automatic cleanup) ===
Stack array: [10, 20, 30, 40, 50]
Sum: 150
...
```

**Why `-I./include`?**
- Tells compiler where to find `utils.h`
- `-I` = "Include directory"
- Compiler looks for headers in `./include/`

---

#### Method 2: Separate Compilation, Then Link

**Why do this?** If you change only one file, you only recompile that one file (faster!)

##### Step 1: Compile Each File to Object File

```bash
# Compile 02_arrays_memory.cpp to object file
clang++ -std=c++17 -I./include -c src/02_arrays_memory.cpp -o arrays_main.o

# Compile utils.cpp to object file
clang++ -std=c++17 -I./include -c src/utils.cpp -o utils.o
```

**Flag `-c` = Compile only, don't link**

**Creates:**
- `arrays_main.o` (object file from 02_arrays_memory.cpp)
- `utils.o` (object file from utils.cpp)

Check they exist:
```bash
ls -lh *.o
# Output:
# -rw-r--r--  arrays_main.o (15 KB)
# -rw-r--r--  utils.o (8 KB)
```

---

##### Step 2: Link Object Files

```bash
# Link object files together
clang++ -std=c++17 arrays_main.o utils.o -o arrays

./arrays
```

**Output:**
```
=== STACK ARRAYS (automatic cleanup) ===
Stack array: [10, 20, 30, 40, 50]
Sum: 150
...
```

---

### Why Separate Compilation Matters

**Scenario:** You modify only `02_arrays_memory.cpp`

**Method 1 (One command):**
```bash
clang++ -std=c++17 -I./include src/02_arrays_memory.cpp src/utils.cpp -o arrays
# Recompiles BOTH files (slower)
```

**Method 2 (Separate):**
```bash
# Only recompile the file you changed
clang++ -std=c++17 -I./include -c src/02_arrays_memory.cpp -o arrays_main.o
# utils.o is already compiled from before!

# Link the new object file with old object file
clang++ -std=c++17 arrays_main.o utils.o -o arrays
# Much faster!
```

**This is what Make does automatically** — tracks which files changed and only recompiles those.

---

## Example 3: With Optimization Flags

### No Optimization (Compile Fast, Run Slow)

```bash
clang++ -O0 -std=c++17 src/02_arrays_memory.cpp src/utils.cpp -o arrays_O0
./arrays_O0
```

**Flag `-O0` = No optimization**
- Compilation: ~instant
- Runtime: Slower (no optimizations applied)
- Good for: Debugging (code matches source)

### Medium Optimization (Default)

```bash
clang++ -O2 -std=c++17 src/02_arrays_memory.cpp src/utils.cpp -o arrays_O2
./arrays_O2
```

**Flag `-O2` = Medium optimization**
- Compilation: ~1 second
- Runtime: Fast (50+ optimizations applied)
- Good for: Most use cases

### Aggressive Optimization

```bash
clang++ -O3 -std=c++17 src/02_arrays_memory.cpp src/utils.cpp -o arrays_O3
./arrays_O3
```

**Flag `-O3` = Aggressive optimization**
- Compilation: ~5 seconds
- Runtime: Very fast (sometimes faster than O2!)
- Good for: Performance-critical code

### Size Optimization

```bash
clang++ -Os -std=c++17 src/02_arrays_memory.cpp src/utils.cpp -o arrays_Os
./arrays_Os
```

**Flag `-Os` = Optimize for size**
- Binary is smaller
- Still fairly fast
- Good for: Embedded systems, small devices

---

### Comparing Binary Sizes

```bash
ls -lh arrays_*

# Output:
# -rwxr-xr-x  arrays_O0    (150 KB)  - Largest, unoptimized
# -rwxr-xr-x  arrays_O2    (80 KB)   - Optimized
# -rwxr-xr-x  arrays_O3    (80 KB)   - Aggressive optimize
# -rwxr-xr-x  arrays_Os    (70 KB)   - Smallest
```

---

## Compiler Flags Explained (Common Ones)

### Optimization Flags

| Flag | Compilation | Runtime | Best For |
|------|-------------|---------|----------|
| `-O0` | Fast | Slow | Debugging |
| `-O1` | Medium | Medium | Balance |
| `-O2` | Slow | Fast | Most code |
| `-O3` | Slowest | Fastest | Performance |
| `-Os` | Slow | Fast | Small binary |

### Warning Flags

```bash
# No warnings
clang++ src/main.cpp -o main

# Show common warnings
clang++ -Wall src/main.cpp -o main

# Show extra warnings
clang++ -Wall -Wextra src/main.cpp -o main

# Treat warnings as errors (fail if any warnings)
clang++ -Wall -Werror src/main.cpp -o main
```

### Include Path

```bash
# Search for headers in current directory and ./include/
clang++ -I. -I./include src/main.cpp -o main
```

### C++ Standard

```bash
# Use C++11 standard
clang++ -std=c++11 src/main.cpp -o main

# Use C++17 standard (recommended)
clang++ -std=c++17 src/main.cpp -o main

# Use C++20 standard (newer)
clang++ -std=c++20 src/main.cpp -o main
```

### Debug Symbols

```bash
# Include debugging information (for lldb)
clang++ -g src/main.cpp -o main
lldb ./main  # Now you can debug with breakpoints
```

### All Together (Production Build)

```bash
clang++ -std=c++17 -Wall -Wextra -O2 -g -I./include \
  src/02_arrays_memory.cpp src/utils.cpp \
  -o arrays

./arrays
```

**Breakdown:**
- `-std=c++17` → Use C++17
- `-Wall -Wextra` → Show all warnings
- `-O2` → Optimize for speed
- `-g` → Include debug symbols
- `-I./include` → Look for headers in include/
- `src/*.cpp` → Compile these files
- `-o arrays` → Output binary named `arrays`

---

## Example 4: Example 3 (Functions and Lambdas) — No Dependencies

```bash
clang++ -std=c++17 src/03_functions_lambdas.cpp -o functions
./functions
```

**Output:**
```
=== FUNCTION POINTERS ===
Applying function to array:
  arr[0] = 1
  arr[1] = 4
  ...
```

This one doesn't need any headers or other files — it's self-contained!

---

## Real-Time Compilation Workflow (What Developers Do)

### Scenario: You're Writing Code

```bash
# 1. Write code in your editor
#    (file: src/my_program.cpp)

# 2. Quick compile and run
clang++ -std=c++17 src/my_program.cpp -o my_prog && ./my_prog

# 3. See an error? Edit the file again

# 4. Recompile (same command)
clang++ -std=c++17 src/my_program.cpp -o my_prog && ./my_prog

# 5. Works? Great! Now with warnings
clang++ -std=c++17 -Wall src/my_program.cpp -o my_prog && ./my_prog

# 6. Clean up warnings, then optimize
clang++ -std=c++17 -Wall -O2 src/my_program.cpp -o my_prog && ./my_prog

# 7. Final version with debug symbols for later
clang++ -std=c++17 -Wall -O2 -g src/my_program.cpp -o my_prog
```

---

## Debugging Compilation Errors

### Error: "include file not found"

```
fatal error: 'utils.h' file not found
#include "../include/utils.h"
         ^
```

**Solution: Add include path**

```bash
# Wrong
clang++ -std=c++17 src/02_arrays_memory.cpp -o arrays

# Right
clang++ -std=c++17 -I./include src/02_arrays_memory.cpp -o arrays
```

---

### Error: "undefined reference to"

```
undefined reference to `print_array(int const*, int, char const*)'
```

**This means:** Compiler found the declaration (from header), but not the definition.

**Solution: Compile the file with the definition**

```bash
# Wrong (missing utils.cpp)
clang++ -std=c++17 -I./include src/02_arrays_memory.cpp -o arrays

# Right (includes utils.cpp)
clang++ -std=c++17 -I./include src/02_arrays_memory.cpp src/utils.cpp -o arrays
```

---

### Error: "redefinition of"

```
redefinition of 'print_array'
```

**This means:** Same function defined twice (usually in header and cpp file).

**Solution: Put function in `.cpp` file, declaration in `.h` file only**

Check:
- `include/utils.h` should have `void print_array(...);` (declaration)
- `src/utils.cpp` should have `void print_array(...) { ... }` (definition)
- NOT in both files!

---

## Quick Reference: Common Compilation Commands

### Compile One File

```bash
clang++ -std=c++17 src/main.cpp -o main
```

### Compile Multiple Files

```bash
clang++ -std=c++17 src/main.cpp src/utils.cpp -o myprogram
```

### With Includes Directory

```bash
clang++ -std=c++17 -I./include src/main.cpp src/utils.cpp -o myprogram
```

### With Optimization

```bash
clang++ -std=c++17 -O2 src/main.cpp src/utils.cpp -o myprogram
```

### With Debug Symbols

```bash
clang++ -std=c++17 -g src/main.cpp src/utils.cpp -o myprogram
lldb ./myprogram
```

### With All Warnings

```bash
clang++ -std=c++17 -Wall -Wextra src/main.cpp src/utils.cpp -o myprogram
```

### Complete Production Build

```bash
clang++ -std=c++17 -Wall -Wextra -O2 -g -I./include \
  src/main.cpp src/utils.cpp \
  -o myprogram
```

### Separate Compilation (for faster rebuilds)

```bash
# Compile each file to object file
clang++ -std=c++17 -I./include -c src/main.cpp -o main.o
clang++ -std=c++17 -I./include -c src/utils.cpp -o utils.o

# Link object files
clang++ -std=c++17 main.o utils.o -o myprogram

# Run
./myprogram
```

---

## Hands-On: Try Each Method

### Method 1: Super Simple (One File)

```bash
cd /Users/surendrashukla/projects/2026/platform-lab/cpp_cuda_prep

clang++ -std=c++17 src/01_hello_world.cpp -o hello
./hello
```

**Expected output:**
```
Hello, C++!
This is your first C++ program.
```

---

### Method 2: With Multiple Files

```bash
clang++ -std=c++17 -I./include \
  src/02_arrays_memory.cpp src/utils.cpp \
  -o arrays

./arrays
```

**Expected output:**
```
=== STACK ARRAYS (automatic cleanup) ===
Stack array: [10, 20, 30, 40, 50]
Sum: 150
...
```

---

### Method 3: See Assembly Code

```bash
clang++ -std=c++17 -S src/01_hello_world.cpp -o hello.s
cat hello.s  # View assembly (it's complex!)
```

---

### Method 4: Separate Compilation

```bash
# Compile to object files
clang++ -std=c++17 -I./include -c src/02_arrays_memory.cpp -o arrays_main.o
clang++ -std=c++17 -I./include -c src/utils.cpp -o utils_lib.o

# Link
clang++ -std=c++17 arrays_main.o utils_lib.o -o arrays

./arrays
```

---

### Method 5: Different Optimization Levels

```bash
# No optimization
clang++ -O0 -std=c++17 -I./include src/02_arrays_memory.cpp src/utils.cpp -o arrays_O0

# Medium optimization
clang++ -O2 -std=c++17 -I./include src/02_arrays_memory.cpp src/utils.cpp -o arrays_O2

# Compare binary sizes
ls -lh arrays_O*
```

---

## How Make Automates This

Remember the Makefile from your project?

```makefile
$(BUILD_DIR)/02_arrays_memory: $(SRC_DIR)/02_arrays_memory.cpp $(UTILS_OBJ)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< $(UTILS_OBJ) -o $@
```

This is **equivalent to:**

```bash
clang++ -std=c++17 -Wall -Wextra -O2 -I./include \
  src/02_arrays_memory.cpp build/utils.o -o build/02_arrays_memory
```

Make just:
1. Tracks which files changed
2. Only recompiles what's needed
3. Automatically links everything
4. Runs with one command: `make run-02`

**You're doing manually what Make does automatically!**

---

## Key Takeaways

✅ **Simplest compilation:**
```bash
clang++ -std=c++17 src/file.cpp -o output
./output
```

✅ **With multiple files:**
```bash
clang++ -std=c++17 -I./include src/main.cpp src/utils.cpp -o output
```

✅ **Separate compilation (faster rebuilds):**
```bash
clang++ -std=c++17 -I./include -c src/main.cpp -o main.o
clang++ -std=c++17 -I./include -c src/utils.cpp -o utils.o
clang++ -std=c++17 main.o utils.o -o output
```

✅ **With flags:**
- `-std=c++17` → C++17 standard
- `-Wall -Wextra` → All warnings
- `-O2` → Optimize for speed
- `-g` → Debug symbols
- `-I./include` → Include directory

✅ **Compilation stages (what happens inside):**
1. Preprocess (`#include` expansion)
2. Compile (C++ → assembly)
3. Assemble (assembly → machine code `.o`)
4. Link (`.o` files → executable)

All automated when you run `clang++` once!

---

## See Also

- Run with different flags: `clang++ -std=c++17 -Wall -Wextra -O2 ...`
- Debug: `clang++ -g ... && lldb ./program`
- View assembly: `clang++ -S ... && cat program.s`
- View object symbols: `nm program.o`
- Disassemble binary: `llvm-objdump -d ./program`

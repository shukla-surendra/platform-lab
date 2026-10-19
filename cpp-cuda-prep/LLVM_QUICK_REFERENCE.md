# LLVM Quick Reference Card

## What Is LLVM? (30-second version)

```
LLVM = Compiler Toolkit that lets multiple languages (C++, Rust, Swift)
compile to multiple targets (x86, ARM, RISC-V) by sharing optimization
and code generation infrastructure.

Your Code → [Clang Frontend] → LLVM IR → [LLVM Optimizer] → 
[LLVM Backend] → Binary
```

---

## You're Using LLVM Right Now

```bash
clang++ -std=c++17 -O2 src/main.cpp -o main
 └─┬──┘
   └─ This is LLVM!
```

| Component | What It Does |
|-----------|-------------|
| **clang++** | Reads C++ code (Clang = LLVM C++ Frontend) |
| **LLVM IR** | Universal intermediate format (all languages use this) |
| **-O2** | Run LLVM optimizers (make code 10-100x faster) |
| **Backend** | Generate x86/ARM/MIPS machine code |
| **Linker** | Create executable |

---

## LLVM Architecture (3 Layers)

```
┌──────────────────────────────────────────┐
│ FRONTEND (Language-Specific)             │
│ ├─ Clang (C/C++)                         │
│ ├─ Rustc (Rust)                          │
│ ├─ Swift Compiler                        │
│ └─ 50+ others                            │
└─────────────┬──────────────────────────────┘
              │ LLVM IR (Universal)
┌─────────────▼──────────────────────────────┐
│ MIDDLE-END (Shared Optimizations)         │
│ ├─ Dead code elimination                  │
│ ├─ Constant folding                       │
│ ├─ Loop unrolling                         │
│ ├─ Vectorization                          │
│ └─ 100+ more optimizations                │
└─────────────┬──────────────────────────────┘
              │ Optimized LLVM IR
┌─────────────▼──────────────────────────────┐
│ BACKEND (Target-Specific)                 │
│ ├─ x86 (Intel/AMD processors)             │
│ ├─ ARM (mobile/embedded)                  │
│ ├─ MIPS (networking)                      │
│ ├─ RISC-V (open hardware)                 │
│ └─ WebAssembly (browser)                  │
└──────────────┬───────────────────────────┘
               │ Machine Code
               ▼ Binary Executable
```

---

## LLVM vs GCC at a Glance

| Dimension | LLVM | GCC |
|-----------|------|-----|
| **Design** | Modular | Monolithic |
| **Optimization** | Shared by all languages | Language-specific |
| **License** | Apache 2.0 (permissive) | GPL v3 (restrictive) |
| **Speed** | Fast compilation, fast runtime | Slower compilation |
| **Error Messages** | Clear & helpful | Verbose & confusing |
| **Commercial Backing** | Apple, Google, Intel | GNU Foundation |
| **Industry Adoption** | Growing, modern | Established, legacy |
| **Languages Supported** | 60+ | ~20 |

**Verdict:** LLVM is winning for new projects; GCC for existing Linux systems.

---

## Key LLVM Concepts

### 1. **LLVM IR (Intermediate Representation)**

Think of it as a "universal assembly language" that all languages compile to.

**Example:**
```cpp
// C++ code
int add(int a, int b) { return a + b; }

// Becomes LLVM IR
define i32 @add(i32 %a, i32 %b) {
  %result = add i32 %a, %b
  ret i32 %result
}

// Then becomes machine code (different per CPU)
add eax, esi    ; x86 instruction
ret
```

**Why it matters:**
- Optimizer works on IR (doesn't care what language you wrote)
- Backend converts IR to any CPU (x86, ARM, etc.)
- Same optimizations benefit C++, Rust, Swift equally

### 2. **Optimization Passes**

`-O2` tells LLVM to run about 50 optimization passes. Each pass improves the code:

```bash
# Without optimization (-O0)
clang++ -O0 file.cpp        # Fast compilation, slow runtime

# With optimization (-O2)
clang++ -O2 file.cpp        # Slower compilation, 10-100x faster runtime

# With aggressive optimization (-O3)
clang++ -O3 file.cpp        # Slowest compilation, sometimes fastest runtime
```

### 3. **Modular Design**

LLVM's genius: Separate components work together.

```
New Language (Python) + New Target (RISC-V)
     ↓
Use existing LLVM IR + existing optimizers + existing backend
     ↓
Works immediately! (No need to rewrite optimization or code generation)
```

---

## LLVM Tools You Might Use

```bash
# Compile to LLVM IR and see it
clang++ -S -emit-llvm file.cpp -o file.ll
cat file.ll

# Disassemble a binary to see machine code
llvm-objdump -d ./program

# Optimize LLVM IR standalone
opt -O2 input.ll -o output.ll

# Convert LLVM IR to assembly
llc input.ll -o output.asm

# Inspect binary with LLVM tools
llvm-nm ./program          # Show symbols
llvm-size ./program        # Show section sizes
llvm-readobj ./program     # Detailed binary info
```

---

## What Happens When You Compile (With LLVM)

```
$ clang++ -O2 src/main.cpp -o main

1. Clang Lexer
   Converts: int x = 5;
   To:      TOKEN(INT), TOKEN(IDENTIFIER, "x"), TOKEN(EQUALS), TOKEN(NUMBER, 5)

2. Clang Parser
   Builds Abstract Syntax Tree (AST) from tokens

3. Clang Semantics
   Checks types, scopes, etc.

4. LLVM IR Generation
   Converts AST to LLVM IR

5. LLVM Optimizer (-O2)
   Runs 50 optimization passes:
   - Dead code elimination
   - Constant propagation
   - Loop unrolling
   - Vectorization
   - ... (many more)

6. LLVM Code Generator
   Converts IR to x86 machine code

7. Assembler
   Converts assembly to object files (.o)

8. Linker
   Links object files + libraries → executable
```

---

## LLVM + Your Learning Path

### Now (C++ with Clang/LLVM)
```
C++ Code → Clang++ (LLVM) → Binary
```
You're learning this ✓

### Later (CUDA with NVCC)
```
CUDA Code → NVCC → GPU Binary
```
Same concept, but for GPU:
- Frontend: CUDA C++ syntax
- Optimizer: GPU-specific optimizations
- Backend: NVIDIA GPU machine code

**Key insight:** Understanding LLVM architecture prepares you for CUDA!

---

## Real-World LLVM Users

| Company/Project | Using LLVM For |
|-----------------|----------------|
| **Apple** | Swift, Clang (default C/C++), all dev tools |
| **Rust** | Official compiler (rustc) |
| **Google** | Android NDK, WebAssembly experiments |
| **Meta** | Code optimization, research |
| **Microsoft** | Research projects, considering adoption |
| **NVIDIA** | Some GPU compiler infrastructure |
| **Intel** | Compiler research, oneAPI |
| **Mozilla** | Firefox browser (via Rust) |
| **Linux Kernel** | Moving toward Clang support |
| **Emscripten** | WebAssembly compilation |

---

## LLVM Version You're Using

```bash
$ clang++ --version
Apple clang version 17.0.0 (clang-17.0.0)
Target: arm64-apple-macosx14.0.0
```

**Breakdown:**
- **Version 17.0.0** = LLVM 17 (released Sept 2023)
- **Apple clang** = Clang frontend (Apple's distribution)
- **arm64** = Target is Apple Silicon (M1/M2/M3)
- **macosx14** = Target macOS 14 (Sonoma)

**Why versions matter:**
- LLVM 17 has optimizations that LLVM 16 doesn't
- Newer = faster code generation + better error messages
- Your system is on cutting edge ✓

---

## Generate and Inspect LLVM IR

### Try This Now:

```bash
# Create a test file
cat > /tmp/test.cpp << 'EOF'
int multiply(int a, int b) {
    return a * b;
}

int main() {
    int result = multiply(5, 3);
    return result;
}
EOF

# Compile to LLVM IR (don't generate binary)
clang++ -S -emit-llvm /tmp/test.cpp -o /tmp/test.ll

# View the LLVM IR
cat /tmp/test.ll

# Compile with optimization to IR
clang++ -S -emit-llvm -O2 /tmp/test.cpp -o /tmp/test_opt.ll

# Compare (optimized should be simpler)
diff /tmp/test.ll /tmp/test_opt.ll
```

**What you'll see:**
- Unoptimized IR: More code, explicit instructions
- Optimized IR: Simplified (dead code removed, constants folded)

---

## Common Misconceptions

❌ **"LLVM is a virtual machine"**
✅ True: Name is misleading. LLVM is a compiler toolkit, not a VM.

❌ **"LLVM only works with C/C++"**
✅ True: 60+ languages use LLVM (Rust, Swift, Go, Julia, etc.)

❌ **"LLVM is only for open source"**
✅ True: Permissive license, used commercially by Apple, Google, Meta

❌ **"LLVM is slower than hand-written assembly"**
✅ True & False: LLVM optimization often beats hand-written code!

---

## Quick Commands Reference

```bash
# Check LLVM version
clang++ --version

# Compile to LLVM IR
clang++ -S -emit-llvm -O2 file.cpp -o file.ll

# View generated assembly
clang++ -S file.cpp -o file.asm
cat file.asm

# Disassemble binary
llvm-objdump -d ./program

# Compile with specific optimization level
clang++ -O0 file.cpp      # No optimization (fast compile, slow run)
clang++ -O1 file.cpp      # Light optimization
clang++ -O2 file.cpp      # Medium optimization (balance)
clang++ -O3 file.cpp      # Aggressive optimization
clang++ -Os file.cpp      # Optimize for size
clang++ -Oz file.cpp      # Aggressive size optimization

# See which optimizations are applied
clang++ -O2 -Xclang -print-stats file.cpp
```

---

## Key Takeaway

**LLVM = The compiler infrastructure that makes clang++ work.**

When you compile C++ code with:
```bash
clang++ -O2 -std=c++17 file.cpp -o binary
```

You're actually running:
1. **Clang** (LLVM's C++ frontend) — parses your code
2. **LLVM IR Generator** — converts to universal format
3. **LLVM Optimizer** — makes code faster (50+ passes)
4. **LLVM Backend** — generates machine code for your CPU
5. **Linker** — creates executable

All three layers are LLVM. That's why it's so powerful.

---

## Next: Explore LLVM in Your Project

```bash
cd ~/projects/2026/platform-lab/cpp_cuda_prep

# Generate LLVM IR from your examples
clang++ -S -emit-llvm src/02_arrays_memory.cpp -o /tmp/arrays.ll

# Look at it
cat /tmp/arrays.ll

# See what optimizations do
clang++ -S -emit-llvm -O0 src/02_arrays_memory.cpp -o /tmp/arrays_O0.ll
clang++ -S -emit-llvm -O2 src/02_arrays_memory.cpp -o /tmp/arrays_O2.ll

# Compare
diff /tmp/arrays_O0.ll /tmp/arrays_O2.ll | head -20
```

You'll see how `-O2` optimization simplifies the code!

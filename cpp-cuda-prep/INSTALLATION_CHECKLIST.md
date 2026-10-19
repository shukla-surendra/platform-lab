# Installation Checklist: What You Need to Run C++

This guide shows **exactly what's installed on your system right now** and how to verify/install each component.

---

## ✅ Your Current System (Verified)

You already have everything needed to run C++ on macOS. Here's what's installed:

### Tier 1: Essential (You Have These ✓)

| Component | Package | Version | Status | Command to Verify |
|-----------|---------|---------|--------|-------------------|
| **C++ Compiler** | LLVM/Clang | 17.0.0+ | ✅ Installed | `clang++ --version` |
| **Build Tool** | GNU Make | 3.81+ | ✅ Installed | `make --version` |
| **Debugger** | LLDB | 17.0.0+ | ✅ Installed | `lldb --version` |

### Tier 2: Optional but Useful (Install as Needed)

| Component | Package | Purpose | Install Command |
|-----------|---------|---------|-----------------|
| **Alternative Compiler** | GCC/G++ | Compare performance | `brew install gcc` |
| **Text Editor** | VS Code | Edit code with plugins | `brew install --cask visual-studio-code` |
| **Advanced Debugger** | GDB | Alternative to LLDB | `brew install gdb` |
| **Documentation** | CPPReference | C++ standard library docs | https://en.cppreference.com/ |

---

## Installation Timeline: How It Happened

### Stage 1: Initial Xcode Installation (macOS)

When you set up your Mac, Xcode Command Line Tools were installed (either explicitly or automatically).

```bash
# Check if Xcode command line tools are installed
xcode-select -p

# If not installed, run:
xcode-select --install
```

**What this gave you:**
- ✅ Clang++ compiler
- ✅ LLDB debugger
- ✅ Make build tool
- ✅ Git version control
- ✅ Standard C/C++ libraries

**Installation size:** ~1.2 GB
**Installation time:** ~10 minutes

---

### Stage 2: Homebrew Installation (You May Have)

Homebrew is a package manager for macOS (like `apt` on Linux).

```bash
# Check if Homebrew is installed
brew --version

# If not, install:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**What Homebrew gives you:**
- Easy package management
- One-command installs
- Automatic updates
- Version management

---

### Stage 3: Installing Build Tools (What We Did)

Using Homebrew (or Xcode CLT directly), you have:

```bash
# These come with Xcode Command Line Tools (no separate install needed)
clang++      # C++ compiler
make         # Build automation
lldb         # Debugger
git          # Version control
```

**Installation method:** Already installed via Xcode CLT
**Installation size:** Included in Xcode (~1.2 GB total)
**Installation time:** Already done ✓

---

## What Each Component Does

### 1. **Clang++ Compiler** (The Most Important)

**What it is:** Translates C++ code into machine code

```bash
# Location on your system
which clang++
# Output: /usr/bin/clang++ (or /opt/homebrew/bin/clang++)

# Version info
clang++ --version
# Output: Apple clang version 17.0.0 (or similar)

# See compiler search paths
clang++ -v -E - < /dev/null 2>&1 | grep -A 20 "include"
```

**Files it needs:**
- `/usr/include/c++/v1/` (C++ standard library headers)
- `/usr/lib/libc++.dylib` (C++ runtime library)

**What it produces:**
- `.o` files (object files) when you use `-c` flag
- Executable binaries when you link

---

### 2. **Make** (Build Automation)

**What it is:** Reads instructions from `Makefile`, runs compilation commands

```bash
# Location
which make
# Output: /usr/bin/make

# Version
make --version
# Output: GNU Make 3.81 or 4.0+

# How it works
make          # Reads Makefile, executes rules
make clean    # Executes clean target
make run-all  # Chains multiple targets
```

**Files it uses:**
- `Makefile` (contains rules and dependencies)
- Dependency tracking (knows which files changed)

**Why you need it:**
- Without Make: manually type compiler flags every time
- With Make: one command does everything

---

### 3. **LLDB Debugger** (Optional but Useful)

**What it is:** Lets you step through code, set breakpoints, inspect variables

```bash
# Location
which lldb
# Output: /usr/bin/lldb

# Version
lldb --version
# Output: lldb-1700.0.0 or similar

# How to use
lldb ./build/program    # Run program in debugger
(lldb) break set --file src/main.cpp --line 5  # Set breakpoint
(lldb) run              # Execute until breakpoint
(lldb) print variable   # Inspect variable
(lldb) step             # Step one line
(lldb) continue         # Resume execution
(lldb) quit             # Exit debugger
```

**When to use:**
- Program crashes → find the crash line
- Wrong output → inspect variable values
- Logic errors → step through code

---

### 4. **C++ Standard Library** (Automatically Installed)

**What it is:** Pre-built functions (cout, vector, string, etc.)

```bash
# Headers location
ls -la /usr/include/c++/v1/ | head

# Libraries location
ls -la /usr/lib/libc++*

# Link command (automatic via clang++)
# clang++ automatically links -lc++
```

**Included in Xcode Command Line Tools:**
- `iostream` (input/output)
- `vector` (dynamic arrays)
- `string` (text)
- `algorithm` (sorting, searching)
- `memory` (smart pointers)
- And 200+ more

---

## Installation Verification (Complete Checklist)

Run these commands to verify your setup:

```bash
#!/bin/bash
echo "=== C++ Installation Verification ==="

echo -e "\n1. COMPILER:"
if command -v clang++ &> /dev/null; then
  clang++ --version | head -1
  echo "✓ Clang++ ready"
else
  echo "✗ Clang++ NOT found"
fi

echo -e "\n2. BUILD TOOL:"
if command -v make &> /dev/null; then
  make --version | head -1
  echo "✓ Make ready"
else
  echo "✗ Make NOT found"
fi

echo -e "\n3. DEBUGGER:"
if command -v lldb &> /dev/null; then
  lldb --version | head -1
  echo "✓ LLDB ready"
else
  echo "✗ LLDB NOT found"
fi

echo -e "\n4. STANDARD LIBRARY:"
if [ -d "/usr/include/c++/v1" ]; then
  echo "✓ C++ Standard Library headers found"
  echo "  Location: /usr/include/c++/v1"
else
  echo "✗ C++ Standard Library NOT found"
fi

echo -e "\n5. C++ VERSION SUPPORT:"
clang++ -std=c++17 -dM -E - < /dev/null 2>/dev/null | grep -q "__cplusplus" && echo "✓ C++17 supported" || echo "✗ C++17 not supported"

echo -e "\n6. TEST COMPILATION:"
cat > /tmp/test.cpp << 'EOF'
#include <iostream>
int main() { std::cout << "Hello\n"; return 0; }
EOF
if clang++ -std=c++17 /tmp/test.cpp -o /tmp/test && /tmp/test > /dev/null 2>&1; then
  echo "✓ Test compilation successful"
  rm /tmp/test /tmp/test.cpp
else
  echo "✗ Test compilation failed"
fi

echo -e "\n=== Setup Complete ==="
```

Copy this into a file (e.g., `verify.sh`), run with `bash verify.sh`

---

## Installation Paths on macOS

### Xcode Command Line Tools Locations

```
/usr/bin/                    ← Compilers, make, tools
├── clang
├── clang++
├── make
├── lldb
└── ...

/usr/include/                ← System headers
├── stdio.h
├── stdlib.h
└── ...

/usr/include/c++/v1/         ← C++ Standard Library headers
├── iostream
├── vector
├── string
└── ...

/usr/lib/                    ← Compiled libraries
├── libc++.dylib             ← C++ runtime
├── libSystem.dylib          ← System library
└── ...
```

### Homebrew Locations (if installed)

```
/opt/homebrew/               ← Homebrew root (Apple Silicon)
├── bin/                     ← Executables
├── lib/                     ← Libraries
└── include/                 ← Headers

/usr/local/                  ← Homebrew root (Intel Mac)
├── bin/
├── lib/
└── include/
```

---

## What Gets Installed with Each Package

### Option A: Xcode Command Line Tools (Recommended ✓ You Have This)

**Installation:**
```bash
xcode-select --install
```

**What's included:**
- ✅ Clang/Clang++
- ✅ LLDB
- ✅ Make
- ✅ Git
- ✅ C/C++ Standard Libraries
- ✅ linker (ld)
- ✅ archiver (ar)

**Size:** ~1.2 GB
**Time:** ~10 minutes
**No reboot needed:** Install while you work

---

### Option B: Full Xcode IDE (Alternative, Not Necessary)

**Installation:**
```bash
# Download from App Store or
# https://developer.apple.com/download/
```

**What's included:**
- Everything from Xcode Command Line Tools
- IDE (graphical interface)
- Simulator
- Additional frameworks
- Documentation

**Size:** ~40+ GB
**Time:** 1-2 hours
**Reboot:** May need restart

**Best for:** iOS/macOS app development (not just C++ learning)

---

### Option C: Homebrew Package Manager (Optional)

**Installation:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**What's included:**
- Package manager (brew command)
- Can install: gcc, llvm, gdb, etc.

**Size:** ~100 MB (+ space for packages you install)
**Time:** ~5 minutes
**Why useful:** Easy version management, installing additional tools

---

## Install Additional Compilers (Optional Learning)

### Install G++ (for comparison)

```bash
# If you have Homebrew
brew install gcc

# Without Homebrew (via Xcode + MacPorts)
sudo port install gcc11

# Verify installation
g++ --version
which g++
```

**What you get:**
- Alternative compiler to compare results
- Different optimization strategies
- Useful for cross-platform testing

---

### Install Intel C++ Compiler (Optional, for HPC)

```bash
# Download free community edition from Intel
# https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit-download.html

# Or via Homebrew (Apple Silicon)
brew install intel-oneapi-compiler-cpp
```

**What you get:**
- High-performance numeric compiler
- Better optimization for mathematical code
- Enterprise-grade support

---

## File Size Summary

| Component | Size | Included | Separate Install |
|-----------|------|----------|-------------------|
| Clang++ | 50 MB | Xcode CLT | `brew install llvm` |
| Make | 2 MB | Xcode CLT | `brew install make` |
| LLDB | 20 MB | Xcode CLT | (bundled) |
| Xcode CLT (total) | 1.2 GB | macOS | `xcode-select --install` |
| Full Xcode | 40+ GB | ✗ | Download from App Store |
| G++ | 500 MB | ✗ | `brew install gcc` |
| Intel ICC | 2+ GB | ✗ | Download from Intel |

---

## Troubleshooting Installation Issues

### Issue: "clang++: command not found"

**Cause:** Xcode Command Line Tools not installed

**Fix:**
```bash
# Install CLT
xcode-select --install

# Agree to license
sudo xcode-select --reset
xcode-select --license accept
```

### Issue: "make: command not found"

**Cause:** Xcode CLT not fully installed

**Fix:**
```bash
# Reinstall CLT
rm -rf /Library/Developer/CommandLineTools
xcode-select --install
```

### Issue: "Permission denied: /usr/bin/clang++"

**Cause:** Permissions issue (rare)

**Fix:**
```bash
# Check permissions
ls -l /usr/bin/clang++

# Reset permissions (usually not needed)
sudo chmod 755 /usr/bin/clang++
```

### Issue: "cannot find /usr/include/c++/v1"

**Cause:** Standard library headers not installed

**Fix:**
```bash
# This comes with Xcode CLT, reinstall if missing
xcode-select --install

# Or explicitly
softwareupdate -i -a
```

---

## Post-Installation Setup

### 1. Verify Everything Works

```bash
cd ~/projects/2026/platform-lab/cpp_cuda_prep
make run-all
```

**Expected:** All 3 programs compile and run successfully

### 2. Set Up Your Editor (Optional)

**If using VS Code:**
```bash
# Install C++ extension
# In VS Code: Extensions → Search "C++" → Install "C/C++" by Microsoft

# Create .vscode/settings.json for your project
mkdir -p .vscode
cat > .vscode/settings.json << 'EOF'
{
    "C_Cpp.default.compilerPath": "/usr/bin/clang++",
    "C_Cpp.default.cStandard": "c17",
    "C_Cpp.default.cppStandard": "c++17",
    "C_Cpp.default.intelliSenseEngine": "Tag Parser"
}
EOF
```

### 3. Configure Git (If Not Already Done)

```bash
git config --global user.name "Surendra Shukla"
git config --global user.email "surendra.shukla29@gmail.com"
```

---

## Installation Comparison: macOS vs Linux

### macOS (You)

```
Xcode → xcode-select --install → Clang++ + Make + LLDB
```

**Automatic:** Works out of the box
**Alternative:** Homebrew for additional tools

### Linux (Ubuntu/Debian)

```
Ubuntu → apt install build-essential → G++ + Make + GDB
```

**Command:**
```bash
sudo apt update
sudo apt install build-essential clang make
```

### Linux (Fedora/RHEL)

```bash
sudo dnf install gcc g++ make clang
```

### Windows

```
Windows → Visual Studio → MSVC + MSBuild + Debugger
```

**Or:** MinGW + Make + GDB

---

## What to Do Right Now

✅ **Verify your setup:**
```bash
clang++ --version && make --version && lldb --version
```

✅ **Test the project:**
```bash
cd cpp_cuda_prep && make run-all
```

✅ **Next step (optional):** Install G++ for comparison
```bash
brew install gcc
```

---

## Quick Reference: All Commands

```bash
# Verify installation
clang++ --version
make --version
lldb --version

# Compile a single file
clang++ -std=c++17 -Wall src/main.cpp -o main

# Compile with optimization
clang++ -std=c++17 -O2 src/main.cpp -o main

# Use makefile
make
make run-all
make clean

# Debug a program
lldb ./main
(lldb) run
(lldb) break set --file src/main.cpp --line 10

# Test setup
bash verify.sh

# Install alternatives (if needed)
brew install gcc        # G++
brew install gdb        # GDB debugger
brew install clang-tools-extra  # More LLVM tools
```

---

## Next: What You Can Do After Installation ✓

1. **Immediate (this week):**
   - Run all C++ examples ✓
   - Modify examples
   - Create new files

2. **Short term (next 2 weeks):**
   - Learn debugging with LLDB
   - Compare Clang vs G++ compilation
   - Write own projects

3. **Medium term (weeks 3-4):**
   - Install Intel ICC (optional)
   - Benchmark different compilers
   - Optimize performance

4. **Long term (week 5+):**
   - Install NVIDIA CUDA Toolkit
   - Learn GPU programming
   - Compile `.cu` files with `nvcc`

---

## Conclusion

**You have everything installed** to:
✅ Compile C++ code
✅ Build projects with Make
✅ Debug programs
✅ Learn C++ fundamentals

Your system is production-ready for this entire learning path, from C++ basics through CUDA GPU programming.

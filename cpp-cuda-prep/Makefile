# C++ Build System
# This Makefile teaches you how to compile C++ programs
# Make is a build automation tool that tracks dependencies and rebuilds only what changed

CXX = clang++
CXXFLAGS = -std=c++17 -Wall -Wextra -O2
INCLUDES = -I./include
BUILD_DIR = build
SRC_DIR = src

# Object files (compiled, not linked)
UTILS_OBJ = $(BUILD_DIR)/utils.o

# Targets: executable names (one per program)
TARGETS = $(BUILD_DIR)/01_hello_world $(BUILD_DIR)/02_arrays_memory $(BUILD_DIR)/03_functions_lambdas

# Default target: build everything
all: $(TARGETS)

# Create build directory if needed
$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)

# Compile utils.cpp to object file
$(UTILS_OBJ): $(SRC_DIR)/utils.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

# Link 01_hello_world (no utils needed)
$(BUILD_DIR)/01_hello_world: $(SRC_DIR)/01_hello_world.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< -o $@

# Link 02_arrays_memory (needs utils)
$(BUILD_DIR)/02_arrays_memory: $(SRC_DIR)/02_arrays_memory.cpp $(UTILS_OBJ) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< $(UTILS_OBJ) -o $@

# Link 03_functions_lambdas (no utils needed)
$(BUILD_DIR)/03_functions_lambdas: $(SRC_DIR)/03_functions_lambdas.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< -o $@

# Run targets
run-01:
	@echo "=== Running 01_hello_world ==="
	./$(BUILD_DIR)/01_hello_world

run-02:
	@echo "=== Running 02_arrays_memory ==="
	./$(BUILD_DIR)/02_arrays_memory

run-03:
	@echo "=== Running 03_functions_lambdas ==="
	./$(BUILD_DIR)/03_functions_lambdas

run-all: $(TARGETS) run-01 run-02 run-03

# Cleanup
clean:
	rm -rf $(BUILD_DIR)

# Debug: print variables (useful for understanding Make)
debug:
	@echo "CXX: $(CXX)"
	@echo "CXXFLAGS: $(CXXFLAGS)"
	@echo "TARGETS: $(TARGETS)"

.PHONY: all run-01 run-02 run-03 run-all clean debug

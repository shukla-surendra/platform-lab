#include "../include/utils.h"

// This example demonstrates:
// - Stack arrays (fixed size, automatic cleanup)
// - Heap arrays (dynamic size, manual cleanup)
// - Pointers and array operations
// - Memory allocation with new/delete
// These concepts are CRITICAL for CUDA programming

int main() {
    std::cout << "\n=== STACK ARRAYS (automatic cleanup) ===\n";

    // Stack array - size must be known at compile time
    int stack_array[5] = {10, 20, 30, 40, 50};
    print_array(stack_array, 5, "Stack array");
    std::cout << "Sum: " << sum_array(stack_array, 5) << "\n";

    // std::vector - dynamic array, automatic cleanup
    std::vector<int> vec = {1, 2, 3, 4, 5};
    print_array(vec, "Vector");
    std::cout << "Sum: " << sum_array(vec) << "\n";

    std::cout << "\n=== HEAP ARRAYS (manual cleanup required) ===\n";

    int size = 10;

    // Allocate array on heap
    float* heap_array = allocate_array(size);

    // Fill with values
    for (int i = 0; i < size; ++i) {
        heap_array[i] = i * 1.5f;
    }

    print_array(heap_array, size, "Heap array");
    std::cout << "Sum: " << sum_array(heap_array, size) << "\n";

    // IMPORTANT: Must free memory when done
    free_array(heap_array);
    std::cout << "Freed heap memory\n";

    std::cout << "\n=== POINTER ARITHMETIC ===\n";

    float* arr = allocate_array(6);
    fill_array(arr, 6, 2.5f);

    // Accessing via pointer arithmetic
    std::cout << "arr[0] = " << arr[0] << "\n";
    std::cout << "*(arr + 1) = " << *(arr + 1) << "\n";  // Same as arr[1]

    // Pointer to middle of array
    float* mid = arr + 3;
    std::cout << "*mid (arr[3]) = " << *mid << "\n";

    free_array(arr);

    std::cout << "\n=== KEY TAKEAWAY FOR CUDA ===\n";
    std::cout << "CUDA kernels receive POINTERS to GPU memory (not vectors)\n";
    std::cout << "You must: 1) allocate, 2) fill, 3) pass pointer, 4) cleanup\n";

    return 0;
}

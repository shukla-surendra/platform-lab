#include <iostream>
#include <vector>
#include <functional>

// This example demonstrates:
// - Function pointers
// - Lambda functions (anonymous functions)
// - std::function for flexible function handling
// These concepts map to CUDA kernel functions

// Traditional function
float square(float x) {
    return x * x;
}

float cube(float x) {
    return x * x * x;
}

// Function that takes a function pointer as argument
void apply_function(float* arr, int size, float (*func)(float)) {
    std::cout << "Applying function to array:\n";
    for (int i = 0; i < size; ++i) {
        arr[i] = func(arr[i]);
        std::cout << "  arr[" << i << "] = " << arr[i] << "\n";
    }
}

// Function that takes std::function (more flexible)
void process_array(float* arr, int size, std::function<float(float)> operation) {
    for (int i = 0; i < size; ++i) {
        arr[i] = operation(arr[i]);
    }
}

int main() {
    std::cout << "\n=== FUNCTION POINTERS ===\n";

    float data[5] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    apply_function(data, 5, &square);

    std::cout << "\n=== LAMBDA FUNCTIONS ===\n";

    // Lambda: [captures] (params) -> return_type { body }
    float data2[5] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};

    auto add_ten = [](float x) -> float { return x + 10.0f; };
    std::cout << "Lambda that adds 10:\n";
    process_array(data2, 5, add_ten);
    for (int i = 0; i < 5; ++i) {
        std::cout << "  data[" << i << "] = " << data2[i] << "\n";
    }

    std::cout << "\n=== INLINE LAMBDA ===\n";

    float data3[5] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    std::cout << "Lambda that multiplies by 5:\n";
    process_array(data3, 5, [](float x) { return x * 5.0f; });
    for (int i = 0; i < 5; ++i) {
        std::cout << "  data[" << i << "] = " << data3[i] << "\n";
    }

    std::cout << "\n=== CLOSURE (lambda with capture) ===\n";

    float multiplier = 3.0f;
    // Capture multiplier by value
    auto scale = [multiplier](float x) -> float {
        return x * multiplier;
    };

    float data4[5] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    process_array(data4, 5, scale);
    for (int i = 0; i < 5; ++i) {
        std::cout << "  data[" << i << "] = " << data4[i] << "\n";
    }

    std::cout << "\n=== KEY TAKEAWAY FOR CUDA ===\n";
    std::cout << "CUDA kernels are functions that run MANY times in parallel\n";
    std::cout << "Each GPU thread executes the same kernel function with different data\n";
    std::cout << "Think: apply_function(data, size, kernel)\n";
    std::cout << "       kernel runs in parallel on GPU, once per thread\n";

    return 0;
}

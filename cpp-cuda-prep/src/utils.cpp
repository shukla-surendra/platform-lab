#include "../include/utils.h"
#include <cstdlib>

void print_array(const std::vector<int>& arr, const char* label) {
    std::cout << label << ": [";
    for (size_t i = 0; i < arr.size(); ++i) {
        std::cout << arr[i];
        if (i < arr.size() - 1) std::cout << ", ";
    }
    std::cout << "]\n";
}

void print_array(const int* arr, int size, const char* label) {
    std::cout << label << ": [";
    for (int i = 0; i < size; ++i) {
        std::cout << arr[i];
        if (i < size - 1) std::cout << ", ";
    }
    std::cout << "]\n";
}

void print_array(const float* arr, int size, const char* label) {
    std::cout << label << ": [";
    for (int i = 0; i < size; ++i) {
        std::cout << arr[i];
        if (i < size - 1) std::cout << ", ";
    }
    std::cout << "]\n";
}

int sum_array(const std::vector<int>& arr) {
    int sum = 0;
    for (int val : arr) {
        sum += val;
    }
    return sum;
}

int sum_array(const int* arr, int size) {
    int sum = 0;
    for (int i = 0; i < size; ++i) {
        sum += arr[i];
    }
    return sum;
}

float sum_array(const float* arr, int size) {
    float sum = 0.0f;
    for (int i = 0; i < size; ++i) {
        sum += arr[i];
    }
    return sum;
}

float* allocate_array(int size) {
    return new float[size];
}

void free_array(float* arr) {
    delete[] arr;
}

void fill_array(float* arr, int size, float value) {
    for (int i = 0; i < size; ++i) {
        arr[i] = value;
    }
}

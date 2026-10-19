#ifndef UTILS_H
#define UTILS_H

#include <vector>
#include <iostream>

// Vector operations
void print_array(const std::vector<int>& arr, const char* label = "Array");
void print_array(const int* arr, int size, const char* label = "Array");
void print_array(const float* arr, int size, const char* label = "Array");

// Math operations
int sum_array(const std::vector<int>& arr);
int sum_array(const int* arr, int size);
float sum_array(const float* arr, int size);

// Memory utilities
float* allocate_array(int size);
void free_array(float* arr);
void fill_array(float* arr, int size, float value);

#endif

#include <stddef.h>

enum Kind { First, Second, Third, Fourth };

int main(void) {
    int integers[6] = {0};
    unsigned char bytes[5] = {0};
    double doubles[4] = {0};
    enum Kind kinds[4] = {0};
    int *pointers[3] = {&integers[0], &integers[1], &integers[2]};
    int *integer_begin = integers + 1;
    int *integer_end = integers + 5;
    int **pointer_begin = pointers;
    int **pointer_end = pointer_begin + 3;

    ptrdiff_t integer_forward = integer_end - integer_begin;
    ptrdiff_t integer_reverse = integer_begin - integer_end;
    ptrdiff_t byte_difference = &bytes[4] - &bytes[0];
    ptrdiff_t double_difference = &doubles[3] - &doubles[0];
    ptrdiff_t enum_difference = &kinds[3] - &kinds[0];
    ptrdiff_t pointer_difference = pointer_end - pointer_begin;

    return integer_forward == 4 && integer_reverse == -4 &&
           byte_difference == 4 && double_difference == 3 &&
           enum_difference == 3 &&
           pointer_difference == 3 ? 0 : 1;
}

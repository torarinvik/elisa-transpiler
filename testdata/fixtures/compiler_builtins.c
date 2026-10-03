#include <math.h>

static char object_size_buffer[50];
struct object_size_container
{
    char bytes[8];
    int tail;
};
static struct object_size_container object_size_container_value;

static int unknown_object_size(unsigned char *pointer)
{
    return __builtin_object_size(pointer, 0) == (unsigned long)-1 &&
                   __builtin_object_size(pointer, 1) == (unsigned long)-1 &&
                   __builtin_object_size(pointer, 2) == 0 &&
                   __builtin_object_size(pointer, 3) == 0
               ? 0
               : 1;
}

float compiler_builtin_math(float value)
{
    return __builtin_sinf(value) + __builtin_powf(value, 2.0f);
}

int compiler_builtin_expect(int value)
{
    return __builtin_expect(value, 1);
}

int main(void)
{
    float value = compiler_builtin_math(0.0f);
    return compiler_builtin_expect(42) == 42 && value == 0.0f &&
                   __builtin_object_size(object_size_buffer, 0) == sizeof object_size_buffer &&
                   __builtin_object_size(object_size_buffer, 1) == sizeof object_size_buffer &&
                   __builtin_object_size(object_size_buffer, 2) == sizeof object_size_buffer &&
                   __builtin_object_size(object_size_buffer, 3) == sizeof object_size_buffer &&
                   __builtin_object_size((char *)object_size_buffer, 0) == sizeof object_size_buffer &&
                   __builtin_object_size(object_size_container_value.bytes, 0) == sizeof object_size_container_value &&
                   __builtin_object_size(object_size_container_value.bytes, 1) == sizeof object_size_container_value.bytes &&
                   __builtin_object_size(object_size_container_value.bytes, 2) == sizeof object_size_container_value &&
                   __builtin_object_size(object_size_container_value.bytes, 3) == sizeof object_size_container_value.bytes &&
                   unknown_object_size((unsigned char *)object_size_buffer) == 0
               ? 0
               : 1;
}

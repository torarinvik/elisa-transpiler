#include <stdarg.h>

static int first_argument_twice(int count, ...)
{
    va_list first;
    va_list second;
    va_start(first, count);
    va_copy(second, first);
    int left = va_arg(first, int);
    int right = va_arg(second, int);
    va_end(second);
    va_end(first);
    return left + right;
}

int main(void)
{
    return first_argument_twice(2, 10, 32) == 20 ? 0 : 1;
}

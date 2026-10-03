#include <stdarg.h>

static int sum_ints(int count, ...)
{
    va_list ap;
    va_start(ap, count);
    int total = 0;
    for (int index = 0; index < count; ++index)
        total += va_arg(ap, int);
    va_end(ap);
    return total;
}

int main(void)
{
    return sum_ints(3, 10, 20, 12) == 42 ? 0 : 1;
}

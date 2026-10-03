#include <stdarg.h>

static int promoted_values(int count, ...)
{
    va_list ap;
    va_start(ap, count);
    int small_integer = va_arg(ap, int);
    double promoted_float = va_arg(ap, double);
    int promoted_bool = va_arg(ap, int);
    va_end(ap);
    return small_integer + (int)promoted_float + promoted_bool;
}

int main(void)
{
    unsigned char small = 7;
    float fraction = 0.5f;
    _Bool flag = 1;
    return promoted_values(3, small, fraction, flag) == 8 ? 0 : 1;
}

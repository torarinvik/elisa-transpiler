#include "fp_scoped_controls_header.h"

#define FP_SCOPED_SUM(left, middle, right) ((left) + ((middle) + (right)))

#pragma clang fp reassociate(off)

#pragma float_control(precise, off, push)
float fp_scoped_float_control_fast(float left, float middle, float right)
{
    return left + (middle + right);
}
#pragma float_control(pop)

#pragma float_control(precise, off, push)
int fp_scoped_float_comparison(float left, float right)
{
    return left < right;
}
#pragma float_control(pop)

float fp_scoped_precise(float left, float middle, float right)
{
    return FP_SCOPED_SUM(left, middle, right);
}

float fp_scoped_reassociate(float left, float middle, float right)
{
#pragma clang fp reassociate(on)
    float result = FP_SCOPED_SUM(left, middle, right);
    {
#pragma clang fp reassociate(off)
        result = FP_SCOPED_SUM(left, middle, right);
    }
    result = FP_SCOPED_SUM(left, middle, right);
    return result;
}

#if 0
#pragma clang fp reassociate(on)
float fp_inactive_pragma(float left, float middle, float right)
{
    return left + (middle + right);
}
#endif

int main(void)
{
    return fp_scoped_header(1.0f, 2.0f, 3.0f) == 6.0f &&
                   fp_scoped_float_control_fast(1.0f, 2.0f, 3.0f) == 6.0f &&
                   fp_scoped_float_comparison(1.0f, 2.0f) == 1 &&
                   fp_scoped_precise(1.0f, 2.0f, 3.0f) == 6.0f &&
                   fp_scoped_reassociate(1.0f, 2.0f, 3.0f) == 6.0f
               ? 0
               : 1;
}

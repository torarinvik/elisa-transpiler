#pragma clang fp reassociate(on)

static inline float fp_scoped_header(float left, float middle, float right)
{
    return left + (middle + right);
}

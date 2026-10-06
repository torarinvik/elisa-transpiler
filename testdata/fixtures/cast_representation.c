#include <stdint.h>

static int64_t sign_extend_i32(int32_t value)
{
    return (int64_t)value;
}

static uint32_t truncate_u64(uint64_t value)
{
    return (uint32_t)value;
}

int main(void)
{
    return sign_extend_i32(-17) == -17 && truncate_u64(0x100000001ULL) == 1u
               ? 0
               : 1;
}

static unsigned int wrap_add(void)
{
    return 0xffffffffu + 1u;
}

static unsigned int wrap_multiply(void)
{
    return 0x80000000u * 2u;
}

static unsigned int bitwise_not(void)
{
    return ~0u;
}

static unsigned int octal_wrap(void)
{
    return 037777777777U + 1U;
}

static unsigned long long u64_add_wrap(void)
{
    return 18446744073709551615ULL + 1ULL;
}

static unsigned long long u64_sub_wrap(void)
{
    return 0ULL - 1ULL;
}

static unsigned long long u64_multiply_wrap(void)
{
    return 0x8000000000000000ULL * 2ULL;
}

static unsigned long long u64_shift_left(void)
{
    return 1ULL << 63;
}

static unsigned long long u64_shift_right(void)
{
    return 0x8000000000000000ULL >> 1;
}

static unsigned long long u64_divide(void)
{
    return 0xffffffffffffffffULL / 2ULL;
}

static unsigned long long u64_remainder(void)
{
    return 0xffffffffffffffffULL % 7ULL;
}

static unsigned long long u64_bitwise_not(void)
{
    return ~0ULL;
}

static unsigned long long u64_unary_negation(void)
{
    return -1ULL;
}

static unsigned long long u64_bitwise_and_high(void)
{
    return 0xffffffffffffffffULL & 0x8000000000000000ULL;
}

static unsigned long long u64_bitwise_or_high(void)
{
    return 0x8000000000000000ULL | 1ULL;
}

static unsigned long long u64_bitwise_xor_high(void)
{
    return 0xffffffffffffffffULL ^ 0x8000000000000000ULL;
}

static unsigned long long u64_divide_high_values(void)
{
    return 0xffffffffffffffffULL / 0x8000000000000000ULL;
}

static unsigned long long u64_remainder_high_values(void)
{
    return 0xffffffffffffffffULL % 0x8000000000000000ULL;
}

static unsigned long long u64_cast_u32_value(void)
{
    return (unsigned long long)0x80000000U;
}

static unsigned char u64_to_u8_target_conversion(void)
{
    return (unsigned char)0x8000000000000001ULL;
}

static unsigned short u64_to_u16_target_conversion(void)
{
    return (unsigned short)0x8000000000000001ULL;
}

static unsigned int u64_to_u32_target_conversion(void)
{
    return (unsigned int)0xffffffffffffffffULL;
}

static int u64_high_order_relations(void)
{
    return 0x8000000000000000ULL <= 0xffffffffffffffffULL &&
           0xffffffffffffffffULL >= 0x8000000000000000ULL &&
           0xffffffffffffffffULL != 0x7fffffffffffffffULL;
}

static int u64_high_values_compare_unsigned(void)
{
    return 0xffffffffffffffffULL > 1ULL &&
           1ULL < 0x8000000000000000ULL &&
           !(-1 < 1ULL);
}

static unsigned long long u64_cast_negative(void)
{
    return (unsigned long long)-1;
}

static long long i64_multiply_without_overflow(void)
{
    return 3037000499LL * 3037000499LL;
}

static long long i64_minimum_value(void)
{
    return -9223372036854775807LL - 1LL;
}

static long long i64_divide_negative(void)
{
    return -9223372036854775807LL / 3LL;
}

static long long i64_remainder_negative(void)
{
    return -9223372036854775807LL % 3LL;
}

static long long u64_to_i64_target_conversion(void)
{
    return (long long)0xffffffffffffffffULL;
}

static int u64_to_i32_target_conversion(void)
{
    return (int)0xffffffffffffffffULL;
}

static int u64_to_i32_above_signed_max(void)
{
    return (int)0x80000000ULL;
}

static int u64_to_i16_target_conversion(void)
{
    return (short)0xffffffffffffffffULL;
}

static int u64_to_i32_representable_conversion(void)
{
    return (int)0x7fffffffULL;
}

/* These exported probes are intentionally never called: evaluating these
 * signed-overflow expressions has undefined behavior in C. Their generated
 * shape must keep the operations rather than folding with host arithmetic. */
long long i64_min_divide_by_negative_one(void)
{
    return (-9223372036854775807LL - 1LL) / -1LL;
}

long long i64_min_remainder_by_negative_one(void)
{
    return (-9223372036854775807LL - 1LL) % -1LL;
}

int i32_min_divide_by_negative_one(void)
{
    return (-2147483647 - 1) / -1;
}

int i32_min_remainder_by_negative_one(void)
{
    return (-2147483647 - 1) % -1;
}

long long i64_signed_overflow_add(void)
{
    return 9223372036854775807LL + 1LL;
}

long long i64_signed_overflow_subtract(void)
{
    return (-9223372036854775807LL - 1LL) - 1LL;
}

long long i64_signed_overflow_multiply(void)
{
    return 9223372036854775807LL * 2LL;
}

int main(void)
{
    u64_to_i32_above_signed_max();
    u64_to_i16_target_conversion();
    return wrap_add() == 0u &&
                   wrap_multiply() == 0u &&
                   bitwise_not() == 0xffffffffu &&
                   octal_wrap() == 0u &&
                   !(-1 < 1u) &&
                   u64_add_wrap() == 0ULL &&
                   u64_sub_wrap() == 0xffffffffffffffffULL &&
                   u64_multiply_wrap() == 0ULL &&
                   u64_shift_left() == 0x8000000000000000ULL &&
                   u64_shift_right() == 0x4000000000000000ULL &&
                   u64_divide() == 0x7fffffffffffffffULL &&
                   u64_remainder() == 1ULL &&
                   u64_bitwise_not() == 0xffffffffffffffffULL &&
                   u64_unary_negation() == 0xffffffffffffffffULL &&
                   u64_bitwise_and_high() == 0x8000000000000000ULL &&
                   u64_bitwise_or_high() == 0x8000000000000001ULL &&
                   u64_bitwise_xor_high() == 0x7fffffffffffffffULL &&
                   u64_divide_high_values() == 1ULL &&
                   u64_remainder_high_values() == 0x7fffffffffffffffULL &&
                   u64_cast_u32_value() == 0x80000000ULL &&
                   u64_to_u8_target_conversion() == 1u &&
                   u64_to_u16_target_conversion() == 1u &&
                   u64_to_u32_target_conversion() == 0xffffffffu &&
                   u64_high_order_relations() &&
                   u64_high_values_compare_unsigned() &&
                   u64_cast_negative() == 0xffffffffffffffffULL &&
                   i64_multiply_without_overflow() == 9223372030926249001LL &&
                   i64_minimum_value() == (-9223372036854775807LL - 1LL) &&
                   i64_divide_negative() == -3074457345618258602LL &&
                   i64_remainder_negative() == -1LL &&
                   u64_to_i64_target_conversion() == -1LL &&
                   u64_to_i32_target_conversion() == -1 &&
                   u64_to_i32_representable_conversion() == 2147483647
               ? 0
               : 1;
}

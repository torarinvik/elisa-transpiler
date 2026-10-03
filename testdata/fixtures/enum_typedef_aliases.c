typedef enum CValue {
    C_VALUE_ZERO = 0,
    C_VALUE_UNSIGNED_MAX = 0xffffffffu
} CValue;

typedef CValue CValueAlias;
typedef CValueAlias CValueAlias2;

static CValueAlias2 global_value = (CValueAlias2)5u;

static unsigned int to_unsigned(CValueAlias value)
{
    return value;
}

static CValueAlias2 from_unsigned(unsigned int value)
{
    return (CValueAlias2)value;
}

int main(void)
{
    CValueAlias2 value = from_unsigned(5u);
    if (value != global_value)
        return 1;
    if (to_unsigned(value) != 5u)
        return 2;

    signed char signed_byte = value;
    unsigned char unsigned_byte = value;
    short signed_short = value;
    unsigned short unsigned_short = value;
    int signed_int = value;
    unsigned int unsigned_int = value;
    long signed_long = value;
    unsigned long unsigned_long = value;
    long long signed_long_long = value;
    unsigned long long unsigned_long_long = value;

    if (signed_byte != 5 || unsigned_byte != 5u)
        return 3;
    if (signed_short != 5 || unsigned_short != 5u)
        return 4;
    if (signed_int != 5 || unsigned_int != 5u)
        return 5;
    if (signed_long != 5L || unsigned_long != 5UL)
        return 6;
    if (signed_long_long != 5LL || unsigned_long_long != 5ULL)
        return 7;

    value |= (CValueAlias2)0x20u;
    if (to_unsigned(value) != 37u)
        return 8;

    CValueAlias2 boundary = from_unsigned(0xffffffffu);
    signed char boundary_signed_byte = boundary;
    unsigned char boundary_unsigned_byte = boundary;
    short boundary_signed_short = boundary;
    unsigned short boundary_unsigned_short = boundary;
    int boundary_signed_int = boundary;
    unsigned int boundary_unsigned_int = boundary;
    long boundary_signed_long = boundary;
    unsigned long boundary_unsigned_long = boundary;
    long long boundary_signed_long_long = boundary;
    unsigned long long boundary_unsigned_long_long = boundary;
    if (boundary_signed_byte != (signed char)0xffffffffu || boundary_unsigned_byte != (unsigned char)0xffffffffu)
        return 9;
    if (boundary_signed_short != (short)0xffffffffu || boundary_unsigned_short != (unsigned short)0xffffffffu)
        return 10;
    if (boundary_signed_int != (int)0xffffffffu || boundary_unsigned_int != (unsigned int)0xffffffffu)
        return 11;
    if (boundary_signed_long != (long)0xffffffffu || boundary_unsigned_long != (unsigned long)0xffffffffu)
        return 12;
    if (boundary_signed_long_long != (long long)0xffffffffu || boundary_unsigned_long_long != (unsigned long long)0xffffffffu)
        return 13;
    return 0;
}

static unsigned int add_wrap(unsigned int left, unsigned int right)
{
    return left + right;
}

static unsigned int multiply_wrap(unsigned int left, unsigned int right)
{
    return left * right;
}

int main(void)
{
    unsigned char maximum8 = (unsigned char)-1;
    unsigned short maximum16 = (unsigned short)-1;
    unsigned int maximum32 = (unsigned int)-1;
    unsigned long long maximum64 = (unsigned long long)-1;
    unsigned int high_bit = 0x80000000u;

    if (maximum8 != 0xffu)
    {
        return 3;
    }
    if (maximum16 != 0xffffu)
    {
        return 4;
    }
    if (maximum32 != 0xffffffffu)
    {
        return 5;
    }
    if (maximum64 != 0xffffffffffffffffULL)
    {
        return 6;
    }
    if (add_wrap(maximum32, 1u) != 0u)
    {
        return 1;
    }
    if (multiply_wrap(high_bit, 2u) != 0u)
    {
        return 2;
    }
    return 0;
}

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
    unsigned int maximum = (unsigned int)-1;
    unsigned int high_bit = 0x80000000u;

    if (add_wrap(maximum, 1u) != 0u)
    {
        return 1;
    }
    if (multiply_wrap(high_bit, 2u) != 0u)
    {
        return 2;
    }
    return 0;
}

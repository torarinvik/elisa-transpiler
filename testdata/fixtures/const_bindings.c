static int read_const_bindings(const int scalar, int * const fixed, const int *readonly)
{
    return scalar + *fixed + *readonly;
}

int main(void)
{
    int value = 2;
    const int scalar = 3;
    int * const fixed = &value;
    const int *readonly = &scalar;
    return read_const_bindings(scalar, fixed, readonly) == 8 ? 0 : 1;
}

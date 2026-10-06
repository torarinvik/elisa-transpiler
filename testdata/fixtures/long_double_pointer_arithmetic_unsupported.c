static long double *opaque_value;

int main(void)
{
    return opaque_value + 1 == opaque_value ? 0 : 1;
}

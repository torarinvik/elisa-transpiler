static long double *opaque_value;

int main(void)
{
    return *opaque_value > 0.0L ? 0 : 1;
}

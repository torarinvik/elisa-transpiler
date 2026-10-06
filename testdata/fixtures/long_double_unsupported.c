typedef long double extended_real;

static extended_real widen_to_extended(double value)
{
    return (extended_real)value;
}

int main(void)
{
    extended_real value = widen_to_extended(1.0);
    return value > 0.0L ? 0 : 1;
}

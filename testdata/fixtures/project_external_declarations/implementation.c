int project_external_sum(int left, int right)
{
    return left + right;
}

int project_external_qualified(int value, int *output)
{
    *output = value;
    return value + 1;
}

int project_external_zero(void)
{
    return 17;
}

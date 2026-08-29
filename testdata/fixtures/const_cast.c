static int discard_const(const int *value)
{
    return ((int *)value)[0];
}

static int add_const(int *value)
{
    const int *readonly = value;
    return readonly[0];
}

int main(void)
{
    int value = 9;
    return discard_const(&value) == 9 && add_const(&value) == 9 ? 0 : 1;
}

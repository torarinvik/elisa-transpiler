static int shared_value = 5;

static int read_shared(int addend)
{
    return shared_value + addend;
}

static int recursive_total(int depth)
{
    if (depth <= 0)
    {
        return read_shared(0);
    }
    if (depth == 1)
    {
        return recursive_total(0) + recursive_total(0);
    }
    return recursive_total(depth - 1);
}

int main(void)
{
    return recursive_total(1) == 10 ? 0 : 1;
}

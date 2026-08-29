static int simplify(int value)
{
    int result = (value + 0) * 1;
    if (1 && 1)
        return result;
    return 0;
}

static int read_after_guard(const int *value)
{
    if (value == 0)
        return 0;
    return value[0];
}

static int read_mutable_pointer(int *value)
{
    return value[0];
}

static int inspect_readonly(const int *value)
{
    return value != 0;
}

static int read_after_readonly_call(int *value)
{
    if (value == 0)
        return 0;
    inspect_readonly(value);
    return value[0];
}

int main(void)
{
    int value = 7;
    return simplify(value) == 7 && read_after_guard(&value) == 7 && read_after_guard(0) == 0 && read_mutable_pointer(&value) == 7 ? 0 : 1;
}

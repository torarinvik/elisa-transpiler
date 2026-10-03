static int first_value(const int *value)
{
    if (value == 0)
        return -1;
    return value[0];
}

int main(void)
{
    int value = 73;
    return first_value(&value) == 73 ? 0 : 1;
}

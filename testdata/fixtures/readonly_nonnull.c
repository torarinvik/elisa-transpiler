static int read_first(const int *value)
{
    return value[0];
}

int main(void)
{
    int value = 39;
    return read_first(&value) == 39 ? 0 : 1;
}

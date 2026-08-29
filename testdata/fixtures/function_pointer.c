static int increment(int value)
{
    return value + 1;
}

int main(void)
{
    int (*operation)(int) = increment;
    return operation(41) == 42 ? 0 : 1;
}

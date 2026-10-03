static int first(void)
{
    static int value = 1;
    return value;
}

static int second(void)
{
    static int value = 2;
    return value;
}

int main(void)
{
    return first() + second() == 3 ? 0 : 1;
}

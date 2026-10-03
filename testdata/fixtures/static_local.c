static int next_value(void)
{
    static int value = 4;
    value += 3;
    return value;
}

int main(void)
{
    return next_value() == 7 && next_value() == 10 && next_value() == 13 ? 0 : 1;
}

static int folded_value(void)
{
    return (2 + 3) * 4;
}

static int folded_condition(void)
{
    return (7 > 3) && (4 != 0) ? 1 : 0;
}

int main(void)
{
    return folded_value() == 20 && folded_condition() == 1 ? 0 : 1;
}

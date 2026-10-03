int main(void)
{
    int value = 1, stable = 8;
    value += 2;

    {
        int shadow = 20, scratch = 0;
        shadow++;
        scratch++;
    }

    int accumulated = 0;
    for (int index = 0, steps = 0; index < 3; index++, steps++)
        accumulated += index + steps;

    return value == 3 && stable == 8 && accumulated == 6 ? 0 : 1;
}

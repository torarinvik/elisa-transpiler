int main(void)
{
    int i = 0;
    int sum = 0;

    do
    {
        i++;
        if (i < 3)
            continue;
        sum += i;
    }
    while (i < 5);

    return sum == 12 ? 0 : 1;
}

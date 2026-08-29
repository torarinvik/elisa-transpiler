int main(void)
{
    int i = 0;
    int total = 0;

    while (i < 5)
    {
        total += i;
        i++;
        if (i == 3)
            goto done;
    }

done:
    return total == 3 ? 0 : 1;
}

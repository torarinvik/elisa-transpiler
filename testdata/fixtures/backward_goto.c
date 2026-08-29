int main(void)
{
    int n = 0;
    int total = 0;

repeat:
    if (n < 3)
    {
        total += n;
        n++;
        goto repeat;
    }

    return total == 3 ? 0 : 1;
}

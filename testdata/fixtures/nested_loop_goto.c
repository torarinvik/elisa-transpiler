int main(void)
{
    int value = 0;

    while (value < 4)
    {
        while (value < 4)
        {
            value++;
            goto done;
        }
    }

done:
    return value == 1 ? 0 : 1;
}

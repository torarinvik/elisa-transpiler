int main(void)
{
    int total = 0;
    int index = 0;
    for (; index < 5; index++)
    {
        if (index == 3)
            continue;
        total += index;
    }
    do
    {
        total += index;
        index--;
    } while (index > 0);
    return total == 22 ? 0 : 1;
}

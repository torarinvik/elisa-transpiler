int main(void)
{
    int index = 0;
    int value = 0;

    for (; index < 5; index++)
    {
        switch (index)
        {
            case 2:
                goto finished;
            default:
                value++;
        }
        value += 10;
    }

finished:
    return index == 2 && value == 22 ? 0 : 1;
}

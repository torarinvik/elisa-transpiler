int main(void)
{
    int value = 1;
    {
        int value = 2;
        if (value != 2)
            return 1;
    }
    return value == 1 ? 0 : 1;
}

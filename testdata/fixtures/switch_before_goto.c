int main(void)
{
    int value = 1;
    int result = 0;

    switch (value)
    {
        case 1:
            result = 42;
            break;
        default:
            result = -1;
            break;
    }

    if (result == 42)
        goto done;
    result = -1;

done:
    return result == 42 ? 0 : 1;
}

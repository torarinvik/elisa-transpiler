int main(void)
{
    int value = 1;
    int result = 0;

    switch (value)
    {
        case 1:
            if (value == 1)
            {
                result = 40;
                result += 2;
                break;
            }
        default:
            result = -1;
            break;
    }

    goto done;

done:
    return result == 42 ? 0 : 1;
}

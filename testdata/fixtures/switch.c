static int classify(int value)
{
    switch (value)
    {
        case 0:
        case 1:
            return 10;
        case 2:
            value += 3;
            /* intentional fallthrough */
        case 5:
            return value;
        default:
            return -1;
    }
}

static int loop_break(int value)
{
    switch (value)
    {
        case 0:
            for (int index = 0; index < 3; index++)
            {
                if (index == 1)
                    break;
                value += index;
            }
            return value;
        default:
            return -1;
    }
}

static int nested_switch(int value)
{
    int result = 0;
    for (int index = 0; index < 2; index++)
    {
        switch (value)
        {
            case 2:
                result = 20;
                break;
            default:
                result = -20;
                break;
        }
        break;
    }
    return result;
}

int main(void)
{
    return classify(0) == 10 && classify(2) == 5 && classify(5) == 5 && classify(9) == -1 && loop_break(0) == 0 && nested_switch(2) == 20 ? 0 : 1;
}

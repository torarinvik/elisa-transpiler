static int selector_calls = 0;

static int select_value(void)
{
    selector_calls += 1;
    return 1;
}

int main(void)
{
    int result = 0;
    goto dispatch;

dispatch:
    switch (select_value())
    {
        case 0:
            result = -1;
            break;
        case 1:
            result = 42;
            break;
        default:
            result = -1;
            break;
    }

    return selector_calls == 1 && result == 42 ? 0 : 1;
}

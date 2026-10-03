static int gate;
static int cursor;
static int index_calls;
static unsigned char values[1] = {255};

static int touches;

static int touch(void)
{
    touches += 1;
    return 1;
}

static int comma_return(void)
{
    return (touch(), touches);
}

static int comma_arithmetic_return(void)
{
    return (touch(), touches) + 20;
}

static int comma_conditional_return(int selector)
{
    return selector ? (touch(), touches + 70) : (touch(), touches + 80);
}

static int next_index(void)
{
    index_calls += 1;
    return 0;
}

static int identity(int value)
{
    return value;
}

int main(void)
{
    gate = 0;
    cursor = 0;
    if (gate && (cursor = 5))
        return 1;
    if (cursor != 0)
        return 2;

    gate = 1;
    cursor = 0;
    if (!(gate && (cursor = 6)) || cursor != 6)
        return 3;

    gate = 1;
    cursor = 0;
    if (!(gate || (cursor = 7)) || cursor != 0)
        return 4;

    gate = 0;
    cursor = 0;
    if (!(gate || (cursor = 8)) || cursor != 8)
        return 5;

    cursor = 0;
    int result = identity(cursor = 9);
    if (result != 9 || cursor != 9)
        return 6;

    index_calls = 0;
    values[0] = 255;
    unsigned char compound_result = values[next_index()] += 1;
    if (index_calls != 1 || compound_result != 0 || values[0] != 0)
        return 7;

    index_calls = 0;
    int wide_value = 300;
    unsigned char simple_result = values[next_index()] = wide_value;
    if (index_calls != 1 || simple_result != 44 || values[0] != 44)
        return 9;

    cursor = 0;
    if ((cursor += 3) != 3 || cursor != 3)
        return 8;

    touches = 0;
    if ((touch(), touches) != 1)
        return 10;
    if (touches != 1)
        return 12;

    touches = 0;
    int iterations = 0;
    while ((touch(), iterations < 3))
        iterations += 1;
    if (touches != 4 || iterations != 3)
        return 11;

    touches = 0;
    int snapshot = (touch(), touches);
    if (snapshot != 1 || touches != 1)
        return 13;

    touches = 0;
    int returned = comma_return();
    if (returned != 1 || touches != 1)
        return 14;

    touches = 0;
    gate = 1;
    int conditional_true = gate ? (touch(), touches + 30) : (touch(), touches + 40);
    if (conditional_true != 31 || touches != 1)
        return 23;

    touches = 0;
    gate = 0;
    int conditional_false = gate ? (touch(), touches + 40) : (touch(), touches + 50);
    if (conditional_false != 51 || touches != 1)
        return 24;

    touches = 0;
    gate = 1;
    int conditional_nested_value = gate ? ((touch(), touches) + 60) : 0;
    if (conditional_nested_value != 61 || touches != 1)
        return 25;

    touches = 0;
    gate = 1;
    int conditional_condition_effect = (touch(), gate) ? (touch(), touches + 70) : 0;
    if (conditional_condition_effect != 72 || touches != 2)
        return 26;

    touches = 0;
    int conditional_returned = comma_conditional_return(1);
    if (conditional_returned != 71 || touches != 1)
        return 27;

    touches = 0;
    conditional_returned = comma_conditional_return(0);
    if (conditional_returned != 81 || touches != 1)
        return 28;

    touches = 0;
    int call_argument_snapshot = identity((touch(), touches));
    if (call_argument_snapshot != 1 || touches != 1)
        return 15;

    touches = 0;
    int nested_call_argument_snapshot = identity(identity((touch(), touches)));
    if (nested_call_argument_snapshot != 1 || touches != 1)
        return 16;

    touches = 0;
    int arithmetic_snapshot = (touch(), touches) + 10;
    if (arithmetic_snapshot != 11 || touches != 1)
        return 17;

    touches = 0;
    int arithmetic_returned = comma_arithmetic_return();
    if (arithmetic_returned != 21 || touches != 1)
        return 18;

    touches = 0;
    int arithmetic_call_argument = identity((touch(), touches) + 30);
    if (arithmetic_call_argument != 31 || touches != 1)
        return 19;

    touches = 0;
    values[0] = 22;
    int array_index_snapshot = values[(touch(), 0)];
    if (array_index_snapshot != 22 || touches != 1)
        return 20;

    touches = 0;
    gate = 0;
    int short_circuit_and_left = ((touch(), gate) && touch());
    if (short_circuit_and_left != 0 || touches != 1)
        return 21;

    touches = 0;
    gate = 1;
    int short_circuit_or_left = ((touch(), gate) || touch());
    if (short_circuit_or_left != 1 || touches != 1)
        return 22;

    return 0;
}

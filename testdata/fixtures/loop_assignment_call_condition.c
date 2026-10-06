static int while_condition_calls;
static int zero_condition_calls;
static int if_condition_calls;
static int short_circuit_condition_calls;
static int dynamic_assignment_value;

static int next_while_value(void)
{
    while_condition_calls++;
    return while_condition_calls <= 3 ? while_condition_calls : -1;
}

static int next_if_value(void)
{
    if_condition_calls++;
    return 17;
}

static int next_zero_condition_value(void)
{
    zero_condition_calls++;
    return zero_condition_calls < 3 ? 0 : 1;
}

static int next_short_circuit_condition_value(void)
{
    short_circuit_condition_calls++;
    return 1;
}

static int dynamic_and_condition(int left)
{
    if (left && (dynamic_assignment_value = next_short_circuit_condition_value()) != 0) {
        return 1;
    }
    return 0;
}

static int dynamic_or_condition(int left)
{
    if (left || (dynamic_assignment_value = next_short_circuit_condition_value()) != 0) {
        return 1;
    }
    return 0;
}

static int while_assignment_condition(void)
{
    int value = 0;
    int total = 0;
    while ((value = next_while_value()) != -1) {
        total += value;
    }
    return total == 6 && value == -1 && while_condition_calls == 4 ? 0 : 1;
}

static int if_assignment_condition(void)
{
    int value = 0;
    if ((value = next_if_value()) != -1) {
        return value == 17 && if_condition_calls == 1 ? 0 : 1;
    }
    return 2;
}

static int while_assignment_zero_condition(void)
{
    int value = -1;
    while ((value = next_zero_condition_value()) == 0) {
    }
    return value == 1 && zero_condition_calls == 3 ? 0 : 1;
}

static int skipped_assignment_short_circuit_condition(void)
{
    int value = 0;
    if (0 && (value = next_short_circuit_condition_value()) != 0) {
        return 1;
    }
    return value == 0 && short_circuit_condition_calls == 0 ? 0 : 1;
}

static int dynamic_short_circuit_assignment_condition(void)
{
    int and_left = 0;
    if (dynamic_and_condition(and_left)) {
        return 1;
    }
    and_left = 1;
    if (!dynamic_and_condition(and_left)) {
        return 2;
    }

    int or_left = 1;
    if (!dynamic_or_condition(or_left)) {
        return 3;
    }
    or_left = 0;
    if (!dynamic_or_condition(or_left)) {
        return 4;
    }
    return dynamic_assignment_value == 1 && short_circuit_condition_calls == 2 ? 0 : 5;
}

int main(void)
{
    if (while_assignment_condition() != 0) {
        return 1;
    }
    if (if_assignment_condition() != 0) {
        return 2;
    }
    if (while_assignment_zero_condition() != 0) {
        return 3;
    }
    if (skipped_assignment_short_circuit_condition() != 0) {
        return 4;
    }
    if (dynamic_short_circuit_assignment_condition() != 0) {
        return 5;
    }
    return 0;
}

static int selected_true_calls;
static int selected_false_calls;
static int second_argument_calls;

static int mark_true(void)
{
    ++selected_true_calls;
    return 0;
}

static int mark_false(void)
{
    ++selected_false_calls;
    return 0;
}

static int mark_second_argument(void)
{
    ++second_argument_calls;
    return 0;
}

static int combine(int first, int second)
{
    return first + second;
}

int main(void)
{
    int (*operation)(int, int) = combine;
    int selector = 1;
    int true_result = operation(
        selector ? (mark_true(), 40) : (mark_false(), 90),
        mark_second_argument() + 2);
    if (true_result != 42 || selected_true_calls != 1 ||
        selected_false_calls != 0 || second_argument_calls != 1) {
        return 1;
    }

    selector = 0;
    int false_result = operation(
        selector ? (mark_true(), 40) : (mark_false(), 90),
        mark_second_argument() + 3);
    if (false_result != 93 || selected_true_calls != 1 ||
        selected_false_calls != 1 || second_argument_calls != 2) {
        return 2;
    }
    return 0;
}

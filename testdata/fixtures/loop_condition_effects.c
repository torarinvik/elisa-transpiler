static int for_condition_calls;
static int do_condition_calls;

static int structured_for_continue(void)
{
    int total = 0;
    for (int index = 0; index < 6; ++index) {
        if (index == 2) {
            continue;
        }
        total += index;
    }
    return total;
}

static int cfg_for_continue(void)
{
    int total = 0;
    for (int index = 0; index < 6; ++index) {
        if (index == 2) {
            continue;
        }
        total += index;
    }
    goto done;
    total = -100;
done:
    return total;
}

static int for_condition_effects(void)
{
    int index = 0;
    int total = 0;
    for (; index < 4 && (++for_condition_calls, index < 4); ++index) {
        if (index & 1) {
            continue;
        }
        total += index;
    }
    return total;
}

static int do_condition_effects(void)
{
    int iterations = 0;
    do {
        ++iterations;
        if (iterations == 1) {
            continue;
        }
    } while ((++do_condition_calls, iterations < 3));
    return iterations;
}

static int nested_do_continue(void)
{
    int total = 0;
    for (int index = 0; index < 3; ++index) {
        int attempts = 0;
        do {
            ++attempts;
            continue;
        } while (attempts < 2);
        total += index;
    }
    return total;
}

int main(void)
{
    if (structured_for_continue() != 13) {
        return 1;
    }
    if (cfg_for_continue() != 13) {
        return 2;
    }
    if (for_condition_effects() != 2 || for_condition_calls != 4) {
        return 3;
    }
    if (do_condition_effects() != 3 || do_condition_calls != 3) {
        return 4;
    }
    if (nested_do_continue() != 3) {
        return 5;
    }
    return 0;
}

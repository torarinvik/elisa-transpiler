#if __cplusplus < 201703L
#error "this fixture requires C++17 or later argument sequencing"
#endif

static int trace;
static volatile int volatile_value = 3;

static int first_argument()
{
    trace = trace * 10 + 1;
    trace = trace * 10 + 2;
    return 10;
}

static int second_argument()
{
    trace = trace * 10 + 3;
    trace = trace * 10 + 4;
    return 20;
}

static int combine(int first, int second)
{
    return first + second;
}

static int set_volatile()
{
    volatile_value = 7;
    return 0;
}

int main()
{
    int direct = combine(first_argument(), second_argument());
    if (direct != 30 || (trace != 1234 && trace != 3412)) {
        return 1;
    }

    volatile_value = 3;
    int volatile_result = combine(volatile_value, set_volatile());
    if ((volatile_result != 3 && volatile_result != 7) ||
        volatile_value != 7) {
        return 2;
    }

    trace = 0;
    int (*operation)(int, int) = combine;
    int indirect = (*operation)(first_argument(), second_argument());
    if (indirect != 30 || (trace != 1234 && trace != 3412)) {
        return 3;
    }
    return 0;
}

typedef int (*operation_fn)(int, int);

struct operation_table {
    operation_fn operation;
};

static int factory_calls;
static int argument_calls;
static struct operation_table table;

static int combine(int first, int second)
{
    return first + second;
}

static struct operation_table *select_table(void)
{
    ++factory_calls;
    return &table;
}

static int next_argument(void)
{
    ++argument_calls;
    return 20;
}

int main(void)
{
    table.operation = combine;
    int result = select_table()->operation(next_argument(), 22);
    if (result != 42 || factory_calls != 1 || argument_calls != 1) {
        return 1;
    }

    int selector = 1;
    int conditional_result =
        (selector ? combine : combine)(selector ? (next_argument(), 20) : 21, 22);
    if (conditional_result != 42 || argument_calls != 2) {
        return 2;
    }

    selector = 0;
    int skipped_result =
        (selector ? combine : combine)(selector ? (next_argument(), 20) : 21, 22);
    if (skipped_result != 43 || argument_calls != 2) {
        return 3;
    }
    return 0;
}

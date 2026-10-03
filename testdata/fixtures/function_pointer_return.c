#include <stddef.h>

typedef int (*operation_fn)(int, int);

static int factory_calls;
static int argument_calls;

static int combine(int first, int second)
{
    return first + second;
}

static operation_fn select_operation(int should_return_operation)
{
    ++factory_calls;
    return should_return_operation ? combine : NULL;
}

static int next_argument(void)
{
    ++argument_calls;
    return 20;
}

int main(void)
{
    int result = select_operation(1)(next_argument(), 22);
    if (result != 42 || factory_calls != 1 || argument_calls != 1) {
        return 1;
    }
    operation_fn absent = select_operation(0);
    if (absent != NULL || factory_calls != 2 || argument_calls != 1) {
        return 2;
    }
    return 0;
}

#include <stddef.h>

struct Allocator {
    void *(*allocate)(size_t);
};

static void *return_null(size_t size)
{
    return NULL;
}

static void *call_allocator(const struct Allocator *allocator, size_t size)
{
    return allocator->allocate(size);
}

static int increment(int value)
{
    return value + 1;
}

int main(void)
{
    int (*operation)(int) = increment;
    struct Allocator allocator = {return_null};
    if (operation(41) != 42)
        return 1;
    return call_allocator(&allocator, 41) != NULL;
}

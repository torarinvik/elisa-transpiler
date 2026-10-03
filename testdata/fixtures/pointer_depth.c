#include <stddef.h>

typedef void *memptr;

static int store_pointer(memptr *slot)
{
    *slot = 0;
    return *slot == 0;
}

int main(void)
{
    memptr value = 0;
    return store_pointer(&value) ? 0 : 1;
}

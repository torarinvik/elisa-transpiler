#include <stddef.h>

typedef void *(*allocate_fn)(size_t);

struct Hooks {
    allocate_fn allocate;
};

static void *return_null(size_t size) {
    (void)size;
    return NULL;
}

int main(void) {
    struct Hooks hooks = { return_null };
    if (hooks.allocate != NULL) {
        return hooks.allocate(8) == NULL ? 0 : 1;
    }
    return 2;
}

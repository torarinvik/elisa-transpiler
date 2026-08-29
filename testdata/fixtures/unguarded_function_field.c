#include <stddef.h>

typedef int (*operation_fn)(size_t);

struct Operations {
    operation_fn run;
};

static int return_size(size_t size) {
    (void)size;
    return 7;
}

int main(void) {
    struct Operations operations = { return_size };
    return operations.run(7) == 7 ? 0 : 1;
}

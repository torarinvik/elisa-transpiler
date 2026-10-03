#include <stddef.h>

struct Box {
    void *value;
};

static void *identity(void *value) {
    return value;
}

static int read_through_void(void *value) {
    return *(int *)value;
}

static void **identity_slot(void **slot) {
    return slot;
}

int main(void) {
    int value = 37;
    int *typed = &value;
    void *opaque = typed;
    int *restored = opaque;
    void *opaque_null = NULL;
    int *typed_null = opaque_null;
    struct Box box = {typed};
    int *field_restored = box.value;
    void *slots[2] = {typed, NULL};
    void **slot = slots;
    void **returned_slot = identity_slot(slot);
    void *round_trip = identity(returned_slot[0]);
    int *nested_restored = round_trip;
    int observed = read_through_void(typed);

    return observed == 37 && restored == &value && field_restored == &value &&
           typed_null == NULL && returned_slot[1] == NULL &&
           nested_restored == &value ? 0 : 1;
}

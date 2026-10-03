static int exercise_qualified_pointers(int **source_slot) {
    int **writable_slot = (int **)(int * const *)source_slot;
    volatile int **volatile_slot = (volatile int **)source_slot;
    **writable_slot += 5;
    return volatile_slot == 0 || **writable_slot != 42;
}

static int read_only_chain(const int * const *slot) {
    return slot != 0;
}

static int replace_const_pointee_pointer(const int **slot) {
    *slot = 0;
    return *slot == 0;
}

static int pointer_binding_qualifiers(void) {
    int first = 37;
    int second = 40;
    const int *readonly_pointee = &first;
    readonly_pointee = &second;
    int * const immutable_slot = &first;
    *immutable_slot = 42;
    return first != 42 || *readonly_pointee != 40;
}

int main(void) {
    int value = 37;
    int *pointer = &value;
    const int *pointer_to_const = &value;
    return exercise_qualified_pointers(&pointer) || value != 42 || read_only_chain(0) != 0 || !replace_const_pointee_pointer(&pointer_to_const) || pointer_binding_qualifiers();
}

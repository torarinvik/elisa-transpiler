struct CompoundValue {
    int value;
};

struct CompoundValue *global_value = &(struct CompoundValue){13};

int main(void) {
    return global_value->value == 13 ? 0 : 1;
}

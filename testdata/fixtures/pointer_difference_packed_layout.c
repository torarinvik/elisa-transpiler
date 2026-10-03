struct __attribute__((packed)) PackedItem {
    char tag;
    int value;
};

int main(void) {
    struct PackedItem items[2] = {0};
    return (items + 1) - items;
}

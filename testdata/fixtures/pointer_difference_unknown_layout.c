union Item {
    int value;
    double wide_value;
};

int main(void) {
    union Item items[2] = {0};
    return (items + 1) - items;
}

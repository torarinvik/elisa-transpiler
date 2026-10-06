int main(void) {
    volatile int *value = &(volatile int){13};
    return *value == 13 ? 0 : 1;
}

struct CompoundValue {
    int value;
};

int main() {
    return ((CompoundValue){13}).value == 13 ? 0 : 1;
}

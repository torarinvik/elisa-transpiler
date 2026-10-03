enum class Truth : bool {
    False,
    True
};

int main() {
    if (sizeof(Truth) != 1) return 1;
    Truth value = Truth::True;
    if (value != Truth::True) return 2;
    return 0;
}

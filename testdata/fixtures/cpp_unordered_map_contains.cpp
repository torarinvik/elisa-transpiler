#include <unordered_map>

int main() {
    std::unordered_map<int, int> values;
    if (values.contains(7)) return 1;
    values[7] = 42;
    if (!values.contains(7)) return 2;
    if (values.contains(8)) return 3;
    return values.size() == 1 ? 0 : 4;
}

#include <unordered_map>

int main() {
    std::unordered_map<int, int> values;
    values[7] = 42;

    auto found = values.find(7);
    if (found == values.end()) return 1;
    if (found->first != 7) return 2;
    if (found->second != 42) return 3;
    found->second = 43;
    if (values[7] != 43) return 5;

    auto missing = values.find(8);
    if (missing != values.end()) return 4;
    return 0;
}

#include <unordered_map>

int inspect_read_only(const std::unordered_map<int, int>& values) {
    auto found = values.find(7);
    if (found == values.end()) return 1;
    if (found->first != 7) return 2;
    if (found->second != 42) return 3;

    auto missing = values.find(8);
    if (missing != values.end()) return 4;
    return 0;
}

int main() {
    std::unordered_map<int, int> values;
    values[7] = 42;
    int result = inspect_read_only(values);
    if (result != 0) return result;

    auto mutable_found = values.find(7);
    const auto& read_only = values;
    auto const_found = read_only.find(7);
    if (!(mutable_found == const_found)) return 5;
    if (!(const_found == mutable_found)) return 6;
    if (mutable_found != const_found) return 11;
    if (const_found != mutable_found) return 12;

    auto mutable_missing = values.find(8);
    auto const_missing = read_only.find(8);
    if (!(mutable_missing == read_only.end())) return 7;
    if (!(const_missing == values.end())) return 8;
    if (!(mutable_found != const_missing)) return 9;
    if (!(const_missing != mutable_found)) return 10;
    return 0;
}

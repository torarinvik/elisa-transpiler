#include <cstddef>
#include <unordered_map>

enum class lookup_key : int { first_key = 1, second_key = 2 };

static std::unordered_map<int, int> values;
static std::unordered_map<lookup_key, int> enum_values;

int main() {
    enum_values[lookup_key::first_key] = 17;
    if (enum_values[lookup_key::first_key] != 17 || enum_values.count(lookup_key::second_key) != 0) return 63;
    values[7] = 42;
    for (int i = 0; i < 64; ++i) {
        values[i + 100] = i * 3;
    }
    for (int i = 0; i < 64; ++i) {
        if (values[i + 100] != i * 3) return 62;
    }
    int result = values[7];
    int occurrences = static_cast<int>(values.count(7));
    int was_nonempty = values.empty() ? 0 : 1;
    std::size_t erased = values.erase(7);
    int is_empty = values.empty() ? 1 : 0;
    return result + occurrences + was_nonempty + static_cast<int>(erased) + is_empty + static_cast<int>(values.size()) - 64;
}

#include <cstddef>
#include <unordered_map>

using integer_map = std::unordered_map<int, int>;
using wide_key = unsigned long;

enum class lookup_key : int { first_key = 1, second_key = 2 };

static integer_map values;
static std::unordered_map<wide_key, int> wide_values;
static std::unordered_map<lookup_key, int> enum_values;

int main() {
    // These positive keys share a bucket in Elisa dict's initial 8-slot table.
    // Erasing the first one exercises lookup through a tombstone; reinsertion
    // exercises tombstone reuse without losing the remaining colliding keys.
    std::unordered_map<int, int> collisions;
    collisions[0] = 10;
    collisions[3] = 30;
    collisions[8] = 80;
    if (collisions[0] != 10 || collisions[3] != 30 || collisions[8] != 80) return 61;
    if (collisions.erase(0) != 1 || collisions.count(0) != 0 || collisions.count(3) != 1 || collisions.count(8) != 1) return 62;
    collisions[24] = 240;
    if (collisions[24] != 240 || collisions[3] != 30 || collisions[8] != 80) return 63;
    if (collisions.erase(3) != 1 || collisions.count(3) != 0 || collisions.count(8) != 1 || collisions.count(24) != 1) return 66;

    enum_values[lookup_key::first_key] = 17;
    if (enum_values[lookup_key::first_key] != 17 || enum_values.count(lookup_key::second_key) != 0) return 63;
    wide_key high_key = 73UL;
    wide_values[high_key] = 19;
    if (wide_values.find(high_key) == wide_values.end() || wide_values.count(high_key) != 1) return 67;
    if (wide_values.erase(high_key) != 1 || !wide_values.empty()) return 68;

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
    std::size_t size_after_erase = values.size();
    int default_after_reinsert = values[7];
    std::size_t erased_again = values.erase(7);
    values.clear();
    if (!values.empty() || values.size() != 0 || default_after_reinsert != 0 || erased_again != 1) return 64;
    values[9] = 23;
    if (values.size() != 1 || values[9] != 23) return 65;
    return result + occurrences + was_nonempty + static_cast<int>(erased) + is_empty + static_cast<int>(size_after_erase) - 64;
}

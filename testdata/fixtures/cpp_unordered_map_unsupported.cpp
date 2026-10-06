#include <cstddef>
#include <functional>
#include <memory>
#include <unordered_map>
#include <utility>

struct NonZeroDefault {
    int value;
    NonZeroDefault() : value(17) {}
};

struct CustomHash {
    std::size_t operator()(int value) const
    {
        return static_cast<std::size_t>(value);
    }
};

struct CustomEqual {
    bool operator()(int left, int right) const
    {
        return left == right;
    }
};

static std::unordered_map<int, NonZeroDefault, CustomHash> values;
static std::unordered_map<int, int, std::hash<int>, CustomEqual> equality_policy;
static std::unordered_map<int, int, std::hash<int>, std::equal_to<int>,
                          std::allocator<std::pair<const int, int>>> allocator_policy;
static std::unordered_map<int, int*> pointers;
static std::unordered_map<int*, int> pointer_keys;

int main()
{
    std::unordered_map<int, int> unsupported_operation;
    unsupported_operation[1] = 22;
    auto unsupported_iterator = unsupported_operation.find(1);
    // erase(iterator) is a distinct overload from the supported erase(key).
    unsupported_operation.erase(unsupported_iterator);
    // The iterator-range overload is also outside the current adapter.
    unsupported_operation.erase(unsupported_operation.find(1), unsupported_operation.find(2));
    // reserve() is not part of the current Elisa adapter.
    unsupported_operation.reserve(16);
    return 0;
}

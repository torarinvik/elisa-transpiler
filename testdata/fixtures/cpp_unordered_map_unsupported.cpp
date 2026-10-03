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
    return 0;
}

#include <unordered_map>

static std::unordered_map<int, const char *> names;

int main()
{
    // C++ value-initializes an absent pointer mapped value to null.
    if (names[8] != nullptr)
        return 2;

    names[7] = "seven";
    return names[7][0] == 's' ? 0 : 1;
}

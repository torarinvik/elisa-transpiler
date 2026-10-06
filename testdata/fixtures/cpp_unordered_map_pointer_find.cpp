#include <unordered_map>

int main()
{
    std::unordered_map<int, const char *> names;

    auto missing = names.find(8);
    if (missing != names.end())
        return 1;

    names[7] = "seven";
    auto found = names.find(7);
    if (found == names.end())
        return 2;
    if (found->first != 7)
        return 3;

    const char *value = found->second;
    if (value == nullptr || value[0] != 's')
        return 4;
    return 0;
}

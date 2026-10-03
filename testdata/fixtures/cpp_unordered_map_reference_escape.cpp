#include <unordered_map>

static int address_escape()
{
    std::unordered_map<int, int> values;
    auto found = values.find(7);
    int* mapped_address = &found->second;
    return mapped_address == nullptr;
}

static int reference_escape()
{
    std::unordered_map<int, int> values;
    auto found = values.find(7);
    int& mapped_alias = found->second;
    return mapped_alias == 42;
}

int main()
{
    return address_escape() || reference_escape();
}

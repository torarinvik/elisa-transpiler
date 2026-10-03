template<typename Key, typename Value>
struct unordered_map {
    Value value;
};

static unordered_map<int, int> values;

int main()
{
    values.value = 42;
    return values.value;
}

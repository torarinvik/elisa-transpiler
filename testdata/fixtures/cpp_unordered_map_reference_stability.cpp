#include <unordered_map>

int main()
{
    std::unordered_map<int, int> values;
    int &retained_reference = values[7];
    int *retained_pointer = &retained_reference;
    *retained_pointer = 11;

    for (int key = 100; key < 356; ++key) {
        values[key] = key * 3;
    }

    retained_reference = 97;
    if (values[7] != 97 || values.size() != 257) {
        return 1;
    }
    *retained_pointer = 101;
    if (retained_reference != 101 || values[7] != 101) {
        return 2;
    }
    return 0;
}

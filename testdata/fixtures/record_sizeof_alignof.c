struct RecordItem {
    char tag;
    int value;
};

typedef struct RecordItem RecordAlias;

struct NestedRecord {
    short prefix;
    RecordAlias item;
    char tail[3];
};

int main(void) {
    unsigned long long record_size = sizeof(struct RecordItem);
    unsigned long long record_alignment = _Alignof(struct RecordItem);
    unsigned long long nested_size = sizeof(struct NestedRecord);
    unsigned long long nested_alignment = _Alignof(struct NestedRecord);
    unsigned long long record_array_size = sizeof(RecordAlias[2]);
    unsigned long long record_array_alignment = _Alignof(RecordAlias[2]);
    unsigned long long nested_array_size = sizeof(struct NestedRecord[2]);
    unsigned long long nested_array_alignment = _Alignof(struct NestedRecord[2]);
    return record_size == 8 && record_alignment == 4 &&
           nested_size == 16 && nested_alignment == 4 &&
           record_array_size == 16 && record_array_alignment == 4 &&
           nested_array_size == 32 && nested_array_alignment == 4 ? 0 : 1;
}

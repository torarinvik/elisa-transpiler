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

static long distance_in_items(struct RecordItem *first, struct RecordItem *second) {
    return second - first;
}

static long distance_in_nested(struct NestedRecord *first, struct NestedRecord *second) {
    return second - first;
}

int main(void) {
    struct RecordItem items[3] = {0};
    struct NestedRecord nested[3] = {0};
    return distance_in_items(&items[0], &items[2]) == 2 &&
           distance_in_nested(&nested[0], &nested[2]) == 2 ? 0 : 1;
}

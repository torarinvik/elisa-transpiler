struct __attribute__((packed)) PackedRecordLayout {
    char tag;
    int value;
};

int main(void) {
    return (int)_Alignof(struct PackedRecordLayout);
}

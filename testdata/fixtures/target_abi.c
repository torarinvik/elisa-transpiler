typedef __SIZE_TYPE__ size_t;

long target_long_global;

struct target_record {
    long signed_member;
    unsigned long unsigned_member;
};

long target_long(long value) {
    return value;
}

unsigned long target_unsigned_long(unsigned long value) {
    return value;
}

size_t target_size(size_t value) {
    return value;
}

char target_char(char value) {
    return value;
}

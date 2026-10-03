struct ByteViews
{
    unsigned char *mutable_bytes;
    const unsigned char *readonly_bytes;
};

static int sum_bytes(const unsigned char *bytes)
{
    return bytes[0] + bytes[1] + bytes[2] + bytes[3];
}

int main(void)
{
    unsigned char values[4] = { 1, 2, 3, 4 };
    unsigned char *mutable_cursor = values;
    mutable_cursor = values;
    const unsigned char *readonly_cursor = values;
    struct ByteViews views = { values, values };

    mutable_cursor[2] = 9;
    if (readonly_cursor[2] != 9 || views.mutable_bytes[2] != 9 || views.readonly_bytes[2] != 9)
        return 1;
    if (sum_bytes(values) != 16 || mutable_cursor != &values[0])
        return 2;
    return 0;
}

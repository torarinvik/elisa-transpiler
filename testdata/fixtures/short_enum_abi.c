enum TinyUnsigned {
    TINY_ZERO = 0,
    TINY_MAX = 255
};

enum TinySigned {
    SIGNED_MIN = -1,
    SIGNED_MAX = 1
};

enum SmallUnsigned {
    SMALL_ZERO = 0,
    SMALL_MAX = 65535
};

struct EnumSizes {
    enum TinyUnsigned tiny;
    enum TinySigned signed_value;
    enum SmallUnsigned small;
};

static enum TinyUnsigned pass_tiny(enum TinyUnsigned value)
{
    return value;
}

int main(void)
{
    struct EnumSizes values = { (enum TinyUnsigned)255, (enum TinySigned)-1, (enum SmallUnsigned)65535 };
    if (sizeof(enum TinyUnsigned) != 1 || sizeof(enum TinySigned) != 1 || sizeof(enum SmallUnsigned) != 2)
        return 1;
    if (sizeof(struct EnumSizes) != 4)
        return 2;
    if (pass_tiny(values.tiny) != (enum TinyUnsigned)255)
        return 3;
    if (values.signed_value != (enum TinySigned)-1)
        return 4;
    if (values.small != (enum SmallUnsigned)65535)
        return 5;
    return 0;
}

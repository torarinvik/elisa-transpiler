enum AccessMode
{
    ACCESS_NONE = 0,
    ACCESS_READ = 1,
    ACCESS_WRITE = 4,
    ACCESS_BOTH = ACCESS_READ | ACCESS_WRITE
};

enum WideMask
{
    WIDE_MASK_NONE = 0,
    WIDE_MASK_HIGH = 0xffffffffu
};

struct EnumBundle
{
    enum AccessMode access;
    enum WideMask wide;
};

static enum AccessMode initial_mode = ACCESS_READ | ACCESS_WRITE;
static enum WideMask initial_wide_mask = 0xffffffffu;
static struct EnumBundle initial_bundle = { .access = 7, .wide = 0xffffffffu };

static enum AccessMode from_integer(int value)
{
    return value;
}

static int to_integer(enum AccessMode value)
{
    return value;
}

static int accepts_six(enum AccessMode value)
{
    return value == 6;
}

static enum WideMask wide_mask_from_unsigned(unsigned int value)
{
    return value;
}

static unsigned int wide_mask_to_unsigned(enum WideMask value)
{
    return value;
}

static unsigned int identity_unsigned(unsigned int value)
{
    return value;
}

static int accepts_wide_mask(enum WideMask value)
{
    return value == WIDE_MASK_HIGH;
}

int main(void)
{
    enum AccessMode mode = ACCESS_READ | ACCESS_WRITE;
    if (mode != ACCESS_BOTH || (mode & ACCESS_READ) == 0)
        return 1;

    if (initial_mode != ACCESS_BOTH || !accepts_six(6))
        return 2;

    mode = from_integer(2);
    if (mode != 2)
        return 3;

    mode = (enum AccessMode)2;
    if (mode != 2)
        return 4;

    mode |= ACCESS_WRITE;
    if (mode != 6)
        return 5;

    if (to_integer(mode) != 6)
        return 6;

    enum WideMask wide_mask = 0xffffffffu;
    if (initial_wide_mask != WIDE_MASK_HIGH || wide_mask != WIDE_MASK_HIGH)
        return 7;
    if (wide_mask_from_unsigned(0xffffffffu) != WIDE_MASK_HIGH || !accepts_wide_mask(0xffffffffu))
        return 8;
    if (wide_mask_to_unsigned(wide_mask) != 0xffffffffu)
        return 9;
    if (identity_unsigned(wide_mask) != 0xffffffffu)
        return 10;
    wide_mask = 1u;
    wide_mask |= WIDE_MASK_HIGH;
    if (wide_mask != WIDE_MASK_HIGH)
        return 11;

    struct EnumBundle bundle = { .access = 2, .wide = 1u };
    if (initial_bundle.access != 7 || initial_bundle.wide != WIDE_MASK_HIGH)
        return 12;
    if (bundle.access != 2 || bundle.wide != 1u)
        return 13;
    bundle.access = 3;
    bundle.access |= ACCESS_WRITE;
    bundle.wide = 0xffffffffu;
    if (bundle.access != 7 || bundle.wide != WIDE_MASK_HIGH)
        return 14;

    enum AccessMode access_values[2] = { 1, 2 };
    access_values[1] = 3;
    access_values[1] |= ACCESS_WRITE;
    if (access_values[1] != 7)
        return 15;

    return 0;
}

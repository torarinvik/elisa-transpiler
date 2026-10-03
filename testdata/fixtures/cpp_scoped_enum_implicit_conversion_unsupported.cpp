enum class PixelMode : unsigned int {
    transparent = 0,
    opaque = 1
};

int enum_to_integer(PixelMode mode)
{
    return mode;
}

PixelMode integer_to_enum(int value)
{
    return value;
}

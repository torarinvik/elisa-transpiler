namespace renderer {
enum class PixelMode : unsigned int {
    transparent = 0,
    opaque = 1
};

using PixelModeAlias = PixelMode;
}

using PublicPixelMode = renderer::PixelModeAlias;

static unsigned int to_bits(PublicPixelMode value)
{
    return static_cast<unsigned int>(value);
}

static PublicPixelMode from_bits(unsigned int value)
{
    return static_cast<PublicPixelMode>(value);
}

static unsigned int to_bits_through_pointer(const PublicPixelMode *value)
{
    return static_cast<unsigned int>(*value);
}

int main()
{
    PublicPixelMode value = from_bits(0x80000005u);
    if (to_bits(value) != 0x80000005u) return 1;
    if (to_bits_through_pointer(&value) != 0x80000005u) return 3;

    value = from_bits(0xffffffffu);
    if (to_bits(value) != 0xffffffffu) return 2;
    if (to_bits_through_pointer(&value) != 0xffffffffu) return 4;
    return 0;
}

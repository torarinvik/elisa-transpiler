enum SmallMode {
    SMALL_NONE = 0,
    SMALL_ONE = 1
};

static enum SmallMode choose_mode(void)
{
    return (enum SmallMode)255;
}

int main(void)
{
    return choose_mode() == (enum SmallMode)255 ? 0 : 1;
}

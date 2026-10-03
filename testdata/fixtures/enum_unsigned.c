enum WideMode {
    WIDE_MODE_NONE = 0,
    WIDE_MODE_HIGH = 0xffffffffu
};

static int is_high(enum WideMode mode)
{
    return mode > 0 && mode == 0xffffffffu;
}

int main(void)
{
    enum WideMode mode = WIDE_MODE_HIGH;
    return is_high(mode) ? 0 : 1;
}
